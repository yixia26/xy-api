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
import redis.asyncio as redis

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

class StopSessionRequest(BaseModel):
    session_id: str

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

# Redis 连接配置
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost")

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化 Redis 连接池"""
    try:
        app.state.redis = await redis.from_url(
            REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        logger.info(f"Redis 连接池初始化成功: {REDIS_URL}")
    except Exception as e:
        logger.error(f"Redis 连接池初始化失败: {str(e)}")
        # 这里可以选择继续运行或退出应用
        # sys.exit(1)

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时关闭 Redis 连接池"""
    if hasattr(app.state, "redis"):
        await app.state.redis.close()
        logger.info("Redis 连接池已关闭")

# 会话管理函数
async def run_xianyu_session(session_id: str, cookies_str: str, redis_client, xianyu_instance=None):
    """在后台运行闲鱼会话"""
    try:
        # 如果没有传入已创建的闲鱼实例，则创建一个新的
        if xianyu_instance is None:
            xianyu = XianyuLive(cookies_str, redis_client)
        else:
            xianyu = xianyu_instance
            
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
        # 检查 Redis 连接是否可用
        if not hasattr(app.state, "redis"):
            return {
                "status": "error",
                "message": "Redis 连接不可用，无法启动会话"
            }
            
        # 先创建闲鱼实例以获取myid
        try:
            xianyu = XianyuLive(request.cookies_str, app.state.redis)
            
            # 检查 myid 是否成功提取
            if not hasattr(xianyu, 'myid') or not xianyu.myid:
                return {
                    "status": "error",
                    "message": "无法从cookies中提取用户ID (unb)，请检查cookies是否有效"
                }
                
            session_id = xianyu.myid  # 使用myid作为会话ID
            
        except KeyError as e:
            logger.error(f"创建闲鱼实例失败: cookies中缺少关键字段 - {str(e)}")
            return {
                "status": "error",
                "message": f"cookies中缺少必要字段: {str(e)}，请确保cookies有效"
            }
        except Exception as e:
            logger.error(f"创建闲鱼实例失败: {str(e)}")
            return {
                "status": "error",
                "message": f"无法获取用户ID: {str(e)}"
            }
            
        # 检查是否已存在相同ID的会话
        if session_id in active_sessions:
            # 如果会话已存在且活跃，则返回错误
            if active_sessions[session_id]["status"] == "active":
                return {
                    "status": "error",
                    "session_id": session_id,
                    "message": "该用户已有活跃会话，请先停止当前会话"
                }
            # 如果会话存在但已停止，则清除旧会话信息
            else:
                logger.info(f"清除用户 {session_id} 的旧会话信息")
        
        # 记录会话信息
        active_sessions[session_id] = {
            "session_id": session_id,
            "status": "starting",
            "start_time": datetime.now().isoformat(),
            "cookies_str": request.cookies_str
        }
        
        # 在后台启动会话，传递已创建的闲鱼实例
        background_tasks.add_task(run_xianyu_session, session_id, request.cookies_str, app.state.redis, xianyu)
        
        # 更新状态为活跃
        active_sessions[session_id]["status"] = "active"
        
        # 向Redis Pub/Sub通道发送会话启动通知
        try:
            await app.state.redis.publish('ai_session:start', session_id)
            logger.info(f"已发送会话启动通知到Redis通道: ai_session:start, myid: {session_id}")
        except Exception as e:
            logger.error(f"发送会话启动通知失败: {str(e)}")
            # 通知发送失败不影响会话启动
        
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

@app.post("/stop_session", response_model=SessionResponse)
async def stop_session(request: StopSessionRequest):
    """停止指定的闲鱼会话"""
    session_id = request.session_id
    try:
        if session_id not in active_sessions:
            logger.warning(f"尝试停止不存在的会话: {session_id}")
            raise HTTPException(status_code=404, detail="会话不存在")
        
        logger.info(f"尝试停止会话: {session_id}")
        session = active_sessions[session_id]
        
        if "task" in session and not session["task"].done():
            # 取消会话任务
            session["task"].cancel()
            logger.info(f"已取消会话 {session_id} 的任务")
            
            try:
                await session["task"]
            except asyncio.CancelledError:
                logger.debug(f"会话 {session_id} 的任务已正确取消")
            except Exception as e:
                logger.error(f"取消会话 {session_id} 的任务时发生错误: {str(e)}")
        else:
            logger.warning(f"会话 {session_id} 无活动任务或任务已完成")
        
        # 更新会话状态
        active_sessions[session_id]["status"] = "stopped"
        active_sessions[session_id]["stop_time"] = datetime.now().isoformat()
        
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
            "session_id": session_id,
            "message": f"停止会话失败: {str(e)}"
        }

@app.get("/sessions", response_model=SessionsResponse)
async def get_sessions():
    """获取所有活跃会话列表"""
    try:
        sessions_info = []
        for session_id, session in active_sessions.items():
            # 计算会话运行时间
            start_time = datetime.fromisoformat(session["start_time"])
            current_time = datetime.now()
            running_time_seconds = (current_time - start_time).total_seconds()
            
            # 格式化运行时间
            hours, remainder = divmod(int(running_time_seconds), 3600)
            minutes, seconds = divmod(remainder, 60)
            running_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            info = {
                "session_id": session_id,
                "status": session["status"],
                "start_time": session["start_time"],
                "running_time": running_time
            }
            
            # 如果会话已停止，添加停止时间
            if "stop_time" in session:
                info["stop_time"] = session["stop_time"]
            
            # 如果有错误信息，添加到返回数据中
            if "error" in session:
                info["error"] = session["error"]
                
            sessions_info.append(info)
        
        # 按状态排序：活跃的会话排在前面
        sessions_info.sort(key=lambda x: 0 if x["status"] == "active" else 1)
        
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
    redis_status = "connected" if hasattr(app.state, "redis") else "disconnected"
    return {
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "redis": redis_status
    }

# 启动服务器
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port) 