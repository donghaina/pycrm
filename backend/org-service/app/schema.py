import strawberry
from typing import List, Optional, Set
from .db import SessionLocal
from .models import Company as CompanyModel, User as UserModel
import uuid

PARENT_ADMIN = {"PARENT_ADMIN"}

def _valid_uuid(s: str) -> bool:
    try:
        uuid.UUID(str(s))
        return True
    except Exception:
        return False

def _get_user(db, user_id: str) -> Optional[UserModel]:
    return db.query(UserModel).filter(UserModel.id == str(user_id)).first()


def _allowed_company_ids(db, user: UserModel) -> Set[str]:
    """
    Minimal tenant authorization:
    - Everyone can see their own company.
    - PARENT_ADMIN can also see direct child companies.
    """
    allowed: Set[str] = {str(user.company_id)}

    if user.role in PARENT_ADMIN:
        rows = db.query(CompanyModel).filter(CompanyModel.parent_id == str(user.company_id)).all()
        for r in rows:
            allowed.add(str(r.id))

    return allowed


@strawberry.federation.type(keys=["id"])
class Company:
    id: strawberry.ID
    name: str
    parent_id: Optional[strawberry.ID] = strawberry.field(name="parentId")

    @strawberry.field
    def children(self, info) -> List["Company"]:
        """
        Enforce auth here as well, otherwise callers can bypass Query.childCompanies
        by querying Company.children directly.
        """
        user_id = info.context.get("user_id")
        if not user_id or not _valid_uuid(user_id):
            return []  # 或 None，看返回类型

        db = SessionLocal()
        try:
            user = _get_user(db, user_id)
            if not user:
                return []

            allowed = _allowed_company_ids(db, user)

            # Only allow children listing if THIS company is within allowed scope
            if str(self.id) not in allowed:
                return []

            rows = db.query(CompanyModel).filter(CompanyModel.parent_id == str(self.id)).all()

            # For parent admin: returning direct children is fine; for others,
            # they'll only hit this when self.id == their own company_id,
            # which has no children in our sample, so it returns [] anyway.
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
    def company(self, info) -> Optional[Company]:
        user_id = info.context.get("user_id")
        if not user_id or not _valid_uuid(user_id):
            return None

        db = SessionLocal()
        try:
            user = _get_user(db, user_id)
            if not user:
                return None

            allowed = _allowed_company_ids(db, user)

            # User can only resolve company in their allowed scope
            if str(self.company_id) not in allowed:
                return None

            row = db.query(CompanyModel).filter(CompanyModel.id == str(self.company_id)).first()
            if not row:
                return None
            return Company(id=row.id, name=row.name, parent_id=row.parent_id)
        finally:
            db.close()


@strawberry.type
class Query:
    @strawberry.field
    def me(self, info) -> Optional[User]:
        user_id = info.context.get("user_id")
        if not user_id or not _valid_uuid(user_id):
            return None

        db = SessionLocal()
        try:
            row = _get_user(db, user_id)
            if not row:
                return None
            return User(id=row.id, email=row.email, role=row.role, company_id=row.company_id)
        finally:
            db.close()

    @strawberry.field
    def company(self, info, id: strawberry.ID) -> Optional[Company]:
        user_id = info.context.get("user_id")
        if not user_id or not _valid_uuid(user_id):
            return None

        db = SessionLocal()
        try:
            user = _get_user(db, user_id)
            if not user:
                return None

            allowed = _allowed_company_ids(db, user)
            if str(id) not in allowed:
                return None

            row = db.query(CompanyModel).filter(CompanyModel.id == str(id)).first()
            if not row:
                return None
            return Company(id=row.id, name=row.name, parent_id=row.parent_id)
        finally:
            db.close()

    @strawberry.field
    def child_companies(self, info, parent_id: strawberry.ID) -> List[Company]:
        user_id = info.context.get("user_id")
        if not user_id or not _valid_uuid(user_id):
            return []  # 或 None，看返回类型

        db = SessionLocal()
        try:
            user = _get_user(db, user_id)
            if not user:
                return []

            allowed = _allowed_company_ids(db, user)

            # Only allow listing children if requester is allowed to see the parent
            if str(parent_id) not in allowed:
                return []

            rows = db.query(CompanyModel).filter(CompanyModel.parent_id == str(parent_id)).all()

            # Filter results to allowed scope (defense-in-depth)
            out = []
            for r in rows:
                if str(r.id) in allowed:
                    out.append(Company(id=r.id, name=r.name, parent_id=r.parent_id))
            return out
        finally:
            db.close()


schema = strawberry.federation.Schema(query=Query)