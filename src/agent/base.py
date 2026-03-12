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
            # First, invoke to check if tools are needed
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

                # Stream final response after tool execution
                async for chunk in self.llm_with_tools.astream(lc_messages):
                    if hasattr(chunk, 'content'):
                        yield chunk.content
            else:
                # No tool calls needed, stream the response
                async for chunk in self.llm_with_tools.astream(lc_messages):
                    if hasattr(chunk, 'content'):
                        yield chunk.content
        else:
            # No tools, just stream
            async for chunk in self.llm.astream(lc_messages):
                if hasattr(chunk, 'content'):
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
