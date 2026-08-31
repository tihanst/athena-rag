from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel


class LLMModel(BaseModel):
    model_provider: str
    model_name: str
    model_id: str
    is_local: bool = False


class LLMSettings(BaseSettings):
    search_planner_llm: LLMModel
    chat_llm: LLMModel
    summarizer_llm: LLMModel

    model_config = SettingsConfigDict(
        env_file=".env", env_nested_delimiter="__", extra="ignore"
    )


class XEncoder(BaseSettings):
    cross_encoder_model: str
    cross_encoder_top_k: int

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


llm_settings = LLMSettings()
xencoder_settings = XEncoder()

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
MARKDOWN_DIR = UPLOAD_DIR / "markdowns"
MARKDOWN_DIR.mkdir(exist_ok=True)


if __name__ == "__main__":
    print(llm_settings)
