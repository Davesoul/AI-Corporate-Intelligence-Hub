#!/usr/bin/env python3
"""MCP Server exposing tools for database CRUD, utilities, and communication."""

import os
import sys
import subprocess
import threading
import asyncio
import logging
import glob
import platform
import smtplib
import urllib.parse
import webbrowser
from datetime import datetime
from typing import Optional, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, scoped_session
from PIL import ImageGrab
import pytesseract
import pyautogui
from passlib.context import CryptContext
from mcp.server.fastmcp import FastMCP

from config import SQLITE_DB_URL, MCP_SERVER_PORT
from models import Employee, Project, Task, Document, ACCESS_LEVELS
from main import Message, chat_stream, messages, current_user_data
from rag_manager import ingest_document, query_documents, list_ingested_documents, clear_documents

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

pwd = CryptContext(schemes=["argon2"], deprecated="auto")
DB_PATH = SQLITE_DB_URL
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")


def get_current_user_access_level() -> int:
    """Get the access level of the current logged-in user."""
    if not current_user_data or "email" not in current_user_data:
        return 1  # Default to read-only if no user
    
    with SessionLocal() as s:
        user = s.query(Employee).filter(Employee.email == current_user_data["email"]).first()
        if user:
            return user.access_level
    return 1


def check_access(required_level: int) -> Optional[dict]:
    """Check if current user has required access level. Returns error dict if not authorized."""
    user_level = get_current_user_access_level()
    if user_level < required_level:
        level_names = {1: "read-only", 2: "write", 3: "admin"}
        return {
            "error": "access_denied",
            "message": f"This action requires {level_names.get(required_level, 'higher')} access. Your level: {level_names.get(user_level, 'unknown')}"
        }
    return None

mcp = FastMCP("general", port=MCP_SERVER_PORT)
mcp2 = FastMCP("UI_automation", port=4001)

Base = declarative_base()
engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
SessionLocal = scoped_session(sessionmaker(bind=engine))

def to_dict(instance):
    d = {}
    for c in instance.__table__.columns:
        v = getattr(instance, c.name)
        if isinstance(v, datetime):
            v = v.isoformat()
        d[c.name] = v
    return d


# ===== DB Tools =====

@mcp.tool(name="create_employee", description="Create a new employee (requires admin access)")
def create_employee(email: str, full_name: str = "", role: str = "Employee", department: str = "", password: Optional[str] = None, access_level: int = 1) -> dict:
    access_error = check_access(3)  # Admin required
    if access_error:
        return access_error
    
    hashed_password = pwd.hash(password)
    with SessionLocal() as s:
        if s.query(Employee).filter(Employee.email == email).first():
            return {"error": "employee_exists", "message": f"Employee with email {email} exists."}
        emp = Employee(email=email, full_name=full_name, role=role, department=department, hashed_password=hashed_password, access_level=access_level)
        s.add(emp)
        s.commit()
        s.refresh(emp)
        return to_dict(emp)


@mcp.tool(name="get_employee", description="Get employee by email or id. Pass email as string or id as number.")
def get_employee(email: str = None, employee_id: int = None) -> dict:
    with SessionLocal() as s:
        emp = None
        if employee_id:
            emp = s.get(Employee, employee_id)
        elif email:
            emp = s.query(Employee).filter(Employee.email == email).first()
        
        if emp:
            return to_dict(emp)
        return {"error": "not_found", "message": "Employee not found"}


@mcp.tool(name="list_employees", description="List employees")
def list_employees(limit: int = 100) -> List[dict]:
    with SessionLocal() as s:
        return [to_dict(e) for e in s.query(Employee).limit(limit).all()]


@mcp.tool(name="create_project", description="Create a new project (requires write access)")
def create_project(name: str, department: str = "") -> dict:
    access_error = check_access(2)  # Write access required
    if access_error:
        return access_error
    
    with SessionLocal() as s:
        project = Project(name=name, department=department)
        s.add(project)
        s.commit()
        s.refresh(project)
        return to_dict(project)


@mcp.tool(name="get_project", description="Get project by id")
def get_project(project_id: int) -> dict:
    with SessionLocal() as s:
        project = s.get(Project, project_id)
        if project:
            return to_dict(project)
        return {"error": "not_found", "message": "Project not found"}


@mcp.tool(name="list_projects", description="List all projects")
def list_projects(limit: int = 100) -> List[dict]:
    with SessionLocal() as s:
        return [to_dict(p) for p in s.query(Project).limit(limit).all()]


@mcp.tool(name="create_task", description="Create a new task (requires write access)")
def create_task(title: str, assigned_to: Optional[int] = None, project_id: Optional[int] = None,
                due_date: Optional[datetime] = None, status: str = "Pending") -> dict:
    access_error = check_access(2)  # Write access required
    if access_error:
        return access_error
    
    with SessionLocal() as s:
        task = Task(
            title=title,
            assigned_to=assigned_to,
            project_id=project_id,
            due_date=due_date,
            status=status
        )
        s.add(task)
        s.commit()
        s.refresh(task)
        return to_dict(task)


@mcp.tool(name="get_task", description="Get task by id")
def get_task(task_id: int) -> dict:
    with SessionLocal() as s:
        task = s.get(Task, task_id)
        if task:
            return to_dict(task)
        return {"error": "not_found", "message": "Task not found"}


@mcp.tool(name="list_tasks", description="List all tasks")
def list_tasks(limit: int = 100) -> List[dict]:
    with SessionLocal() as s:
        return [to_dict(t) for t in s.query(Task).limit(limit).all()]


@mcp.tool(name="update_task_status", description="Update task status by id (requires write access)")
def update_task_status(task_id: int, new_status: str) -> dict:
    access_error = check_access(2)  # Write access required
    if access_error:
        return access_error
    
    with SessionLocal() as s:
        task = s.get(Task, task_id)
        if not task:
            return {"error": "not_found"}
        task.status = new_status
        s.add(task)
        s.commit()
        s.refresh(task)
        return to_dict(task)

@mcp.tool(name="get_document", description="Get document by id")
def get_document(doc_id: int) -> dict:
    with SessionLocal() as s:
        doc = s.get(Document, doc_id)
        if doc:
            return to_dict(doc)
        return {"error": "not_found", "message": "Document not found"}


@mcp.tool(name="list_documents", description="List all documents")
def list_documents(limit: int = 100) -> List[dict]:
    with SessionLocal() as s:
        return [to_dict(d) for d in s.query(Document).limit(limit).all()]


@mcp.tool(name="web_search", description="Search the internet for current information, news, facts, or anything not available in local documents/database. Returns search results with titles, snippets and URLs. Use this for any web search request.")
def web_search(query: str, num_results: int = 10) -> dict:
    """Perform an online search and return results directly."""
    try:
        from duckduckgo_search import DDGS
        
        results = []
        with DDGS() as ddgs:
            # Text search with region and safesearch parameters for better results
            search_results = list(ddgs.text(
                query, 
                region="wt-wt",  # Worldwide
                safesearch="moderate",
                max_results=num_results
            ))
            
            for r in search_results:
                results.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "url": r.get("href", "")
                })
        
        if results:
            # Format results for better readability
            formatted_results = []
            for i, r in enumerate(results, 1):
                formatted_results.append(f"**{i}. {r['title']}**\n{r['snippet']}\n🔗 {r['url']}")
            
            return {
                "status": "success",
                "query": query,
                "results_count": len(results),
                "results": results,
                "formatted_summary": "\n\n".join(formatted_results)
            }
        else:
            return {
                "status": "no_results",
                "query": query,
                "message": f"No results found for '{query}'. Try different keywords or a more specific search."
            }
        
    except Exception as e:
        return {
            "status": "error",
            "query": query,
            "message": f"Search failed: {str(e)}. Try using 'open_browser_search' for a direct browser search."
        }


@mcp.tool(name="web_search_news", description="Search for recent news articles on a topic. Use this for current events, breaking news, and recent developments.")
def web_search_news(query: str, num_results: int = 10) -> dict:
    """Search for news articles."""
    try:
        from duckduckgo_search import DDGS
        
        results = []
        with DDGS() as ddgs:
            news_results = list(ddgs.news(
                query, 
                region="wt-wt",
                safesearch="moderate",
                max_results=num_results
            ))
            
            for r in news_results:
                results.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "url": r.get("url", ""),
                    "source": r.get("source", ""),
                    "date": r.get("date", "")
                })
        
        if results:
            # Format results for better readability
            formatted_results = []
            for i, r in enumerate(results, 1):
                date_str = f" ({r['date']})" if r['date'] else ""
                source_str = f" - {r['source']}" if r['source'] else ""
                formatted_results.append(f"**{i}. {r['title']}**{source_str}{date_str}\n{r['snippet']}\n🔗 {r['url']}")
            
            return {
                "status": "success",
                "query": query,
                "results_count": len(results),
                "results": results,
                "formatted_summary": "\n\n".join(formatted_results)
            }
        else:
            return {
                "status": "no_results",
                "query": query,
                "message": f"No news found for '{query}'. Try broader keywords or check 'web_search' for general results."
            }
        
    except Exception as e:
        return {
            "status": "error",
            "query": query,
            "message": f"News search failed: {str(e)}"
        }


@mcp.tool(name="open_browser_search", description="Opens a web search in the default browser. Use this when user explicitly wants to open a browser.")
def open_browser_search(query: str) -> str:
    url = "https://www.google.com/search?q=" + urllib.parse.quote(query)
    webbrowser.open_new_tab(url)
    return f"Opened web search for: {query}"


@mcp.tool(name="search_and_open_file", description="Searches for files matching a pattern and opens the first match.")
def search_and_open_file(pattern: str) -> str:
    matches = glob.glob(pattern, recursive=True)
    if not matches:
        return f"No files found matching: {pattern}"
    filepath = matches[0]

    if platform.system() == "Windows":
        os.startfile(filepath)
    elif platform.system() == "Darwin":
        subprocess.run(["open", filepath])
    else:
        subprocess.run(["xdg-open", filepath])
    return f"Opened file: {filepath}"


@mcp.tool(name="launch_application", description="Launches an application by its command")
def launch_application(app_command: str) -> str:
    try:
        subprocess.Popen(app_command, shell=True)
        return f"Launched application: {app_command}"
    except Exception as e:
        return f"Failed to launch {app_command}: {e}"


sender_email = os.getenv("SENDER_EMAIL", "")
sender_password = os.getenv("SENDER_PASSWORD", "")

@mcp.tool(name="send_simple_email", description="Send a simple email using SMTP.")
def send_simple_email(receiver_email: str, subject: str, body: str) -> dict:
    try:
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = receiver_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, message.as_string())

        return {"status": "sent", "to": receiver_email, "subject": subject}
    except smtplib.SMTPAuthenticationError:
        return {"error": "authentication_failed", "message": "Invalid email or password."}
    except Exception as e:
        return {"error": str(e)}

@mcp2.tool(name="take_screenshot", description="Capture screen")
def take_screenshot(save_to: Optional[str] = None) -> dict:
    try:
        img = ImageGrab.grab()
        if save_to:
            img.save(save_to)
            return {"status": "saved", "path": save_to}
        return {"status": "captured", "size": img.size}
    except Exception as e:
        return {"error": str(e)}


async def _reminder_task(seconds: float, msg: str):
    await asyncio.sleep(seconds)
    logging.info(f"[Reminder] {msg}")
    m = Message(user_input = f"[Reminder] {msg}")
    messages.append({"role": "user", "content": m.user_input})
    await chat_stream(m)


@mcp.tool(name="set_reminder", description="Schedule reminder")
def set_reminder(seconds: float, msg: str) -> dict:
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        asyncio.create_task(_reminder_task(seconds, msg))
    else:
        def _bg():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            new_loop.run_until_complete(_reminder_task(seconds, msg))
            new_loop.close()
        threading.Thread(target=_bg, daemon=True).start()
    return {"scheduled_in_seconds": seconds, "message": msg}


@mcp.tool(name="health_check", description="Server status")
def health_check() -> dict:
    return {"status": "ok", "time": datetime.now(), "db_exists": os.path.exists(DB_PATH)}


# ===== Delete Tools (Admin only) =====

@mcp.tool(name="delete_employee", description="Delete an employee by id (requires admin access)")
def delete_employee(employee_id: int) -> dict:
    access_error = check_access(3)  # Admin required
    if access_error:
        return access_error
    
    with SessionLocal() as s:
        emp = s.get(Employee, employee_id)
        if not emp:
            return {"error": "not_found", "message": f"Employee {employee_id} not found"}
        s.delete(emp)
        s.commit()
        return {"status": "deleted", "employee_id": employee_id}


@mcp.tool(name="delete_project", description="Delete a project by id (requires admin access)")
def delete_project(project_id: int) -> dict:
    access_error = check_access(3)  # Admin required
    if access_error:
        return access_error
    
    with SessionLocal() as s:
        project = s.get(Project, project_id)
        if not project:
            return {"error": "not_found", "message": f"Project {project_id} not found"}
        s.delete(project)
        s.commit()
        return {"status": "deleted", "project_id": project_id}


@mcp.tool(name="delete_task", description="Delete a task by id (requires admin access)")
def delete_task(task_id: int) -> dict:
    access_error = check_access(3)  # Admin required
    if access_error:
        return access_error
    
    with SessionLocal() as s:
        task = s.get(Task, task_id)
        if not task:
            return {"error": "not_found", "message": f"Task {task_id} not found"}
        s.delete(task)
        s.commit()
        return {"status": "deleted", "task_id": task_id}


# ===== RAG Tools =====

@mcp.tool(name="search_documents", description="IMPORTANT: Use this tool to search and retrieve information from uploaded documents (PDFs, text files, etc). Always use this tool when the user asks questions about document content, reports, uploaded files, or any information that might be in uploaded documents. Returns relevant text excerpts from the documents.")
def search_documents(query: str) -> str:
    result = query_documents(query)
    if "No relevant documents found" in result:
        return result
    return f"Here is the relevant information from the uploaded documents:\n\n{result}\n\nPlease use this information to answer the user's question accurately."


@mcp.tool(name="list_uploaded_documents", description="Use this tool when users ask: 'what documents did I upload?', 'name the documents', 'what files are uploaded?', 'list my documents', or similar questions about WHICH documents exist (not about their content). Returns names and chunk counts of all uploaded documents.")
def list_uploaded_documents() -> List[dict]:
    docs = list_ingested_documents()
    if not docs:
        return [{"message": "No documents have been uploaded yet. Use the Upload Document button to add files."}]
    return docs


@mcp.tool(name="clear_uploaded_documents", description="Clear all uploaded documents from the RAG system (requires admin access)")
def clear_uploaded_documents() -> dict:
    access_error = check_access(3)  # Admin required
    if access_error:
        return access_error
    return clear_documents()


@mcp.tool(name="get_my_access_level", description="Get the current user's access level and permissions")
def get_my_access_level() -> dict:
    level = get_current_user_access_level()
    permissions = {
        1: ["read employees", "read projects", "read tasks", "read documents", "search documents"],
        2: ["read", "create employees", "create projects", "create tasks", "update tasks", "upload documents"],
        3: ["read", "create", "update", "delete employees", "delete projects", "delete tasks", "clear documents"]
    }
    return {
        "access_level": level,
        "level_name": ACCESS_LEVELS.get(level, "unknown"),
        "permissions": permissions.get(level, [])
    }


@mcp.tool(name="get_current_user", description="Get information about the currently logged-in user from cache. Use this to know who is currently using the system.")
def get_current_user() -> dict:
    """Returns cached user information without database query."""
    if current_user_data:
        return {
            "id": current_user_data.get("id"),
            "email": current_user_data.get("email"),
            "name": current_user_data.get("name"),
            "role": current_user_data.get("role"),
            "department": current_user_data.get("department"),
            "access_level": current_user_data.get("access_level", 1),
            "access_name": current_user_data.get("access_name", "read-only")
        }
    return {"error": "No user currently logged in"}


def run_server(server: FastMCP, mount_path: Optional[str] = None):
    server.run(transport="streamable-http", mount_path=mount_path)


if __name__ == "__main__":
    logging.info("Starting MCP servers...")
    mcp.run("streamable-http", mount_path="/mcp/")