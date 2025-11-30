from db import init_db, engine
from sqlmodel import Session, select
from models import Employee, Project, Task, Document
from passlib.context import CryptContext
from datetime import datetime, timedelta

# pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
pwd = CryptContext(schemes=["argon2"], deprecated="auto")

def seed():
    init_db()
    with Session(engine) as s:
        # Check if already seeded
        if s.exec(select(Employee)).first():
            print("DB already seeded.")
            return

        e1 = Employee(email="alice@corp.com", full_name="Alice Johnson", hashed_password=pwd.hash("alicepw"), role="Analyst", department="Finance")
        e2 = Employee(email="bob@corp.com", full_name="Bob Smith", hashed_password=pwd.hash("bobpw"), role="Manager", department="Marketing")
        e3 = Employee(email="carol@corp.com", full_name="Carol Davis", hashed_password=pwd.hash("carolpw"), role="Developer", department="IT")
        s.add_all([e1, e2, e3])
        s.commit()

        p1 = Project(name="Q4 Marketing Plan", department="Marketing")
        s.add(p1); s.commit()

        d1 = Document(title="Campaign Draft", content="Initial draft for Q4 campaign", author_id=e1.id, project_id=p1.id)
        s.add(d1); s.commit()

        t1 = Task(title="Submit campaign draft", assigned_to=e2.id, project_id=p1.id, due_date=datetime.now() + timedelta(days=7), status="done")
        t2 = Task(title="Review financial projections", assigned_to=e1.id, due_date=datetime.now() + timedelta(days=9))
        t3 = Task(title="Implement new UI", assigned_to=e3.id, due_date=datetime.now() + timedelta(days=9))

        s.add_all([t1, t2, t3]); s.commit()

        print("Seeded DB.")


if __name__ == "__main__":
    seed()
