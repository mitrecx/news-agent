"""FastAPI server for news agent"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import os
import json
import logging

from .models import ChatRequest, ChatResponse, HealthResponse
from ..agent.base import NewsAgent
from ..agent.config import get_settings
from ..tools import fetch_weibo_hot_search
from ..auth import db, router as auth_router, get_current_user
from ..auth.models import User

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global agent instance
agent: NewsAgent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager"""
    # Initialize database
    settings = get_settings()
    try:
        await db.connect()
    except Exception as e:
        print(f"✗ Failed to connect to database: {e}")
        raise

    # Initialize agent
    global agent
    try:
        # Initialize agent with tools
        tools = [fetch_weibo_hot_search]
        agent = NewsAgent(tools=tools)
        print(f"✓ News Agent initialized with model: {settings.agent_model}")
        print(f"✓ Loaded {len(tools)} tool(s): {[t.name for t in tools]}")
    except Exception as e:
        print(f"✗ Failed to initialize agent: {e}")
        raise

    yield

    # Cleanup
    await db.disconnect()
    print("Shutting down...")


app = FastAPI(
    title="News Agent",
    description="News assistant powered by LangChain and DeepSeek",
    version="0.1.0",
    lifespan=lifespan
)

# Include auth router
app.include_router(auth_router)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="ok",
        agent_ready=agent is not None
    )


@app.get("/api/tools/test")
async def test_weibo_tool():
    """Test weibo hot search tool directly"""
    try:
        result = await fetch_weibo_hot_search.invoke({"limit": 5})
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Chat with the news agent (requires authentication)

    Args:
        request: Chat request with message and optional history
        current_user: Authenticated user

    Returns:
        Chat response from the agent
    """
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    # 打印请求日志
    user_info = f"用户: {current_user.username}"
    logger.info(f"📨 收到聊天请求 ({user_info}): {request.message[:50]}...")
    print(f"\n{'='*60}")
    print(f"💬 {user_info}")
    print(f"💬 用户消息: {request.message}")
    print(f"📜 历史记录数: {len(request.history) if request.history else 0}")
    print(f"{'='*60}\n")

    # Convert history if provided
    history = None
    if request.history:
        history = [msg.model_dump() for msg in request.history]

    try:
        response = await agent.chat(request.message, history)

        # 打印响应日志
        logger.info(f"✓ 响应生成成功: {len(response)} 字符")
        print(f"\n{'='*60}")
        print(f"✅ Agent 响应:")
        print(f"{response[:200]}{'...' if len(response) > 200 else ''}")
        print(f"{'='*60}\n")

        return ChatResponse(response=response)
    except Exception as e:
        logger.error(f"✗ 响应生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Chat with the news agent with streaming response (requires authentication)

    Args:
        request: Chat request with message and optional history
        current_user: Authenticated user

    Returns:
        Streaming response from the agent
    """
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    # 打印请求日志
    user_info = f"用户: {current_user.username}"
    logger.info(f"📨 [流式] 收到聊天请求 ({user_info}): {request.message[:50]}...")
    print(f"\n{'='*60}")
    print(f"💬 [流式] {user_info}")
    print(f"💬 [流式] 用户消息: {request.message}")
    print(f"📜 历史记录数: {len(request.history) if request.history else 0}")
    print(f"{'='*60}\n")

    # Convert history if provided
    history = None
    if request.history:
        history = [msg.model_dump() for msg in request.history]

    async def generate():
        """Generate streaming response"""
        try:
            full_response = ""
            async for chunk in agent.chat_stream(request.message, history):
                full_response += chunk
                # Send SSE format
                yield f"data: {json.dumps({'content': chunk})}\n\n"

            # 打印完成日志
            logger.info(f"✓ [流式] 响应生成完成: {len(full_response)} 字符")
            print(f"\n{'='*60}")
            print(f"✅ [流式] Agent 响应:")
            print(f"{full_response[:200]}{'...' if len(full_response) > 200 else ''}")
            print(f"{'='*60}\n")

            # Send end signal
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"✗ [流式] 响应生成失败: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# Mount static files for frontend
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")

@app.get("/")
async def serve_frontend():
    """Serve frontend"""
    index_file = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "News Agent API - Frontend not found"}


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(app, host=settings.host, port=settings.port)
