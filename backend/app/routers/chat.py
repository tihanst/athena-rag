import asyncio
from fastapi import APIRouter

from app.schemas import ChatRequest, ChatResponse
from app.orchestrator import run_chat
from app.memory import flush_log_history, log_history, chat_history

router = APIRouter(prefix="/api", tags=["chat"])

# To gracefully handle page reload (accidental or otherwise) during in-flight request
# Proper logging write will be made
current_chat_task: asyncio.Task | None = None

# NEED A ROUTING LAYER THAT DECIDES IF RAG IS NEEDED OR JUST A CHAT RESPONSE W/OUT RAG


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    global current_chat_task
    current_chat_task = asyncio.create_task(_consume_run_chat(request))
    try:
        content = await current_chat_task
    finally:
        current_chat_task = None
    return ChatResponse(content=content)
    # content = "".join([chunk async for chunk in run_chat(request)])
    # print("CONTENT:", repr(content))
    # return ChatResponse(content=content)


@router.post("/chat/reset")
async def reset_chat() -> None:
    global current_chat_task

    was_cancelled = current_chat_task is not None and not current_chat_task.done()
    if was_cancelled:
        current_chat_task.cancel()
        try:
            await current_chat_task
        # Prevent successful cancellation from propagating,
        # creating an unhandled exception
        except asyncio.CancelledError:
            pass
        current_chat_task = None

    flush_log_history(
        "user_reset_through_reload_cancel" if was_cancelled else "user_reset_normal"
    )
    chat_history.clear_conversation_history()
    log_history.clear_lexical_history()


async def _consume_run_chat(request: ChatRequest) -> str:
    return "".join([chunk async for chunk in run_chat(request)])


# OLD boilerplate
# @router.post("/chat", response_model=ChatResponse)
# def chat(request: ChatRequest) -> ChatResponse:
#     """Mock chat endpoint. Returns a canned response until the RAG pipeline
#     is wired in behind this route."""
#     ready_files = [f for f in files.values() if f.status == "ready"]

#     if ready_files:
#         context_note = (
#             f"I'd search across {len(ready_files)} document"
#             f"{'s' if len(ready_files) != 1 else ''} "
#             f"({', '.join(f.name for f in ready_files[:3])}"
#             f"{', ...' if len(ready_files) > 3 else ''}) to answer this."
#         )
#     else:
#         context_note = "No documents are uploaded yet, so I have no corpus to search."

#     reply = (
#         f'This is a placeholder response to: "{request.message}". '
#         f"{context_note} Connect the RAG backend to replace this mock."
#     )
#     return ChatResponse(content=reply)
