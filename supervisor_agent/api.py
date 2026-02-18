from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import sys
import requests
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware

# 添加项目根目录到路径，以便导入相关模块
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from supervisor_agent.supervisor_agent import SupervisorAgent
from supervisor_agent.session_store import save_session, load_session, delete_session

app = FastAPI(title="Milk Tea Supervisor API")

# 配置 CORS，允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 内存缓存活跃会话，持久化在 session_store（SQLite）
sessions: Dict[str, SupervisorAgent] = {}

class ChatRequest(BaseModel):
    message: str
    user_id: str
    chat_id: Optional[str] = "default"
    role: Optional[str] = None  # 前端登录时传入的身份：customer / staff
    history: Optional[List[Dict]] = None

class SetIdentityRequest(BaseModel):
    user_id: str
    chat_id: Optional[str] = "default"
    role: str  # customer / staff

class ChatResponse(BaseModel):
    reply: str
    session_id: str
    role: Optional[str] = None
    pending_action: Optional[dict] = None  # 如 {"type": "product_update", "productName", "current", "proposed"}

def _get_or_create_agent(session_id: str, user_id: str, chat_id: str) -> SupervisorAgent:
    """获取或创建 Agent，优先从持久化加载"""
    if session_id in sessions:
        return sessions[session_id]
    agent = SupervisorAgent(user_id=user_id, chat_id=chat_id)
    loaded = load_session(session_id)
    if loaded:
        _user_id, _chat_id, role, history = loaded
        if role is not None:
            agent.role = role
        if history:
            agent.history = history
    sessions[session_id] = agent
    return agent


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        session_id = f"{request.user_id}_{request.chat_id}"
        agent = _get_or_create_agent(session_id, request.user_id, request.chat_id or "default")
        
        if request.role:
            agent.role = request.role
        
        result = agent.chat(user_input=request.message)
        
        # 持久化短期记忆（进程退出后可恢复）
        save_session(session_id, request.user_id, request.chat_id or "default", agent.role, agent.history)
        
        if isinstance(result, dict):
            reply = result.get("output", "")
            pending_action = result.get("pending_action")
            return ChatResponse(
                reply=reply,
                session_id=session_id,
                role=agent.role,
                pending_action=pending_action
            )
        return ChatResponse(
            reply=result,
            session_id=session_id,
            role=agent.role
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/set-identity")
async def set_identity(request: SetIdentityRequest):
    """设置会话身份（登录时调用）"""
    session_id = f"{request.user_id}_{request.chat_id}"
    agent = _get_or_create_agent(session_id, request.user_id, request.chat_id or "default")
    agent.role = request.role
    save_session(session_id, request.user_id, request.chat_id or "default", agent.role, agent.history)
    return {"status": "success", "role": request.role}

@app.post("/api/clear")
async def clear_session(user_id: str, chat_id: str = "default"):
    """清空会话历史，并删除持久化数据。下次对话将重新开始。"""
    session_id = f"{user_id}_{chat_id}"
    if session_id in sessions:
        sessions[session_id].clear_history()
        del sessions[session_id]
    delete_session(session_id)
    return {"status": "success", "message": f"Session {session_id} cleared"}

class ProductUpdateRequest(BaseModel):
    productName: str
    price: Optional[float] = None
    stock: Optional[int] = None

@app.post("/api/product/update")
async def product_update(req: ProductUpdateRequest):
    """执行产品修改（供前端确认按钮和测试直接调用，绕过前端交互）"""
    if req.price is None and req.stock is None:
        raise HTTPException(status_code=400, detail="请至少指定 price 或 stock")
    try:
        from service_discovery import ServiceDiscovery
        sd = ServiceDiscovery(method="config")
        svc = sd.discover("order-mcp-server")
        if not svc:
            raise HTTPException(status_code=503, detail="order-mcp-server 不可用")
        url = f"{svc['url']}/mcp/tools/order-update-product/invoke"
        params = {"productName": req.productName}
        if req.price is not None:
            params["price"] = req.price
        if req.stock is not None:
            params["stock"] = req.stock
        resp = requests.post(url, json={"parameters": params}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "success":
            raise HTTPException(status_code=400, detail=data.get("error", "修改失败"))
        result = data.get("result", "")
        return {"status": "success", "message": result}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"调用订单服务失败: {str(e)}")

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    # 启动在 8000 端口
    uvicorn.run(app, host="0.0.0.0", port=8000)
