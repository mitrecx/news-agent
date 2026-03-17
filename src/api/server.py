"""FastAPI server for news agent"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
from datetime import datetime
import os
import json
import logging

from .models import ChatRequest, ChatResponse, HealthResponse
from ..agent.base import NewsAgent
from ..agent.config import get_settings
from ..tools import fetch_weibo_hot_search
from ..auth import db, router as auth_router, get_current_user
from ..auth.models import User, Conversation, ConversationUpdate
from ..auth.conversation_service import ConversationService
from ..tools.weibo_cache import WeiboHotSearchCache

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


# ========== Real-time Weibo Hot Search Endpoints ==========

@app.get("/api/weibo/hot")
async def get_weibo_hot_search(
    limit: int = 50,
    current_user: User = Depends(get_current_user)
):
    """
    Get real-time weibo hot search (not from cache, live data)

    Args:
        limit: Number of hot search items to return (default: 50)
        current_user: Authenticated user

    Returns:
        List of hot search items with ranking, title, description, and metrics
    """
    try:
        # Use ainvoke for async tool invocation
        result = await fetch_weibo_hot_search.ainvoke({"limit": limit})

        # Parse the result to extract structured data
        # The result is a formatted string, so we need to parse it
        lines = result.strip().split('\n')
        items = []

        for line in lines:
            line = line.strip()
            if not line or line.startswith('=') or line.startswith('[') or line.startswith('✅'):
                continue

            # Try to parse format like "1. 热搜标题 (热度: 热)"
            if line[0].isdigit() and '. ' in line:
                # Remove leading number and dot
                content = line.split('. ', 1)[1].strip()

                # Extract metrics from parentheses if present
                metrics = None
                title = content

                if ' (热度: ' in content:
                    title_part, metrics_part = content.split(' (热度: ', 1)
                    title = title_part.strip()
                    # Remove trailing parenthesis
                    metrics = metrics_part.rstrip(')')

                # Extract rank
                rank_str = line.split('. ')[0]
                try:
                    rank = int(rank_str)
                except ValueError:
                    continue

                items.append({
                    "rank": rank,
                    "title": title,
                    "description": "",
                    "metrics": metrics,
                })

        return {
            "items": items,
            "total": len(items),
            "limit": limit,
            "raw": result  # Include raw text for reference
        }
    except Exception as e:
        logger.error(f"Failed to fetch weibo hot search: {e}")
        raise HTTPException(status_code=500, detail=f"获取微博热搜失败: {str(e)}")


# ========== Conversation Management Endpoints ==========

@app.get("/api/conversations")
async def list_conversations(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user)
):
    """Get user's conversation list"""
    async with db.pool.acquire() as conn:
        conversations = await ConversationService.list_conversations(
            conn, current_user.id, limit, offset
        )
        return conversations


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get a single conversation"""
    async with db.pool.acquire() as conn:
        conversation = await ConversationService.get_conversation_by_id(
            conn, conversation_id, current_user.id
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation


@app.put("/api/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: int,
    update_data: ConversationUpdate,
    current_user: User = Depends(get_current_user)
):
    """Rename conversation"""
    async with db.pool.acquire() as conn:
        conversation = await ConversationService.update_conversation(
            conn, conversation_id, current_user.id, update_data.title
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user)
):
    """Delete conversation"""
    async with db.pool.acquire() as conn:
        success = await ConversationService.delete_conversation(
            conn, conversation_id, current_user.id
        )
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {"message": "Conversation deleted"}


@app.get("/api/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get all messages in a conversation"""
    async with db.pool.acquire() as conn:
        messages = await ConversationService.get_messages(
            conn, conversation_id, current_user.id
        )
        return {
            "conversation_id": conversation_id,
            "messages": [
                {"role": msg["role"], "content": msg["content"]}
                for msg in messages
            ]
        }


# ========== Weibo Hot Search Cache Endpoints ==========

@app.get("/api/weibo/cache")
async def get_weibo_cache(
    limit: int = 15,
    offset: int = 0,
    search: str = None,
    start_date: str = None,
    end_date: str = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get weibo hot search cache entries with filtering

    Args:
        limit: Number of entries to return (default: 15)
        offset: Offset for pagination (default: 0)
        search: Search query to filter by title (optional, fuzzy search)
        start_date: Start date for filtering updated_at (ISO format, optional)
        end_date: End date for filtering updated_at (ISO format, optional)
        current_user: Authenticated user
    """
    cache = WeiboHotSearchCache(pool=db.pool)

    async with db.pool.acquire() as conn:
        # Build WHERE conditions
        conditions = []
        params = []
        param_count = 0

        if search:
            param_count += 1
            conditions.append(f"title ILIKE ${param_count}")
            params.append(f"%{search}%")

        if start_date:
            param_count += 1
            # Parse ISO format string to datetime object
            start_dt = datetime.fromisoformat(start_date)
            conditions.append(f"updated_at >= ${param_count}")
            params.append(start_dt)

        if end_date:
            param_count += 1
            # Parse ISO format string to datetime object
            end_dt = datetime.fromisoformat(end_date)
            conditions.append(f"updated_at <= ${param_count}")
            params.append(end_dt)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Get entries with filters
        query = f"""
            SELECT title_hash, title, description, description_source,
                   created_at, updated_at, expires_at
            FROM weibo_hot_search_cache
            {where_clause}
            ORDER BY updated_at DESC
            LIMIT ${param_count + 1} OFFSET ${param_count + 2}
        """
        rows = await conn.fetch(query, *params, limit, offset)

        # Get total count
        count_query = f"SELECT COUNT(*) FROM weibo_hot_search_cache {where_clause}"
        total_count = await conn.fetchval(count_query, *params)

        return {
            "items": [
                {
                    "title_hash": row["title_hash"],
                    "title": row["title"],
                    "description": row["description"],
                    "description_source": row["description_source"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                    "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
                }
                for row in rows
            ],
            "total": total_count,
            "limit": limit,
            "offset": offset,
        }


@app.get("/api/weibo/cache/stats")
async def get_weibo_cache_stats(current_user: User = Depends(get_current_user)):
    """
    Get weibo hot search cache statistics

    Args:
        current_user: Authenticated user
    """
    cache = WeiboHotSearchCache(pool=db.pool)
    stats = await cache.get_stats()
    return stats


@app.delete("/api/weibo/cache/expired")
async def delete_expired_cache(current_user: User = Depends(get_current_user)):
    """
    Delete expired cache entries

    Args:
        current_user: Authenticated user
    """
    cache = WeiboHotSearchCache(pool=db.pool)
    deleted_count = await cache.delete_expired()
    return {"message": f"Deleted {deleted_count} expired cache entries", "count": deleted_count}


# ========== Helper function to generate conversation title ==========

async def generate_title_with_ai(first_message: str, first_response: str) -> str:
    """策略1: 使用 AI 生成简洁的对话标题"""
    try:
        # Create a simple prompt for title generation
        prompt = f"""根据以下对话内容，生成一个简洁的标题（不超过10个字）：

用户：{first_message[:100]}

只返回标题，不要其他内容。"""

        # Use the agent to generate title (non-streaming)
        title = await agent.chat(prompt, history=None)

        # Clean up the title
        title = title.strip()
        # Remove quotes if present
        title = title.strip('"\'""''《》')
        # Limit to 15 characters
        if len(title) > 15:
            title = title[:15] + "..."

        return title if title else "新对话"
    except Exception as e:
        logger.error(f"Failed to generate title with AI: {e}")
        # Fallback to first 15 characters of user message
        return first_message[:15] + ("..." if len(first_message) > 15 else "")


def generate_title_by_truncate(first_message: str, first_response: str) -> str:
    """策略2: 截取用户问题前7个字作为标题"""
    # Take first 7 characters of user message
    title = first_message[:7]

    # Add ellipsis if message is longer
    if len(first_message) > 7:
        title += "..."

    return title if title else "新对话"


async def generate_conversation_title(first_message: str, first_response: str) -> str:
    """根据配置的策略生成对话标题"""
    settings = get_settings()
    if settings.title_generation_strategy == "ai":
        return await generate_title_with_ai(first_message, first_response)
    else:  # truncate
        return generate_title_by_truncate(first_message, first_response)



@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Chat with the news agent (requires authentication)

    Args:
        request: Chat request with message, optional history, and optional conversation_id
        current_user: Authenticated user

    Returns:
        Chat response from the agent
    """
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    conversation_id = request.conversation_id
    async with db.pool.acquire() as conn:
        # Create or get conversation
        if not conversation_id:
            # Create new conversation with default title (will be updated after AI responds)
            conversation = await ConversationService.create_conversation(
                conn, current_user.id, "新对话"
            )
            conversation_id = conversation["id"]
        else:
            # Verify conversation belongs to user
            conversation = await ConversationService.get_conversation_by_id(
                conn, conversation_id, current_user.id
            )
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")

        # Save user message
        await ConversationService.add_message(
            conn, conversation_id, "user", request.message
        )

        # Get message history for agent
        history = await ConversationService.get_message_history_for_agent(
            conn, conversation_id, current_user.id, exclude_last=True
        )

    # 打印请求日志
    user_info = f"用户: {current_user.username}"
    logger.info(f"📨 收到聊天请求 ({user_info}): {request.message[:50]}...")
    print(f"\n{'='*60}")
    print(f"💬 {user_info}")
    print(f"💬 用户消息: {request.message}")
    print(f"📜 对话ID: {conversation_id}")
    print(f"📜 历史记录数: {len(history) if history else 0}")
    print(f"{'='*60}\n")

    try:
        response = await agent.chat(request.message, history)

        # Save assistant response
        async with db.pool.acquire() as conn:
            await ConversationService.add_message(
                conn, conversation_id, "assistant", response
            )

            # Generate AI title if this is still "新对话"
            conversation = await ConversationService.get_conversation_by_id(
                conn, conversation_id, current_user.id
            )
            if conversation and conversation["title"] == "新对话":
                # Get messages to generate title
                messages = await ConversationService.get_messages(
                    conn, conversation_id, current_user.id
                )
                if len(messages) >= 2:
                    # Find first user and assistant messages
                    first_user_msg = next((m for m in messages if m["role"] == "user"), None)
                    first_assistant_msg = next((m for m in messages if m["role"] == "assistant"), None)
                    if first_user_msg and first_assistant_msg:
                        title = await generate_conversation_title(
                            first_user_msg["content"],
                            first_assistant_msg["content"]
                        )
                        await ConversationService.update_conversation(
                            conn, conversation_id, current_user.id, title
                        )

            await ConversationService.update_conversation_timestamp(conn, conversation_id)

        # 打印响应日志
        logger.info(f"✓ 响应生成成功: {len(response)} 字符")
        print(f"\n{'='*60}")
        print(f"✅ Agent 响应:")
        print(f"{response[:200]}{'...' if len(response) > 200 else ''}")
        print(f"{'='*60}\n")

        return ChatResponse(response=response, conversation_id=conversation_id)
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
        request: Chat request with message, optional history, and optional conversation_id
        current_user: Authenticated user

    Returns:
        Streaming response from the agent
    """
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    conversation_id = request.conversation_id
    async with db.pool.acquire() as conn:
        # Create or get conversation
        if not conversation_id:
            conversation = await ConversationService.create_conversation(
                conn, current_user.id, "新对话"
            )
            conversation_id = conversation["id"]
        else:
            conversation = await ConversationService.get_conversation_by_id(
                conn, conversation_id, current_user.id
            )
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")

        # Save user message
        await ConversationService.add_message(
            conn, conversation_id, "user", request.message
        )

        # Get message history for agent
        history = await ConversationService.get_message_history_for_agent(
            conn, conversation_id, current_user.id, exclude_last=True
        )

    # 打印请求日志
    user_info = f"用户: {current_user.username}"
    logger.info(f"📨 [流式] 收到聊天请求 ({user_info}): {request.message[:50]}...")
    print(f"\n{'='*60}")
    print(f"💬 [流式] {user_info}")
    print(f"💬 [流式] 用户消息: {request.message}")
    print(f"📜 对话ID: {conversation_id}")
    print(f"📜 历史记录数: {len(history) if history else 0}")
    print(f"{'='*60}\n")

    async def generate():
        """Generate streaming response"""
        try:
            full_response = ""

            # Send start signal
            yield f"data: {json.dumps({'type': 'start', 'message': '正在处理您的请求...'})}\n\n"

            # Stream the response
            async for chunk in agent.chat_stream(request.message, history):
                full_response += chunk
                # Send SSE format
                yield f"data: {json.dumps({'content': chunk})}\n\n"

            # Send saving indicator
            yield f"data: {json.dumps({'type': 'progress', 'message': '正在保存对话...'})}\n\n"

            # Save assistant response
            async with db.pool.acquire() as conn:
                await ConversationService.add_message(
                    conn, conversation_id, "assistant", full_response
                )

                # Generate AI title if this is still "新对话"
                conversation = await ConversationService.get_conversation_by_id(
                    conn, conversation_id, current_user.id
                )
                if conversation and conversation["title"] == "新对话":
                    # Send title generation progress
                    yield f"data: {json.dumps({'type': 'progress', 'message': '正在生成对话标题...'})}\n\n"
                    # For streaming, we have the first user message and full response
                    title = await generate_conversation_title(request.message, full_response)
                    await ConversationService.update_conversation(
                        conn, conversation_id, current_user.id, title
                    )
                    logger.info(f"✓ [流式] 对话标题已生成: {title}")

                await ConversationService.update_conversation_timestamp(conn, conversation_id)

            # 打印完成日志
            logger.info(f"✓ [流式] 响应生成完成: {len(full_response)} 字符")

            # Send end signal with conversation_id to ensure onComplete is called exactly once
            yield f"data: {json.dumps({'conversation_id': conversation_id, 'done': True})}\n\n"
        except Exception as e:
            logger.error(f"✗ [流式] 响应生成失败: {e}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# Note: Frontend now runs separately on http://localhost:6173 (Vue dev server)
# This root endpoint returns API status
@app.get("/")
async def root():
    """Root endpoint - API status"""
    return {"message": "News Agent API is running", "frontend": "http://localhost:6173"}


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(app, host=settings.host, port=settings.port)
