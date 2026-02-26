import os
import httpx

ORG_SERVICE_URL = os.getenv("ORG_SERVICE_URL", "http://org-service:4001/graphql")

QUERY = """
query MeAndCompanies($parentId: ID!) {
  me { id role companyId }
  company(id: $parentId) { id parentId }
  childCompanies(parentId: $parentId) { id }
}
"""

async def get_user_context(user_id: str):
    headers = {"x-user-id": user_id}
    async with httpx.AsyncClient() as client:
        resp = await client.post(ORG_SERVICE_URL, json={"query": QUERY, "variables": {"parentId": user_id}}, headers=headers)
        resp.raise_for_status()
        data = resp.json().get("data")
        return data
