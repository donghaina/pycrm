import graphene
from graphene_django import DjangoObjectType
from graphene_federation import build_schema, key

from .models import Company, User


def get_request_user(info):
    user_id = info.context.headers.get("x-user-id") if info.context else None
    if not user_id:
        return None
    return User.objects.filter(id=user_id).first()


def get_allowed_company_ids(user):
    if not user:
        return set()
    if user.role == "PARENT_ADMIN":
        children = Company.objects.filter(parent_id=user.company_id).values_list("id", flat=True)
        return {str(user.company_id), *[str(cid) for cid in children]}
    return {str(user.company_id)}


@key("id")
class CompanyType(DjangoObjectType):
    parent_id = graphene.ID(name="parentId")
    children = graphene.List(lambda: CompanyType)

    class Meta:
        model = Company
        fields = ("id", "name")

    def resolve_parent_id(self, info):
        return str(self.parent_id) if self.parent_id else None

    def resolve_children(self, info):
        user = get_request_user(info)
        if not user or user.role != "PARENT_ADMIN":
            return []
        if str(user.company_id) != str(self.id):
            return []
        return Company.objects.filter(parent_id=self.id)

    def __resolve_reference(self, info):
        return Company.objects.filter(id=self.id).first()


@key("id")
class UserType(DjangoObjectType):
    company_id = graphene.ID(name="companyId")
    company = graphene.Field(CompanyType)

    class Meta:
        model = User
        fields = ("id", "email", "role")

    def resolve_company_id(self, info):
        return str(self.company_id)

    def resolve_company(self, info):
        return Company.objects.filter(id=self.company_id).first()

    def __resolve_reference(self, info):
        return User.objects.filter(id=self.id).first()


class Query(graphene.ObjectType):
    me = graphene.Field(UserType)
    company = graphene.Field(CompanyType, id=graphene.ID(required=True))
    child_companies = graphene.List(CompanyType, parent_id=graphene.ID(required=True), name="childCompanies")

    def resolve_me(self, info):
        return get_request_user(info)

    def resolve_company(self, info, id):
        user = get_request_user(info)
        if not user:
            return None
        allowed = get_allowed_company_ids(user)
        if str(id) not in allowed:
            return None
        return Company.objects.filter(id=id).first()

    def resolve_child_companies(self, info, parent_id):
        user = get_request_user(info)
        if not user or user.role != "PARENT_ADMIN":
            return []
        if str(user.company_id) != str(parent_id):
            return []
        return Company.objects.filter(parent_id=parent_id)


schema = build_schema(query=Query, types=[CompanyType, UserType])
