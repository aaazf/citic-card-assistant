from fastapi import APIRouter

from app.api.v1 import (
    agent,
    chat,
    conversations,
    documents,
    eval,
    indexes,
    knowledge,
    settings,
    system,
    usage,
)

api_router = APIRouter()
api_router.include_router(system.router)
api_router.include_router(chat.router)
api_router.include_router(knowledge.router)
api_router.include_router(agent.router)
api_router.include_router(documents.router)
api_router.include_router(conversations.router)
api_router.include_router(settings.router)
api_router.include_router(indexes.router)
api_router.include_router(eval.router)
api_router.include_router(usage.router)
