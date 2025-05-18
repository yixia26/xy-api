import sqlite3
import os
import json
from datetime import datetime
from loguru import logger


class ChatContextManager:
    """
    聊天上下文管理器
    
    负责存储和检索用户与商品之间的对话历史，使用SQLite数据库进行持久化存储。
    支持按用户ID和商品ID检索对话历史，以及清理过期的历史记录。
    """
    
    def __init__(self, max_history=100, db_path="data/chat_history.db"):
        """
        初始化聊天上下文管理器
        
        Args:
            max_history: 每个对话保留的最大消息数
            db_path: SQLite数据库文件路径
        """
        self.max_history = max_history
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        """初始化数据库表结构"""
        # 确保数据库目录存在
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建消息表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建索引以加速查询
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_user_item ON messages (user_id, item_id)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_timestamp ON messages (timestamp)
        ''')
        
        # 创建议价次数表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS bargain_counts (
            user_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            count INTEGER DEFAULT 0,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, item_id)
        )
        ''')
        
        # 创建商品信息表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            item_id TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            price REAL,
            description TEXT,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"聊天历史数据库初始化完成: {self.db_path}")
        
    def add_message(self, user_id, item_id, role, content):
        """
        添加新消息到对话历史
        
        Args:
            user_id: 用户ID
            item_id: 商品ID
            role: 消息角色 (user/assistant)
            content: 消息内容
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 插入新消息
            cursor.execute(
                "INSERT INTO messages (user_id, item_id, role, content, timestamp) VALUES (?, ?, ?, ?, ?)",
                (user_id, item_id, role, content, datetime.now().isoformat())
            )
            
            # 检查是否需要清理旧消息
            cursor.execute(
                """
                SELECT id FROM messages 
                WHERE user_id = ? AND item_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?, 1
                """, 
                (user_id, item_id, self.max_history)
            )
            
            oldest_to_keep = cursor.fetchone()
            if oldest_to_keep:
                cursor.execute(
                    "DELETE FROM messages WHERE user_id = ? AND item_id = ? AND id < ?",
                    (user_id, item_id, oldest_to_keep[0])
                )
            
            conn.commit()
        except Exception as e:
            logger.error(f"添加消息到数据库时出错: {e}")
            conn.rollback()
        finally:
            conn.close()
        
    def increment_bargain_count(self, user_id, item_id):
        """
        增加用户对特定商品的议价次数
        
        Args:
            user_id: 用户ID
            item_id: 商品ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 使用UPSERT语法（SQLite 3.24.0及以上版本支持）
            cursor.execute(
                """
                INSERT INTO bargain_counts (user_id, item_id, count, last_updated)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(user_id, item_id) 
                DO UPDATE SET count = count + 1, last_updated = ?
                """,
                (user_id, item_id, datetime.now().isoformat(), datetime.now().isoformat())
            )
            
            conn.commit()
            logger.debug(f"用户 {user_id} 商品 {item_id} 议价次数已增加")
        except Exception as e:
            logger.error(f"增加议价次数时出错: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_bargain_count(self, user_id, item_id):
        """
        获取用户对特定商品的议价次数
        
        Args:
            user_id: 用户ID
            item_id: 商品ID
            
        Returns:
            int: 议价次数
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT count FROM bargain_counts WHERE user_id = ? AND item_id = ?",
                (user_id, item_id)
            )
            
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"获取议价次数时出错: {e}")
            return 0
        finally:
            conn.close()
        
    def get_context(self, user_id, item_id):
        """
        获取特定用户和商品的对话历史
        
        Args:
            user_id: 用户ID
            item_id: 商品ID
            
        Returns:
            list: 包含对话历史的列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """
                SELECT role, content FROM messages 
                WHERE user_id = ? AND item_id = ? 
                ORDER BY timestamp ASC
                LIMIT ?
                """, 
                (user_id, item_id, self.max_history)
            )
            
            messages = [{"role": role, "content": content} for role, content in cursor.fetchall()]
            
            # 获取议价次数并添加到上下文中
            bargain_count = self.get_bargain_count(user_id, item_id)
            if bargain_count > 0:
                # 添加一条系统消息，包含议价次数信息
                messages.append({
                    "role": "system", 
                    "content": f"议价次数: {bargain_count}"
                })
            
        except Exception as e:
            logger.error(f"获取对话历史时出错: {e}")
            messages = []
        finally:
            conn.close()
        
        return messages
    
    def get_user_items(self, user_id):
        """
        获取用户交互过的所有商品ID
        
        Args:
            user_id: 用户ID
            
        Returns:
            list: 商品ID列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT DISTINCT item_id FROM messages WHERE user_id = ?", 
                (user_id,)
            )
            
            items = [item[0] for item in cursor.fetchall()]
        except Exception as e:
            logger.error(f"获取用户商品列表时出错: {e}")
            items = []
        finally:
            conn.close()
        
        return items
    
    def get_recent_users(self, limit=100):
        """
        获取最近交互的用户列表
        
        Args:
            limit: 返回的最大用户数
            
        Returns:
            list: 用户ID列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """
                SELECT DISTINCT user_id FROM messages 
                GROUP BY user_id
                ORDER BY MAX(timestamp) DESC
                LIMIT ?
                """, 
                (limit,)
            )
            
            users = [user[0] for user in cursor.fetchall()]
        except Exception as e:
            logger.error(f"获取最近用户列表时出错: {e}")
            users = []
        finally:
            conn.close()
        
        return users
    
    def get_user_stats(self, user_id):
        """
        获取用户的统计信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            dict: 包含用户统计信息的字典
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 获取用户消息总数
            cursor.execute(
                "SELECT COUNT(*) FROM messages WHERE user_id = ?", 
                (user_id,)
            )
            total_messages = cursor.fetchone()[0]
            
            # 获取用户交互的商品数
            cursor.execute(
                "SELECT COUNT(DISTINCT item_id) FROM messages WHERE user_id = ?", 
                (user_id,)
            )
            total_items = cursor.fetchone()[0]
            
            # 获取用户最早和最近的消息时间
            cursor.execute(
                "SELECT MIN(timestamp), MAX(timestamp) FROM messages WHERE user_id = ?", 
                (user_id,)
            )
            first_time, last_time = cursor.fetchone()
            
            stats = {
                "total_messages": total_messages,
                "total_items": total_items,
                "first_interaction": first_time,
                "last_interaction": last_time
            }
        except Exception as e:
            logger.error(f"获取用户统计信息时出错: {e}")
            stats = {}
        finally:
            conn.close()
        
        return stats
    
    def clear_history(self, days_to_keep=30):
        """
        清理指定天数前的历史记录
        
        Args:
            days_to_keep: 保留多少天的历史
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """
                DELETE FROM messages 
                WHERE timestamp < datetime('now', '-' || ? || ' days')
                """, 
                (days_to_keep,)
            )
            
            deleted_count = cursor.rowcount
            conn.commit()
            logger.info(f"已清理 {deleted_count} 条历史消息记录")
        except Exception as e:
            logger.error(f"清理历史记录时出错: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def backup_database(self, backup_path=None):
        """
        备份数据库
        
        Args:
            backup_path: 备份文件路径，如果为None则使用时间戳生成路径
            
        Returns:
            str: 备份文件路径
        """
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.join(os.path.dirname(self.db_path), "backups")
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            backup_path = os.path.join(backup_dir, f"chat_history_{timestamp}.db")
        
        try:
            # 使用SQLite的备份API
            source_conn = sqlite3.connect(self.db_path)
            dest_conn = sqlite3.connect(backup_path)
            
            source_conn.backup(dest_conn)
            
            source_conn.close()
            dest_conn.close()
            
            logger.info(f"数据库已备份到: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"备份数据库时出错: {e}")
            return None
            
    def save_item_info(self, item_id, item_data):
        """
        保存商品信息到数据库
        
        Args:
            item_id: 商品ID
            item_data: 商品信息字典
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 从商品数据中提取有用信息
            price = float(item_data.get('soldPrice', 0))
            description = item_data.get('desc', '')
            
            # 将整个商品数据转换为JSON字符串
            data_json = json.dumps(item_data, ensure_ascii=False)
            
            cursor.execute(
                """
                INSERT INTO items (item_id, data, price, description, last_updated) 
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(item_id) 
                DO UPDATE SET data = ?, price = ?, description = ?, last_updated = ?
                """,
                (
                    item_id, data_json, price, description, datetime.now().isoformat(),
                    data_json, price, description, datetime.now().isoformat()
                )
            )
            
            conn.commit()
            logger.debug(f"商品信息已保存: {item_id}")
        except Exception as e:
            logger.error(f"保存商品信息时出错: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_item_info(self, item_id):
        """
        从数据库获取商品信息
        
        Args:
            item_id: 商品ID
            
        Returns:
            dict: 商品信息字典，如果不存在返回None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT data FROM items WHERE item_id = ?",
                (item_id,)
            )
            
            result = cursor.fetchone()
            if result:
                return json.loads(result[0])
            return None
        except Exception as e:
            logger.error(f"获取商品信息时出错: {e}")
            return None
        finally:
            conn.close()
            
    def clear_old_items(self, days_to_keep=90):
        """
        清理指定天数前未更新的商品信息
        
        Args:
            days_to_keep: 保留多少天的商品信息
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """
                DELETE FROM items 
                WHERE last_updated < datetime('now', '-' || ? || ' days')
                """, 
                (days_to_keep,)
            )
            
            deleted_count = cursor.rowcount
            conn.commit()
            logger.info(f"已清理 {deleted_count} 条过期商品信息")
        except Exception as e:
            logger.error(f"清理商品信息时出错: {e}")
            conn.rollback()
        finally:
            conn.close() 