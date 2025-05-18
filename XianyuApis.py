import json
import time
import os
import re

import requests
from loguru import logger
from utils.xianyu_utils import generate_sign, trans_cookies, generate_device_id


class XianyuApis:
    def __init__(self):
        self.url = 'https://h5api.m.goofish.com/h5/mtop.taobao.idlemessage.pc.login.token/1.0/'
        self.session = requests.Session()
        self.session.headers.update({
            'accept': 'application/json',
            'accept-language': 'zh-CN,zh;q=0.9',
            'cache-control': 'no-cache',
            'origin': 'https://www.goofish.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://www.goofish.com/',
            'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        })
        
    def clear_duplicate_cookies(self):
        """清理重复的cookies"""
        # 创建一个新的CookieJar
        new_jar = requests.cookies.RequestsCookieJar()
        
        # 记录已经添加过的cookie名称
        added_cookies = set()
        
        # 按照cookies列表的逆序遍历（最新的通常在后面）
        cookie_list = list(self.session.cookies)
        cookie_list.reverse()
        
        for cookie in cookie_list:
            # 如果这个cookie名称还没有添加过，就添加到新jar中
            if cookie.name not in added_cookies:
                new_jar.set_cookie(cookie)
                added_cookies.add(cookie.name)
                
        # 替换session的cookies
        self.session.cookies = new_jar
        
        # 更新完cookies后，更新.env文件
        self.update_env_cookies()
        
    def update_env_cookies(self):
        """更新.env文件中的COOKIES_STR"""
        try:
            # 获取当前cookies的字符串形式
            cookie_str = '; '.join([f"{cookie.name}={cookie.value}" for cookie in self.session.cookies])
            
            # 读取.env文件
            env_path = os.path.join(os.getcwd(), '.env')
            if not os.path.exists(env_path):
                logger.warning(".env文件不存在，无法更新COOKIES_STR")
                return
                
            with open(env_path, 'r', encoding='utf-8') as f:
                env_content = f.read()
                
            # 使用正则表达式替换COOKIES_STR的值
            if 'COOKIES_STR=' in env_content:
                new_env_content = re.sub(
                    r'COOKIES_STR=.*', 
                    f'COOKIES_STR={cookie_str}',
                    env_content
                )
                
                # 写回.env文件
                with open(env_path, 'w', encoding='utf-8') as f:
                    f.write(new_env_content)
                    
                logger.info("已更新.env文件中的COOKIES_STR")
            else:
                logger.warning(".env文件中未找到COOKIES_STR配置项")
        except Exception as e:
            logger.warning(f"更新.env文件失败: {str(e)}")
        
    def get_token(self, device_id, retry_count=0):
        if retry_count >= 3:  # 最多重试3次
            logger.error("获取token失败，重试次数过多")
            return {"error": "获取token失败，重试次数过多"}
            
        params = {
            'jsv': '2.7.2',
            'appKey': '34839810',
            't': str(int(time.time()) * 1000),
            'sign': '',
            'v': '1.0',
            'type': 'originaljson',
            'accountSite': 'xianyu',
            'dataType': 'json',
            'timeout': '20000',
            'api': 'mtop.taobao.idlemessage.pc.login.token',
            'sessionOption': 'AutoLoginOnly',
            'spm_cnt': 'a21ybx.im.0.0',
        }
        data_val = '{"appKey":"444e9908a51d1cb236a27862abc769c9","deviceId":"' + device_id + '"}'
        data = {
            'data': data_val,
        }
        
        # 简单获取token，信任cookies已清理干净
        token = self.session.cookies.get('_m_h5_tk', '').split('_')[0]
        
        sign = generate_sign(params['t'], token, data_val)
        params['sign'] = sign
        response = self.session.post('https://h5api.m.goofish.com/h5/mtop.taobao.idlemessage.pc.login.token/1.0/', params=params, data=data)
        res_json = response.json()
        if isinstance(res_json, dict):
            ret_value = res_json.get('ret', [])
            # 检查ret是否包含成功信息
            if not any('SUCCESS::调用成功' in ret for ret in ret_value):
                logger.warning(f"API调用失败，错误信息: {ret_value}")
                # 处理响应中的Set-Cookie
                if 'Set-Cookie' in response.headers:
                    logger.info("检测到Set-Cookie，等待cookie更新")
                    self.clear_duplicate_cookies()
                time.sleep(0.5)
                return self.get_token(device_id, retry_count + 1)
        return res_json

    def get_item_info(self, item_id, retry_count=0):
        """获取商品信息，自动处理token失效的情况"""
        if retry_count >= 3:  # 最多重试3次
            logger.error("获取商品信息失败，重试次数过多")
            return {"error": "获取商品信息失败，重试次数过多"}
            
        params = {
            'jsv': '2.7.2',
            'appKey': '34839810',
            't': str(int(time.time()) * 1000),
            'sign': '',
            'v': '1.0',
            'type': 'originaljson',
            'accountSite': 'xianyu',
            'dataType': 'json',
            'timeout': '20000',
            'api': 'mtop.taobao.idle.pc.detail',
            'sessionOption': 'AutoLoginOnly',
            'spm_cnt': 'a21ybx.im.0.0',
        }
        
        data_val = '{"itemId":"' + item_id + '"}'
        data = {
            'data': data_val,
        }
        
        # 简单获取token，信任cookies已清理干净
        token = self.session.cookies.get('_m_h5_tk', '').split('_')[0]
        
        sign = generate_sign(params['t'], token, data_val)
        params['sign'] = sign
        
        response = self.session.post(
            'https://h5api.m.goofish.com/h5/mtop.taobao.idle.pc.detail/1.0/', 
            params=params, 
            data=data
        )
        
        res_json = response.json()
        # 检查返回状态
        if isinstance(res_json, dict):
            ret_value = res_json.get('ret', [])
            # 检查ret是否包含成功信息
            if not any('SUCCESS::调用成功' in ret for ret in ret_value):
                logger.warning(f"API调用失败，错误信息: {ret_value}")
                # 处理响应中的Set-Cookie
                if 'Set-Cookie' in response.headers:
                    logger.info("检测到Set-Cookie，等待cookie更新")
                    self.clear_duplicate_cookies()
                time.sleep(0.5)
                return self.get_item_info(item_id, retry_count + 1)
        return res_json
