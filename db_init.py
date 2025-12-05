from db import init_db, engine
from sqlmodel import Session, select
from models import Employee, Project, Task, Document
from passlib.context import CryptContext
from datetime import datetime, timedelta

pwd = CryptContext(schemes=["argon2"], deprecated="auto")


def seed():
    init_db()
    with Session(engine) as s:
        if s.exec(select(Employee)).first():
            print("DB already seeded.")
            return

        # Access levels: 1=read-only, 2=read+write, 3=admin
        e1 = Employee(email="alice@corp.com", full_name="Alice Johnson", hashed_password=pwd.hash("alicepw"), role="Analyst", department="Finance", access_level=1)
        e2 = Employee(email="bob@corp.com", full_name="Bob Smith", hashed_password=pwd.hash("bobpw"), role="Manager", department="Marketing", access_level=2)
        e3 = Employee(email="carol@corp.com", full_name="Carol Davis", hashed_password=pwd.hash("carolpw"), role="Admin", department="IT", access_level=3)
        s.add_all([e1, e2, e3])
        s.commit()

        p1 = Project(name="Q4 Marketing Plan", department="Marketing")
        p2 = Project(name="Website Redesign", department="IT")
        p3 = Project(name="Annual Budget Review", department="Finance")
        s.add_all([p1, p2, p3])
        s.commit()

        d1 = Document(title="Campaign Draft", content="Initial draft for Q4 campaign", author_id=e1.id, project_id=p1.id)
        d2 = Document(title="Brand Guidelines", content="Company branding standards and logo usage", author_id=e2.id, project_id=p1.id)
        s.add_all([d1, d2])
        s.commit()

        # Tasks for Q4 Marketing Plan
        t1 = Task(title="Submit campaign draft", assigned_to=e2.id, project_id=p1.id, due_date=datetime.now() + timedelta(days=7), status="done", priority="high")
        t2 = Task(title="Review social media strategy", assigned_to=e2.id, project_id=p1.id, due_date=datetime.now() + timedelta(days=14), priority="medium")
        t3 = Task(title="Prepare marketing budget", assigned_to=e1.id, project_id=p1.id, due_date=datetime.now() + timedelta(days=10), priority="high")
        
        # Tasks for Website Redesign
        t4 = Task(title="Implement new UI", assigned_to=e3.id, project_id=p2.id, due_date=datetime.now() + timedelta(days=9), priority="high")
        t5 = Task(title="Fix login page bugs", assigned_to=e3.id, project_id=p2.id, due_date=datetime.now() + timedelta(days=3), priority="urgent")
        t6 = Task(title="Optimize database queries", assigned_to=e3.id, project_id=p2.id, due_date=datetime.now() + timedelta(days=21), priority="medium")
        t7 = Task(title="Update security certificates", assigned_to=e3.id, project_id=p2.id, due_date=datetime.now() - timedelta(days=2), priority="urgent")  # Overdue
        
        # Tasks for Annual Budget Review
        t8 = Task(title="Review financial projections", assigned_to=e1.id, project_id=p3.id, due_date=datetime.now() + timedelta(days=9), priority="high")
        t9 = Task(title="Compile Q3 expense report", assigned_to=e1.id, project_id=p3.id, due_date=datetime.now() + timedelta(days=5), priority="medium")
        t10 = Task(title="Meet with department heads", assigned_to=e1.id, project_id=p3.id, due_date=datetime.now() + timedelta(days=12), priority="low")
        
        # Standalone tasks
        t11 = Task(title="Schedule team building event", assigned_to=e2.id, due_date=datetime.now() + timedelta(days=30), priority="low")
        t12 = Task(title="Complete compliance training", assigned_to=e3.id, due_date=datetime.now() - timedelta(days=5), status="done", priority="medium")  # Completed overdue
        
        s.add_all([t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12])
        s.commit()

        print("Seeded DB.")


if __name__ == "__main__":
    seed()
