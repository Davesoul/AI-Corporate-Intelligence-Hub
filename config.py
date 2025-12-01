from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8

SQLITE_DB_URL = "sqlite:///./corporate.db"
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", 3003))
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", f"http://localhost:{MCP_SERVER_PORT}/mcp/")
