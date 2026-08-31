from litellm import completion, acompletion

from app.config import llm_settings
from app.memory import ChatHistory


class LLM:
    def __init__(
        self,
        model_provider: str,
        model_name: str,
        model_id: str,
        is_local: bool = False,
    ):
        self.provider = model_provider
        self.model = model_name
        self.id = model_id

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(provider={self.provider}, model={self.model}, model id={self.id} )"

    async def acompletion_call(self, messages: ChatHistory, *args, **kwargs):  #
        mess = (
            messages.to_message_list()
        )  # Assumes system message is present in ChatHistory
        try:
            return await acompletion(
                self.id, mess, *args, **kwargs
            )  # Note litellm.completion for together requires endpoint as model name
        except Exception as e:
            raise RuntimeError(
                f"LiteLLM completion failed for provider '{self.provider}' with details {repr(self)}. Ensure it is supported by LiteLLM, that the model id is correctly specified, and the appropriate API key is set in your environment.\n\nOriginal error: {e}\n"
            )


search_planner_llm = LLM(**llm_settings.search_planner_llm.model_dump())
chat_llm = LLM(**llm_settings.chat_llm.model_dump())
summarizer_llm = LLM(**llm_settings.summarizer_llm.model_dump())

llms = {
    "search_planner_llm": search_planner_llm,
    "chat_llm": chat_llm,
    "summarizer_llm": summarizer_llm,
}
