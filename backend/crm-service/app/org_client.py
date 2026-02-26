import os
import httpx

ORG_SERVICE_URL = os.getenv("ORG_SERVICE_URL", "http://org-service:4001/graphql")

# Step 1: get current user (and their companyId) from org-service
ME_QUERY = """
query Me {
  me { id role companyId }
}
"""

# Step 2: using companyId as parentId, get org context
COMPANIES_QUERY = """
query Companies($parentId: ID!) {
  company(id: $parentId) { id parentId }
  childCompanies(parentId: $parentId) { id }
}
"""

async def get_user_context(user_id: str):
    headers = {"x-user-id": user_id}

    async with httpx.AsyncClient() as client:
        # 1) Fetch me first (so we can use companyId as parentId)
        me_resp = await client.post(
            ORG_SERVICE_URL,
            json={"query": ME_QUERY},
            headers=headers,
        )
        me_resp.raise_for_status()
        me_data = me_resp.json().get("data") or {}
        me = me_data.get("me")
        if not me or not me.get("companyId"):
            # No user context; let caller handle missing user
            return {"me": me, "company": None, "childCompanies": []}

        parent_company_id = me["companyId"]

        # 2) Fetch company + childCompanies using companyId (NOT user_id)
        org_resp = await client.post(
            ORG_SERVICE_URL,
            json={"query": COMPANIES_QUERY, "variables": {"parentId": parent_company_id}},
            headers=headers,
        )
        org_resp.raise_for_status()
        org_data = org_resp.json().get("data") or {}

        # Return a unified shape compatible with existing callers
        return {
            "me": me,
            "company": org_data.get("company"),
            "childCompanies": org_data.get("childCompanies") or [],
        }