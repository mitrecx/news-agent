"""Base agent configuration using LangChain and DeepSeek"""

from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from .config import get_settings


def create_llm() -> BaseChatModel:
    """Create and configure the DeepSeek LLM instance"""
    settings = get_settings()

    return ChatOpenAI(
        model=settings.agent_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=settings.agent_temperature,
        max_tokens=settings.agent_max_tokens,
    )


class NewsAgent:
    """Basic news agent powered by DeepSeek"""

    def __init__(self, tools: list | None = None):
        """
        Initialize the news agent

        Args:
            tools: Optional list of LangChain tools to bind to the LLM
        """
        self.llm = create_llm()
        self.tools = tools or []

        # Bind tools to LLM if provided
        if self.tools:
            self.llm_with_tools = self.llm.bind_tools(self.tools)
        else:
            self.llm_with_tools = self.llm

    async def chat(self, message: str, history: list[dict] | None = None) -> str:
        """
        Send a message to the agent and get a response

        Args:
            message: User message
            history: Optional conversation history

        Returns:
            Agent response
        """
        if history is None:
            history = []

        # Build conversation from history
        messages = []
        for msg in history:
            if msg.get("role") == "user":
                messages.append(("human", msg.get("content")))
            elif msg.get("role") == "assistant":
                messages.append(("ai", msg.get("content")))

        # Add current message
        messages.append(("human", message))

        # Use LLM with tools if available
        response = await self._process_with_tools(messages)
        return response

    async def _process_with_tools(self, messages: list) -> str:
        """
        Process messages with tool support

        Args:
            messages: Message list

        Returns:
            Final response text
        """
        from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

        # Convert messages to LangChain format
        lc_messages = []
        for role, content in messages:
            if role == "human":
                lc_messages.append(HumanMessage(content=content))
            else:
                lc_messages.append(AIMessage(content=content))

        # Invoke LLM
        response = await self.llm_with_tools.ainvoke(lc_messages)

        # Handle tool calls
        if hasattr(response, 'tool_calls') and response.tool_calls:
            # Execute tool calls
            for tool_call in response.tool_calls:
                tool_name = tool_call.get('name')
                tool_args = tool_call.get('args', {})

                # Find and execute the tool
                for tool in self.tools:
                    if tool.name == tool_name:
                        result = await tool.ainvoke(tool_args)
                        # Add tool result to messages
                        lc_messages.append(response)
                        lc_messages.append(ToolMessage(
                            content=result,
                            tool_call_id=tool_call.get('id', '')
                        ))
                        break

            # Check if tool result should be returned directly
            tool_result = lc_messages[-1].content
            if tool_result.startswith("📊 微博热搜榜："):
                # Direct return for weibo hot search
                return tool_result

            # Get final response after tool execution
            final_response = await self.llm_with_tools.ainvoke(lc_messages)
            return final_response.content

        return response.content

    async def chat_stream(self, message: str, history: list[dict] | None = None):
        """
        Stream chat response from the agent

        Args:
            message: User message
            history: Optional conversation history

        Yields:
            Chunks of the response
        """
        from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
        import asyncio
        import logging
        logger = logging.getLogger(__name__)

        if history is None:
            history = []

        # Build conversation from history
        messages = []
        for msg in history:
            if msg.get("role") == "user":
                messages.append(("human", msg.get("content")))
            elif msg.get("role") == "assistant":
                messages.append(("ai", msg.get("content")))

        # Add current message
        messages.append(("human", message))

        # Convert to LangChain format
        lc_messages = []
        for role, content in messages:
            if role == "human":
                lc_messages.append(HumanMessage(content=content))
            else:
                lc_messages.append(AIMessage(content=content))

        # Check if tools are needed
        if self.tools:
            # First, check if tools are needed by invoking
            try:
                response = await asyncio.wait_for(
                    self.llm_with_tools.ainvoke(lc_messages),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                logger.error("chat_stream: ainvoke timeout")
                yield "抱歉，请求超时，请重试。"
                return
            except Exception as e:
                logger.error(f"chat_stream: ainvoke error: {e}", exc_info=True)
                yield f"抱歉，发生错误: {str(e)}"
                return

            # Handle tool calls
            if hasattr(response, 'tool_calls') and response.tool_calls:
                # Check if this is weibo hot search tool
                is_weibo_tool = any(tc.get('name') == 'fetch_weibo_hot_search' for tc in response.tool_calls)

                # Stream the initial response content (skip for weibo tool)
                if not is_weibo_tool and hasattr(response, 'content') and response.content:
                    yield response.content

                # Execute tool calls
                weibo_returned = False
                for tool_call in response.tool_calls:
                    tool_name = tool_call.get('name')
                    tool_args = tool_call.get('args', {})

                    # Find and execute the tool
                    for tool in self.tools:
                        if tool.name == tool_name:
                            try:
                                result = await asyncio.wait_for(
                                    tool.ainvoke(tool_args),
                                    timeout=60.0
                                )
                                lc_messages.append(response)
                                lc_messages.append(ToolMessage(
                                    content=result,
                                    tool_call_id=tool_call.get('id', '')
                                ))

                                # Check if result should be returned directly
                                if result.startswith("📊 微博热搜榜："):
                                    # Direct return for weibo hot search
                                    yield result
                                    weibo_returned = True
                            except asyncio.TimeoutError:
                                logger.error(f"chat_stream: tool execution timeout: {tool_name}")
                                yield "\n\n抱歉，工具执行超时，请重试。"
                                return
                            except Exception as e:
                                logger.error(f"chat_stream: tool execution error: {e}", exc_info=True)
                                yield f"\n\n抱歉，工具执行失败: {str(e)}"
                                return
                            break

                # Skip LLM processing if weibo hot search was returned
                if weibo_returned:
                    return

                # Stream final response after tool execution
                try:
                    async for chunk in self.llm_with_tools.astream(lc_messages):
                        if hasattr(chunk, 'content') and chunk.content:
                            yield chunk.content
                except Exception as e:
                    logger.error(f"chat_stream: final response streaming error: {e}", exc_info=True)
                    yield f"\n\n抱歉，生成响应时出错: {str(e)}"
            else:
                # No tool calls needed, stream the response
                if hasattr(response, 'content') and response.content:
                    yield response.content
                else:
                    yield "抱歉，我没有收到有效的响应。"
        else:
            # No tools, just stream
            async for chunk in self.llm.astream(lc_messages):
                if hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content

    def chat_sync(self, message: str, history: list[dict] | None = None) -> str:
        """
        Synchronous version of chat method

        Args:
            message: User message
            history: Optional conversation history

        Returns:
            Agent response
        """
        if history is None:
            history = []

        # Build conversation from history
        messages = []
        for msg in history:
            if msg.get("role") == "user":
                messages.append(("human", msg.get("content")))
            elif msg.get("role") == "assistant":
                messages.append(("ai", msg.get("content")))

        # Add current message
        messages.append(("human", message))

        # Get response
        response = self.llm.invoke(messages)
        return response.content
