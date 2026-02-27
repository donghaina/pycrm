import os
import httpx

ORG_SERVICE_URL = os.getenv("ORG_SERVICE_URL", "http://org-service:4001/graphql")

ME_QUERY = """
query Me {
  me { id role companyId }
}
"""

CHILDREN_QUERY = """
query Children($parentId: ID!) {
  childCompanies(parentId: $parentId) { id }
}
"""


def _post(query: str, variables: dict | None, user_id: str) -> dict:
    headers = {"x-user-id": user_id}
    with httpx.Client() as client:
        resp = client.post(ORG_SERVICE_URL, json={"query": query, "variables": variables}, headers=headers, timeout=5)
        resp.raise_for_status()
        return resp.json().get("data") or {}


def get_user_context(user_id: str) -> dict:
    data = _post(ME_QUERY, None, user_id)
    me = data.get("me") if data else None
    if not me:
        return {"me": None, "childCompanies": []}

    if me.get("role") == "PARENT_ADMIN":
        children = _post(CHILDREN_QUERY, {"parentId": me.get("companyId")}, user_id).get("childCompanies", [])
    else:
        children = []

    return {"me": me, "childCompanies": children}
