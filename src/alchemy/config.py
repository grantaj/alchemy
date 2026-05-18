from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


load_dotenv()


class Settings(BaseSettings):
    """Runtime configuration for the local controller."""

    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    comfy_host: str = Field(default="127.0.0.1", alias="COMFY_HOST")
    comfy_port: int = Field(default=8188, alias="COMFY_PORT")
    comfy_output_dir: Path | None = Field(default=None, alias="COMFY_OUTPUT_DIR")
    ollama_host: str = Field(default="http://127.0.0.1:11434", alias="OLLAMA_HOST")
    ollama_model: str = Field(default="llama3.2:3b", alias="OLLAMA_MODEL")

    alchemy_output_dir: Path = Field(default=Path("output"), alias="ALCHEMY_OUTPUT_DIR")
    alchemy_workflow: Path = Field(
        default=Path("workflows/sdxl_turbo_txt2img.json"),
        alias="ALCHEMY_WORKFLOW",
    )
    alchemy_prompt_profile: Path = Field(
        default=Path("prompts/default.toml"),
        alias="ALCHEMY_PROMPT_PROFILE",
    )
    alchemy_current_image: Path = Field(
        default=Path("output/current.png"),
        alias="ALCHEMY_CURRENT_IMAGE",
    )
    alchemy_default_negative: str = Field(
        default="text, watermark, detail, low quality",
        alias="ALCHEMY_DEFAULT_NEGATIVE",
    )
    alchemy_style: str = Field(
        default=(
            "ink wash projection artwork, theatrical lighting, soft grain, "
            "high contrast, poetic abstraction"
        ),
        alias="ALCHEMY_STYLE",
    )

    @property
    def comfy_base_url(self) -> str:
        return f"http://{self.comfy_host}:{self.comfy_port}"

    @property
    def comfy_ws_url(self) -> str:
        return f"ws://{self.comfy_host}:{self.comfy_port}/ws"


def load_settings() -> Settings:
    return Settings()
