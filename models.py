from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime

class Employee(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, nullable=False, unique=True)
    full_name: Optional[str] = None
    hashed_password: str
    role: str = "Employee"
    department: Optional[str] = None
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
