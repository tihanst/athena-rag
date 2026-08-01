from typing import Literal

from pydantic import BaseModel


class ChatHistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatHistoryItem] = []


class ChatResponse(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str


class FileRecord(BaseModel):
    id: str
    name: str
    size: int
    status: Literal["uploading", "ready", "error"] = "ready"
