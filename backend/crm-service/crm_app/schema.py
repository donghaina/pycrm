import uuid
import graphene
from django.utils import timezone
from graphene_django import DjangoObjectType
from graphene_federation import build_schema, key, extend, external

from .models import Deal
from .kafka import publish_event
from .auth import get_allowed_company_ids, ensure_can_write


@extend("id")
class CompanyType(graphene.ObjectType):
    id = external(graphene.UUID(required=True))


@extend("id")
class UserType(graphene.ObjectType):
    id = external(graphene.UUID(required=True))


@key("id")
class DealType(DjangoObjectType):
    child_company_id = graphene.ID(name="childCompanyId")
    review_status = graphene.String(name="reviewStatus")
    review_score = graphene.Int(name="reviewScore")
    review_reason = graphene.String(name="reviewReason")
    created_by_user_id = graphene.ID(name="createdByUserId")
    company = graphene.Field(CompanyType)
    created_by = graphene.Field(UserType, name="createdBy")

    class Meta:
        model = Deal
        fields = (
            "id",
            "title",
            "amount",
            "currency",
            "stage",
        )

    def resolve_child_company_id(self, info):
        return str(self.child_company_id)

    def resolve_created_by_user_id(self, info):
        return str(self.created_by_user_id)

    def resolve_company(self, info):
        return CompanyType(id=str(self.child_company_id))

    def resolve_created_by(self, info):
        return UserType(id=str(self.created_by_user_id))

    @classmethod
    def __resolve_reference(cls, info, **kwargs):
        deal_id = kwargs.get("id")
        return Deal.objects.filter(id=deal_id).first()


def _get_user_id(info):
    request = info.context
    if not request:
        return None
    return request.headers.get("x-user-id")


def _to_uuid(value):
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


class Query(graphene.ObjectType):
    deal = graphene.Field(DealType, id=graphene.ID(required=True))
    deals = graphene.List(DealType, company_id=graphene.ID(required=False), name="deals")

    def resolve_deal(self, info, id):
        user_id = _get_user_id(info)
        if not user_id:
            return None

        allowed, _ = get_allowed_company_ids(user_id)
        deal = Deal.objects.filter(id=_to_uuid(id)).first()
        if not deal:
            return None
        if str(deal.child_company_id) not in allowed:
            return None
        return deal

    def resolve_deals(self, info, company_id=None):
        user_id = _get_user_id(info)
        if not user_id:
            return []

        allowed, _ = get_allowed_company_ids(user_id)
        if company_id and str(company_id) not in allowed:
            return []

        target_ids = {str(company_id)} if company_id else set(allowed)
        target_uuids = [_to_uuid(x) for x in target_ids]
        return list(Deal.objects.filter(child_company_id__in=target_uuids))


class CreateDeal(graphene.Mutation):
    class Arguments:
        title = graphene.String(required=True)
        amount = graphene.Float(required=True)
        currency = graphene.String(required=True)
        child_company_id = graphene.ID(required=True, name="childCompanyId")
        created_by_user_id = graphene.ID(required=True, name="createdByUserId")

    Output = DealType

    def mutate(self, info, title, amount, currency, child_company_id, created_by_user_id):
        user_id = _get_user_id(info)
        if not user_id:
            raise ValueError("Missing user")

        allowed, _ = ensure_can_write(user_id)

        if str(child_company_id) not in allowed:
            raise ValueError("Not allowed for company")

        if str(created_by_user_id) != str(user_id):
            raise ValueError("createdByUserId must match x-user-id")

        deal = Deal.objects.create(
            id=uuid.uuid4(),
            child_company_id=_to_uuid(child_company_id),
            title=title,
            amount=amount,
            currency=currency,
            stage="DRAFT",
            review_status="NOT_REQUIRED",
            created_by_user_id=_to_uuid(created_by_user_id),
            version=1,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        return deal


class SubmitDealForReview(graphene.Mutation):
    class Arguments:
        deal_id = graphene.ID(required=True, name="dealId")

    Output = DealType

    def mutate(self, info, deal_id):
        user_id = _get_user_id(info)
        if not user_id:
            raise ValueError("Missing user")

        allowed, _ = ensure_can_write(user_id)
        deal = Deal.objects.filter(id=_to_uuid(deal_id)).first()
        if not deal:
            raise ValueError("Deal not found")

        if str(deal.child_company_id) not in allowed:
            raise ValueError("Not allowed for company")

        deal.review_status = "PENDING"
        deal.stage = "SUBMITTED"
        deal.version = deal.version + 1
        deal.updated_at = timezone.now()
        deal.save()

        payload = {
            "event_id": str(uuid.uuid4()),
            "event_type": "deal.review.requested",
            "deal_id": str(deal.id),
            "child_company_id": str(deal.child_company_id),
            "created_by_user_id": str(deal.created_by_user_id),
            "amount": float(deal.amount),
            "currency": deal.currency,
            "deal_version": deal.version,
        }
        publish_event("deal.review.requested", payload)
        return deal


class Mutation(graphene.ObjectType):
    create_deal = CreateDeal.Field(name="createDeal")
    submit_deal_for_review = SubmitDealForReview.Field(name="submitDealForReview")


schema = build_schema(query=Query, mutation=Mutation, types=[DealType, CompanyType, UserType])
