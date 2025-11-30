#!/usr/bin/env python3
"""
mcpserver.py

FastMCP servers exposing tools for:
 - Database (SQLite) CRUD for employees, projects, tasks, documents, meetings
 - Utilities: reminders, battery status, process listing
 - UI automation: screenshots, OCR click, virtual keyboard, launch apps, open files
 - Communication: send_email (SMTP), send_whatsapp (Twilio optional)

Run:
    python mcpserver.py

Requires:
    pip install mcp-server fastmcp sqlalchemy sqlalchemy-utils twilio pillow pytesseract pyautogui psutil
"""

import os
import sys
import subprocess
import threading
import asyncio
import datetime
from typing import Optional, List, Tuple
from pydantic import Field
from typing import Annotated
import logging

# DB
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, select
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, scoped_session

# utils
import psutil
from PIL import ImageGrab
import pytesseract
import pyautogui
import webbrowser
import urllib.parse
import glob
import platform
import smtplib
from email.message import EmailMessage

# optional Twilio
try:
    from twilio.rest import Client as TwilioClient
except ImportError:
    TwilioClient = None
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from mcp.server.fastmcp import FastMCP
from config import SQLITE_DB_URL
from models import *
from passlib.context import CryptContext


from main import Message, chat_stream, messages
# ===== Logging =====
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ===== Config =====
pwd = CryptContext(schemes=["argon2"], deprecated="auto")

DB_PATH = SQLITE_DB_URL
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_FROM")

# ===== MCP Servers =====
mcp = FastMCP("general", port=3000)
mcp2 = FastMCP("UI_automation", port=4001)

# ===== Database =====
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

@mcp.tool(name="create_employee", description="Create a new employee")
def create_employee(email: str, full_name: str = "", role: str = "Employee", department: str = "", password: Optional[str] = None) -> dict:
    hashed_password = pwd.hash(password)
    with SessionLocal() as s:
        if s.query(Employee).filter(Employee.email == email).first():
            return {"error": "employee_exists", "message": f"Employee with email {email} exists."}
        emp = Employee(email=email, full_name=full_name, role=role, department=department, hashed_password=hashed_password)
        s.add(emp)
        s.commit()
        s.refresh(emp)
        return to_dict(emp)


@mcp.tool(name="get_employee", description="Get employee by email or id")
def get_employee(identifier: str) -> Optional[dict]:
    print(f"identifier {identifier}")
    with SessionLocal() as s:

        if identifier.isdigit():
            emp = s.get(Employee, int(identifier))
            print(emp)
        else:
            emp = s.query(Employee).filter(Employee.email == identifier).first()
            print(emp)

        return to_dict(emp) if emp else "employee not found"


@mcp.tool(name="list_employees", description="List employees")
def list_employees(limit: int = 100) -> List[dict]:
    with SessionLocal() as s:
        return [to_dict(e) for e in s.query(Employee).limit(limit).all()]


@mcp.tool(name="create_project", description="Create a new project")
def create_project(name: str, department: str = "") -> dict:
    with SessionLocal() as s:
        project = Project(name=name, department=department)
        s.add(project)
        s.commit()
        s.refresh(project)
        return to_dict(project)


@mcp.tool(name="get_project", description="Get project by id")
def get_project(project_id: int) -> Optional[dict]:
    with SessionLocal() as s:
        project = s.get(Project, project_id)
        return to_dict(project) if project else "project not found"


@mcp.tool(name="list_projects", description="List all projects")
def list_projects(limit: int = 100) -> List[dict]:
    with SessionLocal() as s:
        return [to_dict(p) for p in s.query(Project).limit(limit).all()]



# ===== TASKS =====
@mcp.tool(name="create_task", description="Create a new task")
def create_task(title: str, assigned_to: Optional[int] = None, project_id: Optional[int] = None,
                due_date: Optional[datetime] = None, status: str = "Pending") -> dict:
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
def get_task(task_id: int) -> Optional[dict]:
    with SessionLocal() as s:
        task = s.get(Task, task_id)
        return to_dict(task) if task else "task not found"


@mcp.tool(name="list_tasks", description="List all tasks")
def list_tasks(limit: int = 100) -> List[dict]:
    with SessionLocal() as s:
        return [to_dict(t) for t in s.query(Task).limit(limit).all()]



@mcp.tool(name="update_task_status", description="Update task status by id")
def update_task_status(task_id: int, new_status: str) -> dict:
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
def get_document(doc_id: int) -> Optional[dict]:
    with SessionLocal() as s:
        doc = s.get(Document, doc_id)
        return to_dict(doc) if doc else "document not found"


@mcp.tool(name="list_documents", description="List all documents")
def list_documents(limit: int = 100) -> List[dict]:
    with SessionLocal() as s:
        return [to_dict(d) for d in s.query(Document).limit(limit).all()]

@mcp.tool(
    name="web_search",
    description="Performs a web search by opening the default browser with search results."
)
def web_search(query: str) -> str:
    """
    Opens the default browser to display search results for the given query.
    """

    url = "https://www.google.com/search?q=" + urllib.parse.quote(query)
    webbrowser.open_new_tab(url)
    return f"Opened web search for: {query}"


@mcp.tool(
    name="search_and_open_file",
    description="Searches for files matching a pattern and opens the first match."
)
def search_and_open_file(pattern: str) -> str:
    """
    Searches for files matching the glob pattern and opens the first found file.
    """
    import glob, os, subprocess, platform

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


@mcp.tool(
    name="launch_application",
    description="Launches an application by its command"
)
def launch_application(app_command: str) -> str:
    """
    Launches the specified application/software on the user machine.
    """

    try:
        subprocess.Popen(app_command, shell=True)
        return f"Launched application: {app_command}"
    except Exception as e:
        return f"Failed to launch {app_command}: {e}"


# ===== Communication =====
sender_email = "davekinimo77@gmail.com"
sender_password = "0846 7756"
@mcp.tool(name="send_simple_email", description="Send a simple email using SMTP (Gmail example).")
def send_simple_email(receiver_email: str, subject: str, body: str) -> dict:
    """
    Send an email through Gmail SMTP.
    """
    print(sender_email, receiver_email, subject, body)
    try:
        # Create the email message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = receiver_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        # Send via Gmail SMTP
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()  # Secure the connection
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, message.as_string())

        return {"status": "sent", "to": receiver_email, "subject": subject}

    except smtplib.SMTPAuthenticationError:
        return {"error": "authentication_failed", "message": "Invalid email or password."}
    except Exception as e:
        return {"error": str(e)}

# ===== UI / Automation =====
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


# ===== Reminders =====
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


# ===== Health Check =====
@mcp.tool(name="health_check", description="Server status")
def health_check() -> dict:
    return {"status": "ok", "time": datetime.now(), "db_exists": os.path.exists(DB_PATH)}


# ===== Run Servers =====
def run_server(server: FastMCP, mount_path: Optional[str] = None):
    server.run(transport="streamable-http", mount_path=mount_path)


if __name__ == "__main__":
    logging.info("Starting MCP servers...")
    # threads = [
    #     threading.Thread(target=run_server, args=(mcp, "/mcp/"), daemon=True),
    #     threading.Thread(target=run_server, args=(mcp2, "/mcp/"), daemon=True)
    # ]
    # for t in threads:
    #     t.start()

    # try:
    #     while True:
    #         threading.Event().wait(1)
    # except KeyboardInterrupt:
    #     logging.info("Shutting down MCP servers...")
    #     sys.exit(0)

    mcp.run("streamable-http", mount_path="/mcp/")