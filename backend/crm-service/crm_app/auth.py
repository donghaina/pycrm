from .org_client import get_user_context

READ_ONLY = {"READONLY"}
PARENT_ADMIN = {"PARENT_ADMIN"}


def get_allowed_company_ids(user_id: str):
    data = get_user_context(user_id)
    me = data.get("me") if data else None
    if not me:
        return set(), None

    role = me.get("role")
    company_id = me.get("companyId")

    if role in PARENT_ADMIN:
        children = data.get("childCompanies") or []
        if children:
            return {c.get("id") for c in children}, role
        return {company_id}, role

    return {company_id}, role


def ensure_can_write(user_id: str):
    allowed, role = get_allowed_company_ids(user_id)
    if role in READ_ONLY:
        raise ValueError("READONLY role cannot write")
    return allowed, role
