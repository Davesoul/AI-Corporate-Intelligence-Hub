import asyncio
from langchain_mistralai import ChatMistralAI
from llm_manager_config import load_mistral_config
from langgraph.prebuilt import create_react_agent
from mcp_client import get_mcp_client
from langchain_core.messages.ai import AIMessageChunk
from typing import AsyncGenerator
from config import MISTRAL_API_KEY

# Create LLM instance
mistral_llm = ChatMistralAI(model="mistral-small-latest", api_key=MISTRAL_API_KEY, temperature=0, max_retries=2)

# Create a react agent using langgraph prebuilt with LLM + tools
# We will create an agent per request to ensure latest tools are loaded,
# or create once and refresh tools periodically.

async def create_agent():
    client = await get_mcp_client()
    tools = await client.get_tools()  # may be coroutine depending on client implementation
    print(tools)
    agent = create_react_agent(mistral_llm, tools)
    return agent

# Streaming generator that yields text chunks from agent's stream
async def stream_agent_response(messages) -> AsyncGenerator[str, None]:
    """
    messages: list of {"role":"user"/"system", "content": "..."}
    yields incremental content strings
    """
    agent = await create_agent()
    print(agent)
    # Use astream from agent if available
    response_iter = agent.astream({"messages": messages}, stream_mode="messages")
    async for chunk in response_iter:
        # chunk is often a list/tuple of MessageChunk objects
        # Convert to printable content
        if isinstance(chunk, tuple) or isinstance(chunk, list):
            print(chunk)

            msg_chunk = chunk[0]

            if isinstance(msg_chunk, AIMessageChunk):
                # Langchain message chunk may have .content or .text
                if hasattr(msg_chunk, "content") and msg_chunk.content:
                    yield msg_chunk.content
                elif hasattr(msg_chunk, "text") and msg_chunk.text:
                    yield msg_chunk.text
        else:
            # Fallback string
            yield str(chunk)
