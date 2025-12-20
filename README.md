# 云边奶茶铺 AI 智能助手

云边奶茶铺的 AI 智能助手系统，基于 Python 和阿里云 DashScope 实现。

## 项目简介

云边奶茶铺智能助手，支持一站式咨询、点单与反馈。当前版本实现了基础的对话功能。

## 功能特性

- ✅ 基础对话功能（Terminal 交互）
- ✅ 直接使用 DashScope SDK（无需 LangChain）
- ✅ 对话历史管理
- ✅ 轻量级实现（仅依赖 dashscope 和 python-dotenv）
- 🚧 多智能体路由（开发中）
- 🚧 子智能体集成（开发中）

## 环境要求

- Python 3.8+
- 阿里云 DashScope API Key

## 技术栈

- **DashScope SDK**: 直接调用阿里云通义千问 API
- **python-dotenv**: 环境变量管理
- **Python 标准库**: 终端交互（无需额外依赖）

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制环境变量模板文件：

```bash
cp .env.template .env
```

编辑 `.env` 文件，填入你的 DashScope API Key：

```env
DASHSCOPE_API_KEY=your_dashscope_api_key_here
DASHSCOPE_MODEL=qwen-plus
```

### 3. 运行对话程序

```bash
python chat.py
```

### 4. 使用说明

- 直接输入问题开始对话
- 输入 `quit` 或 `exit` 退出程序
- 输入 `clear` 清空对话历史

## 项目结构

```
cloud-edge-milk-tea-agent/
├── chat.py              # 主对话程序
├── config.py            # 配置文件
├── requirements.txt     # Python 依赖
├── run.sh              # 启动脚本
├── .env                 # 环境变量配置（需自行创建）
└── README.md           # 项目说明
```

## 获取 API Key

访问 [阿里云 DashScope 控制台](https://dashscope.console.aliyun.com/) 获取 API 密钥。

## 后续计划

- [ ] 实现多智能体路由功能
- [ ] 集成咨询子智能体
- [ ] 集成订单子智能体
- [ ] 集成反馈子智能体
- [ ] 实现 MCP 服务器
- [ ] 添加数据库支持
- [ ] 实现记忆管理功能

## 许可证

MIT License
