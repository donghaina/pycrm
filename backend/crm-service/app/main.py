from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from strawberry.fastapi import GraphQLRouter
from .schema import schema
from .db import init_db

# 1. 使用 lifespan 处理启动逻辑（替代已弃用的 on_event）
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

# 2. 定义 Context 获取器
# 在 0.220.0 中，建议保持异步以获得最佳性能
async def get_context(request: Request):
    return {
        "request": request,
        "user_id": request.headers.get("x-user-id")
    }

# 3. 初始化 GraphQLRouter
graphql_app = GraphQLRouter(
    schema,
    context_getter=get_context
)

# 4. 使用 include_router 挂载（这会自动处理 HTTP 和 WebSocket）
app.include_router(graphql_app, prefix="/graphql")