import json
import time
import hashlib
import uuid
import base64
import struct
from typing import Any, Dict, List, Union
import msgpack


def trans_cookies(cookies_str: str) -> Dict[str, str]:
    """解析cookie字符串为字典"""
    cookies = {}
    for cookie in cookies_str.split("; "):
        try:
            parts = cookie.split('=', 1)
            if len(parts) == 2:
                cookies[parts[0]] = parts[1]
        except:
            continue
    return cookies


def generate_mid() -> str:
    """生成mid"""
    import random
    random_part = int(1000 * random.random())
    timestamp = int(time.time() * 1000)
    return f"{random_part}{timestamp} 0"


def generate_uuid() -> str:
    """生成uuid"""
    timestamp = int(time.time() * 1000)
    return f"-{timestamp}1"


def generate_device_id(user_id: str) -> str:
    """生成设备ID"""
    import random
    
    # 字符集
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    result = []
    
    for i in range(36):
        if i in [8, 13, 18, 23]:
            result.append("-")
        elif i == 14:
            result.append("4")
        else:
            if i == 19:
                # 对于位置19，需要特殊处理
                rand_val = int(16 * random.random())
                result.append(chars[(rand_val & 0x3) | 0x8])
            else:
                rand_val = int(16 * random.random())
                result.append(chars[rand_val])
    
    return ''.join(result) + "-" + user_id


def generate_sign(t: str, token: str, data: str) -> str:
    """生成签名"""
    app_key = "34839810"
    msg = f"{token}&{t}&{app_key}&{data}"
    
    # 使用MD5生成签名
    md5_hash = hashlib.md5()
    md5_hash.update(msg.encode('utf-8'))
    return md5_hash.hexdigest()


class MessagePackDecoder:
    """MessagePack解码器的简化实现"""
    
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0
        self.length = len(data)
    
    def read_byte(self) -> int:
        if self.pos >= self.length:
            raise ValueError("Unexpected end of data")
        byte = self.data[self.pos]
        self.pos += 1
        return byte
    
    def read_bytes(self, count: int) -> bytes:
        if self.pos + count > self.length:
            raise ValueError("Unexpected end of data")
        result = self.data[self.pos:self.pos + count]
        self.pos += count
        return result
    
    def read_uint16(self) -> int:
        return struct.unpack('>H', self.read_bytes(2))[0]
    
    def read_uint32(self) -> int:
        return struct.unpack('>I', self.read_bytes(4))[0]
    
    def read_string(self, length: int) -> str:
        return self.read_bytes(length).decode('utf-8')
    
    def decode(self) -> Any:
        """简化的MessagePack解码"""
        try:
            # 使用msgpack库进行解码
            return msgpack.unpackb(self.data, raw=False, strict_map_key=False)
        except Exception as e:
            # 如果msgpack解码失败，返回原始数据的base64编码
            return base64.b64encode(self.data).decode('utf-8')


def decrypt(data: str) -> str:
    """解密函数的Python实现"""
    try:
        # 1. Base64解码
        # 清理非base64字符
        cleaned_data = ''.join(c for c in data if c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
        
        # 添加padding如果需要
        while len(cleaned_data) % 4 != 0:
            cleaned_data += '='
        
        try:
            decoded_bytes = base64.b64decode(cleaned_data)
        except Exception as e:
            # 如果base64解码失败，尝试其他方法
            return json.dumps({"error": f"Base64 decode failed: {str(e)}", "raw_data": data})
        
        # 2. 尝试MessagePack解码
        try:
            decoder = MessagePackDecoder(decoded_bytes)
            result = decoder.decode()
            
            # 3. 转换为JSON字符串
            def json_serializer(obj):
                """自定义JSON序列化器"""
                if isinstance(obj, bytes):
                    try:
                        return obj.decode('utf-8')
                    except:
                        return base64.b64encode(obj).decode('utf-8')
                elif hasattr(obj, '__dict__'):
                    return obj.__dict__
                else:
                    return str(obj)
            
            return json.dumps(result, ensure_ascii=False, default=json_serializer)
            
        except Exception as e:
            # 如果MessagePack解码失败，尝试直接解析为字符串
            try:
                text_result = decoded_bytes.decode('utf-8')
                return json.dumps({"text": text_result})
            except:
                # 最后的备选方案：返回十六进制表示
                hex_result = decoded_bytes.hex()
                return json.dumps({"hex": hex_result, "error": f"Decode failed: {str(e)}"})
                
    except Exception as e:
        return json.dumps({"error": f"Decrypt failed: {str(e)}", "raw_data": data})
