import json
import subprocess

from fastapi import FastAPI, Request, Depends, Form, Response, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from db import init_db, get_session
from models import *
from auth import verify_password, get_password_hash, create_access_token, decode_token, get_user_by_email
from config import ACCESS_TOKEN_EXPIRE_MINUTES
from datetime import timedelta
from typing import List
from db import engine
from db import init_db
from db import get_session
from db import init_db
from db_init import seed
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, scoped_session

from pydantic import BaseModel
import webbrowser

from llm_manager import stream_agent_response
import psutil
import os
import signal
import platform

import asyncio

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
messages = [{"role": "system", "content": "You are a corporate environment assistant that answers briefly and "
                                          "avoid unnecessary talk, speaking based on facts."}]

PORT = 8080
current_user_data = {}

def force_kill_port(port: int):
    """Forcefully frees a port by killing any process using it."""
    try:
        if platform.system() == "Windows":
            output = subprocess.check_output(
                f'netstat -aon | findstr :{port}', shell=True, text=True
            )
            for line in output.splitlines():
                if "LISTENING" in line:
                    pid = line.strip().split()[-1]
                    print(f"Killing PID {pid} on port {port}")
                    subprocess.run(f'taskkill /PID {pid} /F', shell=True)
        else:
            # Linux / Mac
            output = subprocess.check_output(
                f'lsof -t -i:{port}', shell=True, text=True
            )
            for pid in output.splitlines():
                print(f"Killing PID {pid} on port {port}")
                subprocess.run(f'kill -9 {pid}', shell=True)

    except subprocess.CalledProcessError:
        print(f"No process found using port {port}.")
    except Exception as e:
        print(f"Error while freeing port {port}: {e}")

class Message(BaseModel):
    user_input: str


@app.on_event("startup")
def startup():
    # Kill other processes using the port before Uvicorn binds to it
    # if platform.system() == "Windows":
    #     print(f"Ensuring port {PORT} is free...")
    #     try:
    #         output = subprocess.check_output(
    #             f'netstat -aon | findstr :{PORT}', shell=True, text=True
    #         )
    #         for line in output.splitlines():
    #             if "LISTENING" in line and "PID" not in line:
    #                 pid = line.strip().split()[-1]
    #                 print(f"Terminating process {pid} on port {PORT}...")
    #                 subprocess.run(f'taskkill /PID {pid} /F', shell=True)
    #     except subprocess.CalledProcessError:
    #         print(f"Port {PORT} already free.")
    # else:
    #     os.system(f"fuser -k {PORT}/tcp 2>/dev/null")

    # Initialize DB and seed only if necessary
    print("Initializing database...")
    init_db()
    try:
        seed()
    except Exception as e:
        print("Seeding skipped or failed:", e)

    # Open the app automatically in browser (only once)
    webbrowser.open_new_tab(f"http://127.0.0.1:{PORT}/login")
    print("✅ Application started and browser opened.")


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
    global current_user_data
    with Session(engine) as s:
        user = get_user_by_email(s, email)
        if not user or not verify_password(password, user.hashed_password):
            # raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials")
            # return RedirectResponse(url="/login?error=invalid credentials", status_code=status.HTTP_303_SEE_OTHER)
            return templates.TemplateResponse("login.html", {"request": request, "error": "Incorrect credentials"})

        current_user_data = {"email": user.email, "fullname": user.full_name}
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
def clearcache():
    messages.clear()
    print("new conversation")
    return
# -------- Simple protected API example --------
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
async def chat_stream(request: Message):
    """
    Expects JSON body: {"messages": [{"role":"user","content":"hi"} , ... ]}
    Streams the agent response as Server-Sent Events (SSE) compatible text/event-stream.
    """
    print(request)
    print(len(messages))
    if len(messages) >= 10:
        messages.pop(1)
    # body = await request.json()
    # print(request.user_input)
    # messages = body.get("messages") or [{"role":"user","content": body.get("message", "")}]
    if request.user_input:
        messages.append({"role": "user", "content": request.user_input})
        messages.append({"role": "system", "content": f"you are currently conversing with user: {current_user_data}"})

    print(messages)
    print('lets try')

    async def event_generator():
        print('lets try again')
        try:
            full_response = ""
            async for chunk in stream_agent_response(messages):
                print(type(chunk))
                print(chunk)
                # Each chunk is text; yield as SSE data frame
                if isinstance(chunk, str):
                    full_response += chunk
                    payload = {"content": chunk}
                    yield f"data: {json.dumps(payload)}\n\n"

            messages.append({"role": "assistant", "content": full_response})
                # yield chunk
            # final sentinel
            # yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")

SessionLocal = scoped_session(sessionmaker(bind=engine))

@app.post("/analytics")
def get_analytics():
    with SessionLocal() as s:
        # --- Employees per department ---
        employee_data = s.query(Employee).all()
        departments = {}
        for emp in employee_data:
            dept = emp.department or "Unassigned"
            departments[dept] = departments.get(dept, 0) + 1

        # --- Tasks per status ---
        task_data = s.query(Task).all()
        task_status = {}
        for t in task_data:
            status = t.status or "Unknown"
            task_status[status] = task_status.get(status, 0) + 1

        # --- Projects count ---
        project_count = s.query(Project).count()

        # --- Employees count ---
        employee_count = len(employee_data)

        # --- Tasks count ---
        task_count = len(task_data)

        # Compose analytics dict
        analytics = {
            "employees_per_department": departments,
            "tasks_per_status": task_status,
            "total_projects": project_count,
            "total_employees": employee_count,
            "total_tasks": task_count
        }

    return JSONResponse(content=analytics)

# if __name__ == "__main__":
    # try:
    #     subprocess.Popen(["python", "./mcp_server.py"])  # runs in background
    # except Exception as e:
    #     print("Error running MCP server:", e)

    # subprocess.run(["uvicorn", "app:main", "--host", "0.0.0.0", "--port", "8080"])