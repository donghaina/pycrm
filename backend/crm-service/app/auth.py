from .org_client import get_user_context

READ_ONLY = {"READONLY"}
PARENT_ADMIN = {"PARENT_ADMIN"}

async def get_allowed_company_ids(user_id: str):
    data = await get_user_context(user_id)
    me = data.get("me") if data else None
    if not me:
        return set(), None

    role = me.get("role")
    company_id = me.get("companyId")

    if role in PARENT_ADMIN:
        # For parent admins, allow all children. If not a parent, fall back to own company.
        children = data.get("childCompanies") or []
        if children:
            return {c.get("id") for c in children}, role
        return {company_id}, role

    return {company_id}, role

async def ensure_can_write(user_id: str):
    allowed, role = await get_allowed_company_ids(user_id)
    if role in READ_ONLY:
        raise ValueError("READONLY role cannot write")
    return allowed, role
