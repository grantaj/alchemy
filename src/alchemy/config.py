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
    comfy_input_dir: Path | None = Field(default=None, alias="COMFY_INPUT_DIR")
    ollama_host: str = Field(default="http://127.0.0.1:11434", alias="OLLAMA_HOST")
    ollama_model: str = Field(default="llama3.2:3b", alias="OLLAMA_MODEL")
    whisper_cpp_host: str = Field(default="http://127.0.0.1:8080", alias="WHISPER_CPP_HOST")
    whisper_cpp_inference_path: str = Field(
        default="/inference",
        alias="WHISPER_CPP_INFERENCE_PATH",
    )

    alchemy_output_dir: Path = Field(default=Path("output"), alias="ALCHEMY_OUTPUT_DIR")
    alchemy_workflow: Path = Field(
        default=Path("workflows/sdxl_turbo_txt2img.json"),
        alias="ALCHEMY_WORKFLOW",
    )
    alchemy_feedback_workflow: Path = Field(
        default=Path("workflows/sdxl_turbo_img2img.json"),
        alias="ALCHEMY_FEEDBACK_WORKFLOW",
    )
    alchemy_prompt_profile: Path = Field(
        default=Path("prompts/default.toml"),
        alias="ALCHEMY_PROMPT_PROFILE",
    )
    alchemy_current_image: Path = Field(
        default=Path("output/current.png"),
        alias="ALCHEMY_CURRENT_IMAGE",
    )
    alchemy_initial_image: Path = Field(
        default=Path("output/initial.png"),
        alias="ALCHEMY_INITIAL_IMAGE",
    )
    alchemy_initial_width: int = Field(default=512, alias="ALCHEMY_INITIAL_WIDTH")
    alchemy_initial_height: int = Field(default=512, alias="ALCHEMY_INITIAL_HEIGHT")
    alchemy_initial_color: str = Field(default="#000000", alias="ALCHEMY_INITIAL_COLOR")
    alchemy_initial_denoise: float = Field(default=1.0, alias="ALCHEMY_INITIAL_DENOISE")
    alchemy_default_negative: str = Field(
        default=(
            "text, watermark, detail, low quality, photorealistic, realistic, "
            "photo, photography, lens, portrait, skin, face, 3d render, cgi, "
            "softbox, depth of field, camera, documentary, installation view, "
            "centered ink blot, blob, cloud, smoke, smoky wash, swirl, marbling, "
            "rorschach, generic ink abstraction"
        ),
        alias="ALCHEMY_DEFAULT_NEGATIVE",
    )
    alchemy_style: str = Field(
        default=(
            "flat non-photographic mixed-media paper score, abstract process drawing, "
            "masked pigment, ruled graphite, rubbed charcoal, rough paper grain, "
            "hand-worked edges, high contrast, restrained poetic abstraction, "
            "consistent monochrome black ink and graphite on warm off-white paper, "
            "no camera realism, no photographed scene"
        ),
        alias="ALCHEMY_STYLE",
    )
    alchemy_chunk_max_seconds: float = Field(default=8.0, alias="ALCHEMY_CHUNK_MAX_SECONDS")
    alchemy_chunk_max_words: int = Field(default=35, alias="ALCHEMY_CHUNK_MAX_WORDS")
    alchemy_chunk_min_words: int = Field(default=5, alias="ALCHEMY_CHUNK_MIN_WORDS")
    alchemy_chunk_min_silence_gap: float = Field(
        default=0.7,
        alias="ALCHEMY_CHUNK_MIN_SILENCE_GAP",
    )
    alchemy_chunk_prefer_sentence_boundary: bool = Field(
        default=True,
        alias="ALCHEMY_CHUNK_PREFER_SENTENCE_BOUNDARY",
    )
    alchemy_chunk_sentence_punctuation: str = Field(
        default=".?!;:",
        alias="ALCHEMY_CHUNK_SENTENCE_PUNCTUATION",
    )
    alchemy_backpressure_mode: str = Field(default="latest", alias="ALCHEMY_BACKPRESSURE_MODE")
    alchemy_delay_scale: float = Field(default=1.0, alias="ALCHEMY_DELAY_SCALE")
    alchemy_audio_player: str = Field(default="afplay", alias="ALCHEMY_AUDIO_PLAYER")
    alchemy_viewer_host: str = Field(default="127.0.0.1", alias="ALCHEMY_VIEWER_HOST")
    alchemy_viewer_port: int = Field(default=8765, alias="ALCHEMY_VIEWER_PORT")

    @property
    def comfy_base_url(self) -> str:
        return f"http://{self.comfy_host}:{self.comfy_port}"

    @property
    def comfy_ws_url(self) -> str:
        return f"ws://{self.comfy_host}:{self.comfy_port}/ws"

    @property
    def whisper_cpp_inference_url(self) -> str:
        return f"{self.whisper_cpp_host.rstrip('/')}/{self.whisper_cpp_inference_path.lstrip('/')}"


def load_settings() -> Settings:
    return Settings()
