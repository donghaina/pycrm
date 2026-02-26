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

    # Always include own company
    allowed = set()
    if company_id:
        allowed.add(str(company_id))

    # Parent admins can also see child companies
    if role in PARENT_ADMIN:
        children = data.get("childCompanies") or []
        for c in children:
            cid = c.get("id")
            if cid:
                allowed.add(str(cid))

    return allowed, role

async def ensure_can_write(user_id: str):
    allowed, role = await get_allowed_company_ids(user_id)
    if role in READ_ONLY:
        raise ValueError("READONLY role cannot write")
    return allowed, role