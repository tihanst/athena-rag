"""Basic singleton memory module for a chat session. Resets on /chat/reset route. Does not reset on refresh of web app page"""

from pydantic import BaseModel

from app.schemas import ChatHistoryItem, ChatSystem
from app.prompts import RAG_CHAT_SYSTEM_PROMPT


class ChatHistory(BaseModel):
    history: list[ChatHistoryItem] = []

    def to_message_list(self) -> list[dict]:
        return [{"role": item.role, "content": item.content} for item in self.history]

    def add_message(self, message: ChatHistoryItem) -> None:
        self.history.append(message)

    def clear_conversation_history(self) -> None:
        self.history = []


chat_history = ChatHistory()

chat_history.add_message(ChatSystem(role="system", content=RAG_CHAT_SYSTEM_PROMPT))
