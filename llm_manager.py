import asyncio
from langchain_mistralai import ChatMistralAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages.ai import AIMessageChunk
from langchain_core.messages import ToolMessage
from typing import AsyncGenerator, Dict, Any

from mcp_client import get_mcp_client
from config import MISTRAL_API_KEY

mistral_llm = ChatMistralAI(
    model="mistral-small-latest",
    api_key=MISTRAL_API_KEY,
    temperature=0,
    max_retries=2,
    top_p=1
)


async def create_agent():
    client = await get_mcp_client()
    tools = await client.get_tools()
    agent = create_react_agent(mistral_llm, tools)
    return agent


async def stream_agent_response(messages) -> AsyncGenerator[Dict[str, Any], None]:
    """Streams incremental content with tool usage info."""
    agent = await create_agent()
    response_iter = agent.astream({"messages": messages}, stream_mode="messages")
    
    async for chunk in response_iter:
        if isinstance(chunk, (tuple, list)):
            msg_chunk = chunk[0]
            
            # Yield tool call info
            if hasattr(msg_chunk, "tool_calls") and msg_chunk.tool_calls:
                for tc in msg_chunk.tool_calls:
                    tool_name = tc.get('name', 'unknown')
                    yield {"type": "tool_start", "tool": tool_name}
            
            # Yield tool result info
            if isinstance(msg_chunk, ToolMessage):
                yield {"type": "tool_end", "tool": msg_chunk.name if hasattr(msg_chunk, 'name') else "tool"}
            
            # Yield content
            if isinstance(msg_chunk, AIMessageChunk):
                if hasattr(msg_chunk, "content") and msg_chunk.content:
                    yield {"type": "content", "content": msg_chunk.content}
                elif hasattr(msg_chunk, "text") and msg_chunk.text:
                    yield {"type": "content", "content": msg_chunk.text}
        else:
            yield {"type": "content", "content": str(chunk)}
