from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime

# Access levels: 1=Read-only, 2=Read+Write, 3=Admin (full CRUD)
ACCESS_LEVELS = {
    1: "read",      # Can only view data
    2: "write",     # Can view and create/update
    3: "admin"      # Full access including delete
}

class Employee(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, nullable=False, unique=True)
    full_name: Optional[str] = None
    hashed_password: str
    role: str = "Employee"
    department: Optional[str] = None
    access_level: int = Field(default=1)  # 1=read, 2=write, 3=admin
    is_active: bool = True
    created_at: datetime = Field(default=datetime.now())

class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    department: Optional[str] = None

class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    assigned_to: Optional[int] = Field(default=None, foreign_key="employee.id")
    project_id: Optional[int] = Field(default=None, foreign_key="project.id")
    due_date: Optional[datetime] = None
    status: str = "Pending"

class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    content: str
    author_id: Optional[int] = Field(default=None, foreign_key="employee.id")
    project_id: Optional[int] = None


class UploadedFile(SQLModel, table=True):
    """Tracks uploaded files for RAG system."""
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str = Field(index=True)
    file_path: str
    file_size: int = 0
    file_type: str = ""
    chunks_count: int = 0
    uploaded_by: Optional[int] = Field(default=None, foreign_key="employee.id")
    uploaded_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = True


class ChatSession(SQLModel, table=True):
    """Tracks chat sessions for history."""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="employee.id")
    preview: str = ""  # First user message as preview
    created_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = True


class Conversation(SQLModel, table=True):
    """Tracks chat conversations."""
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: Optional[int] = Field(default=None, foreign_key="chatsession.id")
    user_id: Optional[int] = Field(default=None, foreign_key="employee.id")
    role: str  # 'user', 'assistant', 'tool'
    content: str
    tool_name: Optional[str] = None  # Name of tool used if role='tool'
    created_at: datetime = Field(default_factory=datetime.now)
