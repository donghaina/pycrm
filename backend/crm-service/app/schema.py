import uuid
import strawberry
from typing import List, Optional
from .db import SessionLocal
from .models import Deal as DealModel
from .kafka import publish_event
from .auth import get_allowed_company_ids, ensure_can_write

@strawberry.federation.type(keys=["id"], extend=True)
class Company:
    id: strawberry.ID

@strawberry.federation.type(keys=["id"], extend=True)
class User:
    id: strawberry.ID

@strawberry.federation.type(keys=["id"])
class Deal:
    id: strawberry.ID
    child_company_id: strawberry.ID = strawberry.field(name="childCompanyId")
    title: str
    amount: float
    currency: str
    stage: str
    review_status: str = strawberry.field(name="reviewStatus")
    review_score: Optional[int] = strawberry.field(name="reviewScore")
    review_reason: Optional[str] = strawberry.field(name="reviewReason")
    created_by_user_id: strawberry.ID = strawberry.field(name="createdByUserId")

    @strawberry.field
    def company(self) -> Company:
        return Company(id=self.child_company_id)

    @strawberry.field
    def created_by(self) -> User:
        return User(id=self.created_by_user_id)


def _to_uuid(value: strawberry.ID | str | uuid.UUID) -> uuid.UUID:
    """Convert Strawberry ID / str to uuid.UUID safely."""
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def to_deal(row: DealModel) -> Deal:
    # row.* are uuid.UUID due to UUID(as_uuid=True); return as strings for GraphQL
    return Deal(
        id=str(row.id),
        child_company_id=str(row.child_company_id),
        title=row.title,
        amount=float(row.amount),
        currency=row.currency,
        stage=row.stage,
        review_status=row.review_status,
        review_score=row.review_score,
        review_reason=row.review_reason,
        created_by_user_id=str(row.created_by_user_id),
    )

@strawberry.type
class Query:
    @strawberry.field
    async def deal(self, info, id: strawberry.ID) -> Optional[Deal]:
        user_id = info.context.get("user_id")
        if not user_id:
            return None

        # allowed is a set/list of string UUIDs (from org-service)
        allowed, _ = await get_allowed_company_ids(user_id)

        db = SessionLocal()
        try:
            row = db.query(DealModel).filter(DealModel.id == _to_uuid(id)).first()
            if not row:
                return None
            if str(row.child_company_id) not in allowed:
                return None
            return to_deal(row)
        finally:
            db.close()

    @strawberry.field
    async def deals(self, info, company_id: Optional[strawberry.ID] = None) -> List[Deal]:
        user_id = info.context.get("user_id")
        if not user_id:
            return []

        allowed, _ = await get_allowed_company_ids(user_id)

        if company_id and str(company_id) not in allowed:
            return []

        target_ids = {str(company_id)} if company_id else set(allowed)
        target_uuids = [_to_uuid(x) for x in target_ids]

        db = SessionLocal()
        try:
            rows = db.query(DealModel).filter(DealModel.child_company_id.in_(target_uuids)).all()
            return [to_deal(r) for r in rows]
        finally:
            db.close()

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_deal(
        self,
        info,
        title: str,
        amount: float,
        currency: str,
        child_company_id: strawberry.ID,
        created_by_user_id: strawberry.ID,
    ) -> Deal:
        user_id = info.context.get("user_id")
        if not user_id:
            raise ValueError("Missing user")

        allowed, _ = await ensure_can_write(user_id)

        # allowed is string UUIDs
        if str(child_company_id) not in allowed:
            raise ValueError("Not allowed for company")

        # keep your original security check
        if str(created_by_user_id) != str(user_id):
            raise ValueError("createdByUserId must match x-user-id")

        db = SessionLocal()
        try:
            row = DealModel(
                id=uuid.uuid4(),
                child_company_id=_to_uuid(child_company_id),
                title=title,
                amount=amount,
                currency=currency,
                stage="DRAFT",
                review_status="NOT_REQUIRED",
                created_by_user_id=_to_uuid(created_by_user_id),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return to_deal(row)
        finally:
            db.close()

    @strawberry.mutation
    async def submit_deal_for_review(self, info, deal_id: strawberry.ID) -> Deal:
        user_id = info.context.get("user_id")
        if not user_id:
            raise ValueError("Missing user")

        allowed, _ = await ensure_can_write(user_id)

        db = SessionLocal()
        try:
            row = db.query(DealModel).filter(DealModel.id == _to_uuid(deal_id)).first()
            if not row:
                raise ValueError("Deal not found")

            if str(row.child_company_id) not in allowed:
                raise ValueError("Not allowed for company")

            row.review_status = "PENDING"
            row.stage = "SUBMITTED"
            row.version = row.version + 1
            db.commit()
            db.refresh(row)

            payload = {
                "event_id": str(uuid.uuid4()),
                "event_type": "deal.review.requested",
                "deal_id": str(row.id),
                "child_company_id": str(row.child_company_id),
                "created_by_user_id": str(row.created_by_user_id),
                "amount": float(row.amount),
                "currency": row.currency,
                "deal_version": row.version,
            }
            await publish_event("deal.review.requested", payload)
            return to_deal(row)
        finally:
            db.close()

schema = strawberry.federation.Schema(query=Query, mutation=Mutation)