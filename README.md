# 🚀 Xianyu AutoAgent - 智能闲鱼客服机器人系统

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/) [![LLM Powered](https://img.shields.io/badge/LLM-powered-FF6F61)](https://platform.openai.com/)

专为闲鱼平台打造的AI值守解决方案，实现闲鱼平台7×24小时自动化值守，支持多专家协同决策、智能议价和上下文感知对话。 


## 🌟 核心特性

### 智能对话引擎
| 功能模块   | 技术实现            | 关键特性                                                     |
| ---------- | ------------------- | ------------------------------------------------------------ |
| 上下文感知 | 会话历史存储        | 轻量级对话记忆管理，完整对话历史作为LLM上下文输入            |
| 专家路由   | LLM prompt+规则路由 | 基于提示工程的意图识别 → 专家Agent动态分发，支持议价/技术/客服多场景切换 |

### 业务功能矩阵
| 模块     | 已实现                        | 规划中                       |
| -------- | ----------------------------- | ---------------------------- |
| 核心引擎 | ✅ LLM自动回复<br>✅ 上下文管理 | 🔄 情感分析增强               |
| 议价系统 | ✅ 阶梯降价策略                | 🔄 市场比价功能               |
| 技术支持 | ✅ 网络搜索整合                | 🔄 RAG知识库增强              |
| 运维监控 | ✅ 基础日志                    | 🔄 钉钉集成<br>🔄  Web管理界面 |

## 🎨效果图
<div align="center">
  <img src="./images/demo1.png" width="600" alt="客服">
  <br>
  <em>图1: 客服随叫随到</em>
</div>


<div align="center">
  <img src="./images/demo2.png" width="600" alt="议价专家">
  <br>
  <em>图2: 阶梯式议价</em>
</div>

<div align="center">
  <img src="./images/demo3.png" width="600" alt="技术专家"> 
  <br>
  <em>图3: 技术专家上场</em>
</div>

<div align="center">
  <img src="./images/log.png" width="600" alt="后台log"> 
  <br>
  <em>图4: 后台log</em>
</div>


## 🚴 快速开始

### 环境要求
- Python 3.8+

### 安装步骤
```bash
1. 克隆仓库
git clone https://github.com/shaxiu/XianyuAutoAgent.git
cd xianyu-autoagent

2. 安装依赖
pip install -r requirements.txt

3. 配置环境变量
创建一个 `.env` 文件，包含以下内容，也可直接重命名 `.env.example` ：
#必配配置
API_KEY=apikey通过模型平台获取
COOKIES_STR=填写网页端获取的cookie
MODEL_BASE_URL=模型地址
MODEL_NAME=模型名称
#可选配置
TOGGLE_KEYWORDS=接管模式切换关键词，默认为句号（输入句号切换为人工接管，再次输入则切换AI接管）

注意：默认使用的模型是通义千问，如需使用其他API，请自行修改.env文件中的模型地址和模型名称；
COOKIES_STR自行在闲鱼网页端获取cookies(网页端F12打开控制台，选择Network，点击Fetch/XHR,点击一个请求，查看cookies)

4. 创建提示词文件prompts/*_prompt.txt（也可以直接将模板名称中的_example去掉）
默认提供四个模板，可自行修改
```

### 使用方法

运行主程序：
```bash
python main.py
```

### 自定义提示词

可以通过编辑 `prompts` 目录下的文件来自定义各个专家的提示词：

- `classify_prompt.txt`: 意图分类提示词
- `price_prompt.txt`: 价格专家提示词
- `tech_prompt.txt`: 技术专家提示词
- `default_prompt.txt`: 默认回复提示词

## 🤝 参与贡献

欢迎通过 Issue 提交建议或 PR 贡献代码，请遵循 [贡献指南](https://contributing.md/)



## 🛡 注意事项

⚠️ 注意：**本项目仅供学习与交流，如有侵权联系作者删除。**

鉴于项目的特殊性，开发团队可能在任何时间**停止更新**或**删除项目**。

如需学习交流，请联系：[coderxiu@qq.com](https://mailto:coderxiu@qq.com/)

## 🧸特别鸣谢
本项目参考了以下开源项目：
https://github.com/cv-cat/XianYuApis

感谢<a href="https://github.com/cv-cat">@CVcat</a>的技术支持

## 📱 交流群
欢迎加入项目交流群，交流技术、分享经验、互助学习。
<div align="center">
  <table>
    <tr>
      <td align="center"><strong>交流群3（已满200）</strong></td>
      <td align="center"><strong>交流群4（推荐加入）</strong></td>
    </tr>
    <tr>
      <td><img src="./images/wx_group3.png" width="300px" alt="交流群1"></td>
      <td><img src="./images/wx_group4.png" width="300px" alt="交流群2"></td>
    </tr>
  </table>
</div>

## 💼 寻找机会

### <a href="https://github.com/shaxiu">@Shaxiu</a>
**🔍寻求方向**：**AI产品经理实习**  
**🛠️项目贡献：**：需求分析、agent方案设计与实现  
**📫 联系：** **email**:coderxiu@qq.com；**wx:** coderxiu

### <a href="https://github.com/cv-cat">@CVcat</a>
**🔍寻求方向**：**研发工程师实习**（python、java、逆向、爬虫）  
**🛠️项目贡献：**：闲鱼逆向工程  
**📫 联系：** **email:** 992822653@qq.com；**wx:** CVZC15751076989
## ☕ 请喝咖啡
您的☕和⭐将助力项目持续更新：

<div align="center">
  <img src="./images/wechat_pay.jpg" width="400px" alt="微信赞赏码"> 
  <img src="./images/alipay.jpg" width="400px" alt="支付宝收款码">
</div>


## 📈 Star 趋势
<a href="https://www.star-history.com/#shaxiu/XianyuAutoAgent&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=shaxiu/XianyuAutoAgent&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=shaxiu/XianyuAutoAgent&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=shaxiu/XianyuAutoAgent&type=Date" />
 </picture>
</a>

# 闲鱼自动回复API服务

这是一个基于FastAPI的闲鱼自动回复系统的API服务，可以通过API接口管理闲鱼自动回复会话。

## 功能特点

- 支持多会话并发管理
- 支持会话启动、停止及状态查询
- 支持获取闲鱼商品详情信息
- 支持自动回复与人工接管切换
- 基于WebSocket的闲鱼消息实时处理

## 环境要求

- Python 3.8+
- FastAPI
- Uvicorn
- Loguru
- Websockets
- 其他依赖库 (详见 requirements.txt)

## 安装

1. 克隆代码库：
   ```bash
   git clone https://github.com/your-repo/xy-api.git
   cd xy-api
   ```

2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 配置环境变量：
   创建一个 `.env` 文件并添加以下配置：
   ```
   LOG_LEVEL=INFO
   HEARTBEAT_INTERVAL=15
   HEARTBEAT_TIMEOUT=5
   TOKEN_REFRESH_INTERVAL=3600
   TOKEN_RETRY_INTERVAL=300
   MANUAL_MODE_TIMEOUT=3600
   MESSAGE_EXPIRE_TIME=300000
   TOGGLE_KEYWORDS=。
   PORT=8000
   ```

## 启动服务

```bash
python fastapi_server.py
```

服务将在 `http://0.0.0.0:8000` 启动。你可以通过 `http://0.0.0.0:8000/docs` 访问API文档。

## API接口

### 1. 启动新的闲鱼会话

- **接口**: `POST /start_session`
- **描述**: 启动一个新的闲鱼自动化会话
- **请求体**:
  ```json
  {
    "cookies_str": "your_cookies_string"
  }
  ```
- **响应**:
  ```json
  {
    "status": "success",
    "session_id": "uuid",
    "message": "会话启动成功"
  }
  ```

### 2. 停止闲鱼会话

- **接口**: `POST /stop_session/{session_id}`
- **描述**: 停止指定的闲鱼自动化会话
- **响应**:
  ```json
  {
    "status": "success",
    "session_id": "uuid",
    "message": "会话已停止"
  }
  ```

### 3. 获取所有活跃会话

- **接口**: `GET /sessions`
- **描述**: 获取所有当前活跃的闲鱼自动化会话
- **响应**:
  ```json
  {
    "status": "success",
    "active_sessions": [
      {
        "session_id": "uuid",
        "status": "active",
        "start_time": "2023-06-02T15:30:00"
      }
    ]
  }
  ```

### 4. 获取商品详情

- **接口**: `GET /item_detail/{session_id}/{item_id}`
- **描述**: 获取指定会话和商品 ID 的商品详情信息
- **响应**:
  ```json
  {
    "status": "success",
    "item_id": "item12345",
    "item_name": "闲鱼商品名称",
    "price": "100.00"
  }
  ```

### 5. 健康检查

- **接口**: `GET /health`
- **描述**: 检查API服务的健康状态
- **响应**:
  ```json
  {
    "status": "healthy", 
    "timestamp": "2023-06-02T15:30:00"
  }
  ```

## 客户端示例

以下是使用Python请求库调用API的示例：

```python
import requests

# 配置API基础URL
base_url = "http://localhost:8000"

# 启动会话
cookies_str = "your_cookies_string"
response = requests.post(
    f"{base_url}/start_session",
    json={"cookies_str": cookies_str}
)
session_id = response.json()["session_id"]
print(f"会话已启动，ID: {session_id}")

# 获取所有会话
response = requests.get(f"{base_url}/sessions")
print(f"活跃会话: {response.json()}")

# 获取商品详情
item_id = "item12345"
response = requests.get(f"{base_url}/item_detail/{session_id}/{item_id}")
print(f"商品详情: {response.json()}")

# 停止会话
response = requests.post(f"{base_url}/stop_session/{session_id}")
print(f"会话已停止: {response.json()}")
```

## 注意事项

1. 确保提供有效的闲鱼账号Cookie
2. 会话在闲置一段时间后会自动刷新Token
3. 可以通过环境变量定制服务的各项参数
4. 人工接管模式超时后会自动恢复自动回复模式

## 联系方式

如有问题，请联系[your-email@example.com]


## 常见问题
使用websockets==10.0避免出现  an unexpected keyword argument 'extra_headers' 问题