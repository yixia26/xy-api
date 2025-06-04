import asyncio
import json
import os
import sys
import time
from loguru import logger
import aioredis
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logger.remove()  # 移除默认handler
logger.add(
    sys.stderr,
    level=log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

# Redis配置
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost")

class AIService:
    """
    AI服务，负责从Redis队列接收消息，生成回复，并将回复推送到Redis队列
    """
    def __init__(self):
        """初始化AI服务"""
        self.redis = None
        self.running = False
        # 支持处理多个卖家的消息
        self.seller_ids = set()
        
    async def connect_redis(self):
        """连接到Redis"""
        try:
            self.redis = await aioredis.from_url(
                REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info(f"Redis连接成功: {REDIS_URL}")
            return True
        except Exception as e:
            logger.error(f"Redis连接失败: {str(e)}")
            return False
            
    async def close_redis(self):
        """关闭Redis连接"""
        if self.redis:
            await self.redis.close()
            logger.info("Redis连接已关闭")
            
    def add_seller(self, seller_id):
        """添加要处理的卖家ID"""
        self.seller_ids.add(seller_id)
        logger.info(f"添加卖家ID: {seller_id}")
        
    def remove_seller(self, seller_id):
        """移除卖家ID"""
        self.seller_ids.discard(seller_id)
        logger.info(f"移除卖家ID: {seller_id}")
            
    async def process_message(self, message_data):
        """
        处理客户消息，生成回复
        
        Args:
            message_data: 消息数据（JSON字符串）
            
        Returns:
            dict: 回复数据
        """
        try:
            # 解析消息
            message = json.loads(message_data)
            
            # 提取必要信息
            chat_id = message.get("chat_id")
            sender_id = message.get("sender_id")
            sender_name = message.get("sender_name", "客户")
            item_id = message.get("item_id")
            customer_message = message.get("message", "")
            seller_id = message.get("seller_id")
            item_description = message.get("item_description", "")
            context = message.get("context", [])
            
            # 日志记录
            logger.info(f"收到来自 {sender_name} 的消息: {customer_message}")
            
            # 这里可以调用实际的AI模型生成回复
            # 简单示例：生成一个回复
            reply_content = f"您好，感谢您的咨询！我已收到您的消息："
            var = {customer_message}
            "。请问还有其他问题吗？"

            # 构造回复数据
            reply = {
                "chat_id": chat_id,
                "receiver_id": sender_id,
                "reply_content": reply_content,
                "item_id": item_id,
                "processed_time": int(time.time() * 1000)
            }
            
            # 添加一些处理延迟，模拟AI处理时间
            await asyncio.sleep(1)
            
            logger.info(f"生成回复: {reply_content}")
            return reply
            
        except json.JSONDecodeError:
            logger.error(f"消息解析失败: {message_data}")
            return None
        except Exception as e:
            logger.error(f"处理消息时发生错误: {str(e)}")
            return None
            
    async def listen_for_messages(self, seller_id):
        """
        监听特定卖家的客户消息队列
        
        Args:
            seller_id: 卖家ID
        """
        customer_queue = f"customer:message:{seller_id}"
        response_queue = f"ai:response:{seller_id}"
        
        logger.info(f"开始监听卖家 {seller_id} 的消息队列")
        
        while self.running:
            try:
                # 使用阻塞式弹出，等待客户消息
                result = await self.redis.blpop(customer_queue, timeout=1)
                
                if not result:
                    # 超时或队列为空
                    continue
                    
                # result是一个元组(key, value)，我们需要value
                _, message_data = result
                
                # 处理消息，生成回复
                reply = await self.process_message(message_data)
                
                if reply:
                    # 将回复推送到回复队列
                    await self.redis.rpush(response_queue, json.dumps(reply))
                    logger.info(f"回复已推送到队列: {response_queue}")
                    
            except asyncio.CancelledError:
                logger.info(f"监听卖家 {seller_id} 的任务被取消")
                break
            except Exception as e:
                logger.error(f"监听卖家 {seller_id} 的消息队列时发生错误: {str(e)}")
                # 等待一段时间后重试
                await asyncio.sleep(5)
                
    async def run(self):
        """运行AI服务"""
        # 连接Redis
        if not await self.connect_redis():
            logger.error("Redis连接失败，无法启动AI服务")
            return
            
        self.running = True
        tasks = []
        
        try:
            # 为每个卖家创建一个监听任务
            for seller_id in self.seller_ids:
                task = asyncio.create_task(self.listen_for_messages(seller_id))
                tasks.append(task)
                
            # 等待所有任务完成或被取消
            await asyncio.gather(*tasks, return_exceptions=True)
                
        except asyncio.CancelledError:
            logger.info("AI服务被取消")
        except Exception as e:
            logger.error(f"AI服务运行错误: {str(e)}")
        finally:
            # 停止所有任务
            self.running = False
            for task in tasks:
                if not task.done():
                    task.cancel()
                    
            # 关闭Redis连接
            await self.close_redis()
            
            logger.info("AI服务已停止")
            
async def main():
    """主函数"""
    # 创建AI服务实例
    service = AIService()
    
    # 从环境变量或命令行参数获取卖家ID
    seller_ids = os.getenv("SELLER_IDS", "").split(",")
    if len(sys.argv) > 1:
        seller_ids = sys.argv[1].split(",")
        
    # 如果没有指定卖家ID，退出
    if not seller_ids or not seller_ids[0]:
        logger.error("未指定卖家ID，请通过环境变量SELLER_IDS或命令行参数指定")
        return
        
    # 添加卖家ID
    for seller_id in seller_ids:
        if seller_id:
            service.add_seller(seller_id.strip())
            
    # 运行服务
    try:
        await service.run()
    except KeyboardInterrupt:
        logger.info("接收到中断信号，服务即将停止")
    
if __name__ == "__main__":
    asyncio.run(main()) 