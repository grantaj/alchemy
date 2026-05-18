from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class PromptProfile:
    name: str
    system: str
    template: str
    style: str

    def render(
        self,
        *,
        transcription: str,
        negative_prompt: str,
        style: str | None = None,
        previous_prompt: str = "",
        state_summary: str = "",
    ) -> str:
        return self.template.format(
            transcription=transcription,
            style=(style or self.style).strip(),
            previous_prompt=previous_prompt or "(none)",
            state_summary=state_summary or "(none)",
            negative_prompt=negative_prompt,
        )


def load_prompt_profile(path: Path) -> PromptProfile:
    with path.open("rb") as profile_file:
        data = tomllib.load(profile_file)

    return PromptProfile(
        name=data.get("name", path.stem),
        system=data["system"].strip(),
        template=data["template"].strip(),
        style=data["style"].strip(),
    )
