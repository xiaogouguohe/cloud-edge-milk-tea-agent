# 前端 - 云边奶茶铺智能助手

## 技术栈

- React 18 + TypeScript
- Vite 5
- Axios

## 启动方式

### 1. 安装依赖

```bash
npm install
```

### 2. 启动后端 API（在项目根目录）

```bash
# 从项目根目录执行
pip install -r requirements.txt
python -m supervisor_agent.api
```

> 完整服务依赖请参考根目录 [START_SERVICES.md](../START_SERVICES.md)

### 3. 启动前端

```bash
npm run dev
```

前端运行在 http://localhost:5173，API 通过 Vite 代理转发到 http://localhost:8000。

### 4. 构建

```bash
npm run build
```
