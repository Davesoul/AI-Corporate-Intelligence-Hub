import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from config import MCP_SERVER_URL

# Simple wrapper to initialize mcp client and expose a getter
_mcp_client = None

async def init_mcp_client():
    global _mcp_client
    if _mcp_client is None:
        # Accept a dict mapping server names to transport config
        servers = {
            "general": {
                "url": MCP_SERVER_URL,
                "transport": "streamable_http"
            }
        }
        _mcp_client = MultiServerMCPClient(servers)
    return _mcp_client

async def get_mcp_client():
    global _mcp_client
    if _mcp_client is None:
        await init_mcp_client()
    return _mcp_client
