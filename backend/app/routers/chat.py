from fastapi import APIRouter

from app.schemas import ChatRequest, ChatResponse
from app.state import files

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Mock chat endpoint. Returns a canned response until the RAG pipeline
    is wired in behind this route."""
    ready_files = [f for f in files.values() if f.status == "ready"]

    if ready_files:
        context_note = (
            f"I'd search across {len(ready_files)} document"
            f"{'s' if len(ready_files) != 1 else ''} "
            f"({', '.join(f.name for f in ready_files[:3])}"
            f"{', ...' if len(ready_files) > 3 else ''}) to answer this."
        )
    else:
        context_note = "No documents are uploaded yet, so I have no corpus to search."

    reply = (
        f'This is a placeholder response to: "{request.message}". '
        f"{context_note} Connect the RAG backend to replace this mock."
    )
    return ChatResponse(content=reply)
