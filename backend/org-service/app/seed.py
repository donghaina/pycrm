from .db import SessionLocal
from .models import Company, User

DEFAULT_COMPANIES = [
    Company(id="p1", name="ParentCo", parent_id=None),
    Company(id="c1", name="ChildCo A", parent_id="p1"),
    Company(id="c2", name="ChildCo B", parent_id="p1"),
]

DEFAULT_USERS = [
    User(id="u1", email="admin@parent.co", role="PARENT_ADMIN", company_id="p1"),
    User(id="u2", email="sales@childa.co", role="SALES", company_id="c1"),
    User(id="u3", email="readonly@childb.co", role="READONLY", company_id="c2"),
]


def seed_if_empty():
    db = SessionLocal()
    try:
        count = db.query(Company).count()
        if count == 0:
            db.add_all(DEFAULT_COMPANIES)
            db.add_all(DEFAULT_USERS)
            db.commit()
    finally:
        db.close()
