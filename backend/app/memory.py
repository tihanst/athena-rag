"""Basic singleton memory module for a chat session. Resets on /chat/reset route. Does not reset on refresh of web app page"""

from pydantic import BaseModel
from pathlib import Path
import json
from typing import Any


from app.schemas import ChatHistoryItem, ChatSystem, SearchTerms
from app.prompts import RAG_CHAT_SYSTEM_PROMPT


LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "chat_sessions.jsonl"


class ChatHistory(BaseModel):
    history: list[ChatHistoryItem] = []

    def __len__(self):
        return len(self.history)

    def to_message_list(self) -> list[dict]:
        return [{"role": item.role, "content": item.content} for item in self.history]

    def add_message(self, message: ChatHistoryItem) -> None:
        self.history.append(message)

    def clear_conversation_history(self) -> None:
        self.history = []


# Strictly for use in the chat llm as a singleton, not lexical search llm or any others
chat_history = ChatHistory()
chat_history.add_message(ChatSystem(role="system", content=RAG_CHAT_SYSTEM_PROMPT))


# class SemanticHistory(BaseModel):
#     semantic_history: dict[int, SearchTerms] = {}

#     def add_search_item(self, item: SearchTerms):
#         self.semantic_history[len(self.semantic_history)] = item


class LogHistory(BaseModel):
    log_chat_history: ChatHistory
    log_lexical_history: dict[int, SearchTerms] = {}

    def add_search_item(self, item: SearchTerms):
        self.log_lexical_history[len(self.log_lexical_history)] = item

    def unload_and_pack(
        self, stop_reason: str | None = None
    ) -> dict[str, dict[str, str] | str | Any]:
        log: dict[str, dict[str, str] | str | Any] = {}
        log["lexical_history"] = {
            key: search_terms.model_dump()
            for key, search_terms in self.log_lexical_history.items()
        }
        log["chat_history"] = chat_history.model_dump()

        log["stop_reason"] = stop_reason

        return log

    def clear_lexical_history(self):
        self.log_lexical_history = {}


log_history = LogHistory(log_chat_history=chat_history)


def flush_log_history(reason: str) -> None:
    # chat_history always starts seeded with the chat system prompt, so check if
    # lenght 1 as it means no user turns have happened; skip any write.

    if len(log_history.log_chat_history) <= 1 and not log_history.log_lexical_history:
        return
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_history.unload_and_pack(reason)) + "\n")
