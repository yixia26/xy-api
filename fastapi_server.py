from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import asyncio
import time
import uuid
from datetime import datetime
import uvicorn
import os
from loguru import logger
import sys

# 导入闲鱼主程序相关模块
from XianyuLive import XianyuLive

# 配置日志级别
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logger.remove()  # 移除默认handler
logger.add(
    sys.stderr,
    level=log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

app = FastAPI(title="闲鱼API服务", description="提供闲鱼会话管理和商品信息查询接口")

# 会话存储
active_sessions: Dict[str, Dict[str, Any]] = {}

# 请求模型
class SessionRequest(BaseModel):
    cookies_str: str

# 响应模型
class SessionResponse(BaseModel):
    status: str
    session_id: Optional[str] = None
    message: str

class SessionsResponse(BaseModel):
    status: str
    active_sessions: Optional[List[Dict[str, Any]]] = None
    message: Optional[str] = None

class ItemDetailResponse(BaseModel):
    status: str
    item_id: Optional[str] = None
    item_name: Optional[str] = None
    price: Optional[str] = None
    message: Optional[str] = None

# 会话管理函数
async def run_xianyu_session(session_id: str, cookies_str: str):
    """在后台运行闲鱼会话"""
    try:
        # 创建闲鱼会话实例
        xianyu = XianyuLive(cookies_str)
        active_sessions[session_id]["xianyu"] = xianyu
        active_sessions[session_id]["task"] = asyncio.create_task(xianyu.main())
        
        # 等待任务完成或被取消
        try:
            await active_sessions[session_id]["task"]
        except asyncio.CancelledError:
            logger.info(f"会话 {session_id} 已取消")
        finally:
            # 如果会话已结束，从活跃会话中移除
            if session_id in active_sessions:
                active_sessions[session_id]["status"] = "stopped"
                logger.info(f"会话 {session_id} 已停止")
    except Exception as e:
        logger.error(f"会话 {session_id} 发生错误: {str(e)}")
        if session_id in active_sessions:
            active_sessions[session_id]["status"] = "error"
            active_sessions[session_id]["error"] = str(e)

@app.post("/start_session", response_model=SessionResponse)
async def start_session(request: SessionRequest, background_tasks: BackgroundTasks):
    """启动新的闲鱼会话"""
    try:
        # 生成唯一会话ID
        session_id = str(uuid.uuid4())
        
        # 记录会话信息
        active_sessions[session_id] = {
            "session_id": session_id,
            "status": "starting",
            "start_time": datetime.now().isoformat(),
            "cookies_str": request.cookies_str
        }
        
        # 在后台启动会话
        background_tasks.add_task(run_xianyu_session, session_id, request.cookies_str)
        
        # 更新状态为活跃
        active_sessions[session_id]["status"] = "active"
        
        logger.info(f"成功启动会话: {session_id}")
        return {
            "status": "success",
            "session_id": session_id,
            "message": "会话启动成功"
        }
    except Exception as e:
        logger.error(f"启动会话失败: {str(e)}")
        return {
            "status": "error",
            "message": f"会话启动失败: {str(e)}"
        }

@app.post("/stop_session/{session_id}", response_model=SessionResponse)
async def stop_session(session_id: str):
    """停止指定的闲鱼会话"""
    try:
        if session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        session = active_sessions[session_id]
        if "task" in session and not session["task"].done():
            # 取消会话任务
            session["task"].cancel()
            try:
                await session["task"]
            except asyncio.CancelledError:
                pass
        
        # 更新会话状态
        active_sessions[session_id]["status"] = "stopped"
        logger.info(f"会话 {session_id} 已停止")
        
        return {
            "status": "success",
            "session_id": session_id,
            "message": "会话已停止"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"停止会话 {session_id} 失败: {str(e)}")
        return {
            "status": "error",
            "message": f"停止会话失败: {str(e)}"
        }

@app.get("/sessions", response_model=SessionsResponse)
async def get_sessions():
    """获取所有活跃会话列表"""
    try:
        sessions_info = []
        for session_id, session in active_sessions.items():
            sessions_info.append({
                "session_id": session_id,
                "status": session["status"],
                "start_time": session["start_time"]
            })
        
        return {
            "status": "success",
            "active_sessions": sessions_info
        }
    except Exception as e:
        logger.error(f"获取活跃会话失败: {str(e)}")
        return {
            "status": "error",
            "message": f"获取活跃会话失败: {str(e)}"
        }

@app.get("/item_detail/{session_id}/{item_id}", response_model=ItemDetailResponse)
async def get_item_detail(session_id: str, item_id: str):
    """获取指定会话和商品ID的商品详情信息"""
    try:
        if session_id not in active_sessions:
            return {
                "status": "error",
                "message": "获取商品详情失败: 会话不存在"
            }
        
        session = active_sessions[session_id]
        if session["status"] != "active":
            return {
                "status": "error",
                "message": f"获取商品详情失败: 会话状态为 {session['status']}"
            }
        
        # 获取闲鱼实例
        xianyu = session.get("xianyu")
        if not xianyu:
            return {
                "status": "error",
                "message": "获取商品详情失败: 会话未初始化完成"
            }
        
        # 从缓存中获取商品信息
        item_info = xianyu.context_manager.get_item_info(item_id)
        
        # 如果缓存中没有，则从API获取
        if not item_info:
            api_result = xianyu.xianyu.get_item_info(item_id)
            if 'data' in api_result and 'itemDO' in api_result['data']:
                item_info = api_result['data']['itemDO']
                # 保存到缓存
                xianyu.context_manager.save_item_info(item_id, item_info)
            else:
                return {
                    "status": "error",
                    "message": "获取商品详情失败: API返回错误"
                }
        
        # 返回商品信息
        return {
            "status": "success",
            "item_id": item_id,
            "item_name": item_info.get("title", ""),
            "price": str(item_info.get("soldPrice", ""))
        }
    except Exception as e:
        logger.error(f"获取商品详情失败: {str(e)}")
        return {
            "status": "error",
            "message": f"获取商品详情失败: {str(e)}"
        }

# 添加健康检查接口
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# 启动服务器
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port) 