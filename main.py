import json
import subprocess
import platform
import webbrowser
import os
from pathlib import Path
from datetime import datetime, timedelta

from fastapi import FastAPI, Request, Form, HTTPException, status, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session
from sqlalchemy.orm import sessionmaker, scoped_session
from pydantic import BaseModel

from db import init_db, engine
from db_init import seed
from models import Employee, Project, Task, Conversation, ChatSession
from auth import verify_password, get_password_hash, create_access_token, decode_token, get_user_by_email
from config import ACCESS_TOKEN_EXPIRE_MINUTES
from llm_manager import stream_agent_response

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
SYSTEM_PROMPT_TEMPLATE = """You are a corporate environment assistant. You MUST use tools to answer questions - NEVER make up information.

CURRENT DATE & TIME:
{datetime_context}

CURRENT USER (logged in):
{user_context}

CRITICAL ANTI-HALLUCINATION RULES:
- NEVER invent, guess, or fabricate any data, facts, names, dates, or content
- NEVER answer factual questions without first calling the appropriate tool
- If you don't have information from a tool response, say "I don't have that information" or "I couldn't find that in the data"
- If a tool returns no results, tell the user explicitly - do NOT make up an answer
- ONLY provide information that comes directly from tool responses
- For questions about "me", "my", "who am I" - use the CURRENT USER info above, no tool needed
- For questions about current time/date - use the CURRENT DATE & TIME info above, no tool needed

AVAILABLE TOOLS:

DOCUMENT TOOLS (for uploaded PDFs/files):
- search_documents: Call this FIRST for ANY question about uploaded content, guides, manuals, instructions, PDFs, or file content. ALWAYS use this before answering document questions.
- list_uploaded_documents: Shows what documents are available
- clear_uploaded_documents: Clears all uploaded documents

DATABASE TOOLS (for company records):
- list_employees: List all employees
- get_employee(email=..., employee_id=...): Get specific employee by email or ID
- list_projects: List all projects
- get_project(project_id=...): Get specific project by ID
- list_tasks: List all tasks
- get_task(task_id=...): Get specific task by ID
- create_employee, create_project, create_task: To add records (requires permissions)
- delete_employee, delete_project, delete_task: To delete records (admin only)

SEARCH TOOLS:
- web_search: Search the internet for ANY current information, news, facts, trends, or topics. Use this for ALL web search requests. Present the results clearly with titles and key info.
- web_search_news: Search specifically for recent news articles. Use for current events and breaking news.
- open_browser_search: Opens Google in the browser - use ONLY when user specifically wants to open the browser.

MANDATORY WORKFLOW:
1. User asks about "me/my info" → Use CURRENT USER info from context above
2. User asks about time/date → Use CURRENT DATE & TIME info from context above
3. User asks about documents/files → Call search_documents FIRST, then answer based on results
4. User asks about employees/projects/tasks → Call the appropriate list/get tool FIRST
5. User asks for web search/recherche/search for X → Use web_search tool, then SUMMARIZE the results in a clear format
6. User asks about news/current events → Use web_search_news tool
7. Tool returns data → Use ONLY that data in your response
8. Tool returns empty/no results → Tell user "No results found" or "Please upload documents first"

WEB SEARCH RESPONSE FORMAT:
When presenting web search results:
- Start with a brief summary of what you found
- List the top relevant results with their titles and key information
- Include URLs so users can explore further
- If results seem incomplete, suggest refining the search or using open_browser_search

RESPONSE FORMAT:
- Be concise and factual
- Cite source document names when using document content
- Never say "Based on my knowledge" - only say "Based on the search results" or "According to the database\""""


PORT = 8080
current_user_data = {}
current_session_id = None  # Track current chat session
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def get_system_prompt():
    """Generate system prompt with current user and datetime context."""
    # Get current datetime info
    now = datetime.now()
    datetime_context = f"""- Date: {now.strftime('%A, %B %d, %Y')}
- Time: {now.strftime('%I:%M %p')}
- Week: {now.strftime('%W')} of {now.year}
- Quarter: Q{(now.month - 1) // 3 + 1}"""
    
    # Get user context
    if current_user_data:
        user_context = f"""- Name: {current_user_data.get('name', 'Unknown')}
- Email: {current_user_data.get('email', 'Unknown')}
- Role: {current_user_data.get('role', 'Unknown')}
- Department: {current_user_data.get('department', 'Not specified')}
- Access Level: {current_user_data.get('access_name', 'Unknown')} ({current_user_data.get('access_level', 1)})"""
    else:
        user_context = "No user logged in"
    
    return SYSTEM_PROMPT_TEMPLATE.format(user_context=user_context, datetime_context=datetime_context)


messages = [{"role": "system", "content": get_system_prompt()}]

class Message(BaseModel):
    user_input: str


@app.on_event("startup")
def startup():
    print("Initializing database...")
    init_db()
    try:
        seed()
    except Exception as e:
        print("Seeding skipped or failed:", e)

    webbrowser.open_new_tab(f"http://127.0.0.1:{PORT}/login")
    print("Application started and browser opened.")


# -------- Templates --------
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    # Check if user is logged in
    token = request.cookies.get("access_token")
    if not token:
        # Not logged in, redirect to login
        return RedirectResponse(url="/login")

    payload = decode_token(token)
    if not payload:
        # Invalid token, redirect to login
        return RedirectResponse(url="/login")

    # Fetch user info from DB
    with Session(engine) as s:
        user = get_user_by_email(s, payload.get("sub"))
        if not user:
            # User not found, redirect to login
            return RedirectResponse(url="/login")

    # User authenticated, render index
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@app.get("/login", response_class=HTMLResponse)
def login_get(request: Request, error: str = None):
    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@app.post("/login")
def login_post(request: Request, email: str = Form(...), password: str = Form(...)):
    global current_user_data, messages
    with Session(engine) as s:
        user = get_user_by_email(s, email)
        if not user or not verify_password(password, user.hashed_password):
            return templates.TemplateResponse("login.html", {"request": request, "error": "Incorrect credentials"})

        # Store full user details in cache
        current_user_data = {
            "id": user.id,
            "email": user.email,
            "name": user.full_name or user.email,
            "role": user.role,
            "department": user.department,
            "access_level": user.access_level,
            "access_name": {1: "read-only", 2: "write", 3: "admin"}.get(user.access_level, "unknown")
        }
        
        # Refresh messages with updated user context
        messages.clear()
        messages.append({"role": "system", "content": get_system_prompt()})
        
        token = create_access_token(user.email, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
        res = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        res.set_cookie(key="access_token", value=token, httponly=True, samesite="lax")
        return res

@app.get("/register", response_class=HTMLResponse)
def register_get(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
def register_post(email: str = Form(...), password: str = Form(...), full_name: str = Form(None)):
    with Session(engine) as s:
        if get_user_by_email(s, email):
            raise HTTPException(status_code=400, detail="Email exists")
        hashed = get_password_hash(password)
        user = Employee(email=email, full_name=full_name or "", hashed_password=hashed)
        s.add(user); s.commit()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/logout")
def logout():
    res = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    res.delete_cookie("access_token")
    return res

@app.post("/clearcache")
def clearcache(request: Request):
    from sqlmodel import select, delete
    global current_session_id
    
    messages.clear()
    messages.append({"role": "system", "content": get_system_prompt()})
    current_session_id = None  # Start a new session
    
    # Clear user's conversations from database
    token = request.cookies.get("access_token")
    if token:
        payload = decode_token(token)
        if payload:
            with Session(engine) as s:
                user = get_user_by_email(s, payload.get("sub"))
                if user:
                    # Delete user's conversations
                    s.exec(delete(Conversation).where(Conversation.user_id == user.id))
                    s.commit()
    
    return {"status": "cleared"}

def get_current_user_from_token(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    with Session(engine) as s:
        user = get_user_by_email(s, payload.get("sub"))
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
    return user

# -------- Chat streaming endpoint --------
@app.post("/api/chat/stream", response_class=PlainTextResponse)
async def chat_stream(request: Request, msg: Message):
    """Streams the agent response as Server-Sent Events (SSE)."""
    global current_session_id
    
    # Refresh system prompt with current datetime on each request
    if messages and messages[0]["role"] == "system":
        messages[0]["content"] = get_system_prompt()
    
    if len(messages) >= 12:
        # Keep system prompt (index 0) and remove oldest user/assistant pair
        messages.pop(1)
        messages.pop(1)
    
    # Get current user ID for saving conversation
    user_id = None
    token = request.cookies.get("access_token")
    if token:
        payload = decode_token(token)
        if payload:
            with Session(engine) as s:
                user = get_user_by_email(s, payload.get("sub"))
                if user:
                    user_id = user.id
    
    # Create or get session
    session_id = current_session_id
    if msg.user_input:
        with Session(engine) as s:
            # Create new session if none exists
            if not session_id:
                new_session = ChatSession(
                    user_id=user_id,
                    preview=msg.user_input[:50] + ("..." if len(msg.user_input) > 50 else "")
                )
                s.add(new_session)
                s.commit()
                s.refresh(new_session)
                session_id = new_session.id
                current_session_id = session_id
        
        # Include user context in the user message itself
        user_msg = msg.user_input
        if current_user_data:
            user_msg = f"[Context: Current user is {current_user_data.get('name', 'unknown')} with access level {current_user_data.get('access_level', 1)}]\n\n{msg.user_input}"
        messages.append({"role": "user", "content": user_msg})
        
        # Save user message to database
        with Session(engine) as s:
            conv = Conversation(session_id=session_id, user_id=user_id, role="user", content=msg.user_input)
            s.add(conv)
            s.commit()

    async def event_generator():
        try:
            full_response = ""
            tools_used = []
            
            async for data in stream_agent_response(messages):
                if data["type"] == "tool_start":
                    tools_used.append(data["tool"])
                    yield f"data: {json.dumps({'tool_start': data['tool']})}\n\n"
                elif data["type"] == "tool_end":
                    yield f"data: {json.dumps({'tool_end': data['tool']})}\n\n"
                elif data["type"] == "content":
                    full_response += data["content"]
                    yield f"data: {json.dumps({'content': data['content']})}\n\n"

            messages.append({"role": "assistant", "content": full_response})
            
            # Save assistant response to database
            with Session(engine) as s:
                conv = Conversation(
                    session_id=session_id,
                    user_id=user_id, 
                    role="assistant", 
                    content=full_response,
                    tool_name=",".join(tools_used) if tools_used else None
                )
                s.add(conv)
                s.commit()
            
            # Send done signal
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")

SessionLocal = scoped_session(sessionmaker(bind=engine))

@app.post("/analytics")
def get_analytics():
    with SessionLocal() as s:
        employee_data = s.query(Employee).all()
        departments = {}
        for emp in employee_data:
            dept = emp.department or "Unassigned"
            departments[dept] = departments.get(dept, 0) + 1

        task_data = s.query(Task).all()
        task_status = {}
        for t in task_data:
            status = t.status or "Unknown"
            task_status[status] = task_status.get(status, 0) + 1

        project_count = s.query(Project).count()
        employee_count = len(employee_data)
        task_count = len(task_data)

        analytics = {
            "employees_per_department": departments,
            "tasks_per_status": task_status,
            "total_projects": project_count,
            "total_employees": employee_count,
            "total_tasks": task_count
        }

    return JSONResponse(content=analytics)


# -------- File Upload for RAG --------
@app.post("/api/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
    """Upload a file for RAG processing."""
    from rag_manager import ingest_document
    
    # Check authentication
    token = request.cookies.get("access_token")
    if not token:
        return JSONResponse(content={"error": "Not authenticated"}, status_code=401)
    
    payload = decode_token(token)
    if not payload:
        return JSONResponse(content={"error": "Invalid token"}, status_code=401)
    
    # Check user access level (need at least write access)
    with Session(engine) as s:
        user = get_user_by_email(s, payload.get("sub"))
        if not user:
            return JSONResponse(content={"error": "User not found"}, status_code=401)
        
        # Get access_level, default to 2 (write) if column doesn't exist (old DB)
        user_access = getattr(user, 'access_level', 2)
        # Allow all authenticated users to upload (comment out the check below to restrict)
        # if user_access < 2:
        #     return JSONResponse(content={"error": f"Write access required. Your level: {user_access}"}, status_code=403)
    
    try:
        # Ensure upload directory exists
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_path = UPLOAD_DIR / file.filename
        content = await file.read()
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        print(f"File saved to: {file_path}, size: {len(content)} bytes")
        
        # Ingest into RAG with user ID
        result = ingest_document(str(file_path), {"uploaded_by": user.email}, uploaded_by=user.id)
        print(f"Ingest result: {result}")
        
        return JSONResponse(content=result)
    except Exception as e:
        print(f"Upload error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/documents")
async def list_documents(request: Request):
    """List uploaded documents."""
    from rag_manager import list_ingested_documents
    
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    docs = list_ingested_documents()
    return JSONResponse(content={"documents": docs})


@app.get("/api/user/access")
async def get_user_access(request: Request):
    """Get current user's access level."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    with Session(engine) as s:
        user = get_user_by_email(s, payload.get("sub"))
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        return JSONResponse(content={
            "email": user.email,
            "access_level": user.access_level,
            "level_name": {1: "read", 2: "write", 3: "admin"}.get(user.access_level, "unknown")
        })


@app.get("/api/conversations")
async def get_conversations(request: Request, session_id: int = None, limit: int = 50):
    """Get conversation history for current user."""
    from sqlmodel import select
    
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    with Session(engine) as s:
        user = get_user_by_email(s, payload.get("sub"))
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        if session_id:
            statement = select(Conversation).where(
                Conversation.user_id == user.id,
                Conversation.session_id == session_id
            ).order_by(Conversation.created_at.asc()).limit(limit)
        else:
            # Get current session conversations
            statement = select(Conversation).where(
                Conversation.user_id == user.id,
                Conversation.session_id == current_session_id
            ).order_by(Conversation.created_at.asc()).limit(limit)
        
        conversations = s.exec(statement).all()
        
        return JSONResponse(content={
            "conversations": [
                {
                    "id": c.id,
                    "session_id": c.session_id,
                    "role": c.role,
                    "content": c.content,
                    "tool_name": c.tool_name,
                    "created_at": c.created_at.isoformat() if c.created_at else None
                }
                for c in conversations
            ]
        })


@app.get("/api/conversations/sessions")
async def get_sessions(request: Request, limit: int = 20):
    """Get list of chat sessions for current user."""
    from sqlmodel import select
    
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    with Session(engine) as s:
        user = get_user_by_email(s, payload.get("sub"))
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        statement = select(ChatSession).where(
            ChatSession.user_id == user.id,
            ChatSession.is_active == True
        ).order_by(ChatSession.created_at.desc()).limit(limit)
        
        sessions = s.exec(statement).all()
        
        return JSONResponse(content={
            "sessions": [
                {
                    "id": sess.id,
                    "preview": sess.preview,
                    "created_at": sess.created_at.isoformat() if sess.created_at else None
                }
                for sess in sessions
            ]
        })