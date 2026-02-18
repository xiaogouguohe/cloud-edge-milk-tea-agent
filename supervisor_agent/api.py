from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import sys
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware

# 添加项目根目录到路径，以便导入相关模块
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from supervisor_agent.supervisor_agent import SupervisorAgent

app = FastAPI(title="Milk Tea Supervisor API")

# 配置 CORS，允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 使用字典存储会话，key 为 session_id
# 注意：在生产环境中应该使用 Redis 等持久化存储
sessions: Dict[str, SupervisorAgent] = {}

class ChatRequest(BaseModel):
    message: str
    user_id: str
    chat_id: Optional[str] = "default"
    # 注意：SupervisorAgent 内部管理自己的 history，
    # 但为了兼容前端可能的 history 传递，我们保留这个字段
    history: Optional[List[Dict]] = None

class ChatResponse(BaseModel):
    reply: str
    session_id: str
    role: Optional[str] = None

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        session_id = f"{request.user_id}_{request.chat_id}"
        
        # 获取或创建该会话的 SupervisorAgent 实例
        if session_id not in sessions:
            sessions[session_id] = SupervisorAgent(
                user_id=request.user_id, 
                chat_id=request.chat_id
            )
        
        agent = sessions[session_id]
        
        # 调用 SupervisorAgent 的 chat 方法
        # SupervisorAgent 会自动处理身份识别、任务分解和路由
        reply = agent.chat(user_input=request.message)
        
        return ChatResponse(
            reply=reply,
            session_id=session_id,
            role=agent.role
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/clear")
async def clear_session(user_id: str, chat_id: str = "default"):
    session_id = f"{user_id}_{chat_id}"
    if session_id in sessions:
        sessions[session_id].clear_history()
        return {"status": "success", "message": f"Session {session_id} cleared"}
    return {"status": "error", "message": "Session not found"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    # 启动在 8000 端口
    uvicorn.run(app, host="0.0.0.0", port=8000)
