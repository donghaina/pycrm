from fastapi import FastAPI, Request
from strawberry.fastapi import GraphQLRouter
from .schema import schema
from .db import init_db
from .seed import seed_if_empty
import uuid

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    init_db()
    seed_if_empty()

# 建议：将 get_context 改为异步，以匹配最新 FastAPI/Strawberry 的执行流
async def get_context(request: Request):
    raw = request.headers.get("x-user-id")
    return {
        "request": request,
        "user_id": uuid.UUID(raw) if raw else None
    }

# 初始化 Router
graphql_app = GraphQLRouter(
    schema,
    context_getter=get_context
)

# 【关键修改】：不要用 add_route，改用 include_router
# 这会自动处理 /graphql 的 GET, POST 和 WebSocket 协议
app.include_router(graphql_app, prefix="/graphql")