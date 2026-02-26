import strawberry
from typing import List, Optional
from .db import SessionLocal
from .models import Company as CompanyModel, User as UserModel

@strawberry.federation.type(keys=["id"])
class Company:
    id: strawberry.ID
    name: str
    parent_id: Optional[strawberry.ID] = strawberry.field(name="parentId")

    @strawberry.field
    def children(self) -> List["Company"]:
        db = SessionLocal()
        try:
            rows = db.query(CompanyModel).filter(CompanyModel.parent_id == str(self.id)).all()
            return [Company(id=r.id, name=r.name, parent_id=r.parent_id) for r in rows]
        finally:
            db.close()

@strawberry.federation.type(keys=["id"])
class User:
    id: strawberry.ID
    email: str
    role: str
    company_id: strawberry.ID = strawberry.field(name="companyId")

    @strawberry.field
    def company(self) -> Company:
        db = SessionLocal()
        try:
            row = db.query(CompanyModel).filter(CompanyModel.id == str(self.company_id)).first()
            if not row:
                raise ValueError("Company not found")
            return Company(id=row.id, name=row.name, parent_id=row.parent_id)
        finally:
            db.close()

@strawberry.type
class Query:
    @strawberry.field
    def me(self, info) -> Optional[User]:
        user_id = info.context.get("user_id")
        if not user_id:
            return None
        db = SessionLocal()
        try:
            row = db.query(UserModel).filter(UserModel.id == str(user_id)).first()
            if not row:
                return None
            return User(id=row.id, email=row.email, role=row.role, company_id=row.company_id)
        finally:
            db.close()

    @strawberry.field
    def company(self, id: strawberry.ID) -> Optional[Company]:
        db = SessionLocal()
        try:
            row = db.query(CompanyModel).filter(CompanyModel.id == str(id)).first()
            if not row:
                return None
            return Company(id=row.id, name=row.name, parent_id=row.parent_id)
        finally:
            db.close()

    @strawberry.field
    def child_companies(self, parent_id: strawberry.ID) -> List[Company]:
        db = SessionLocal()
        try:
            rows = db.query(CompanyModel).filter(CompanyModel.parent_id == str(parent_id)).all()
            return [Company(id=r.id, name=r.name, parent_id=r.parent_id) for r in rows]
        finally:
            db.close()

schema = strawberry.federation.Schema(query=Query)
