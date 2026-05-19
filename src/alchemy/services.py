from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from alchemy.config import Settings
from alchemy.ollama_client import OllamaClient
from alchemy.prompt_profile import load_prompt_profile
from alchemy.workflow import load_workflow


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str
    fix: str | None = None


def run_checks(settings: Settings) -> list[CheckResult]:
    return [
        check_comfy(settings),
        check_workflow(settings.alchemy_workflow),
        check_workflow(settings.alchemy_feedback_workflow, name="Feedback workflow file"),
        check_prompt_profile(settings.alchemy_prompt_profile),
        check_comfy_output_dir(settings.comfy_output_dir),
        check_comfy_input_dir(settings.comfy_input_dir),
        check_workflow_checkpoint(settings),
        check_ollama(settings),
        check_whisper_cpp(settings),
    ]


def check_comfy(settings: Settings) -> CheckResult:
    try:
        response = requests.get(f"{settings.comfy_base_url}/system_stats", timeout=5)
        response.raise_for_status()
    except requests.RequestException as error:
        return CheckResult(
            "ComfyUI service",
            False,
            f"Could not reach {settings.comfy_base_url}: {error}",
            "Start ComfyUI and confirm http://127.0.0.1:8188 opens in a browser.",
        )

    return CheckResult("ComfyUI service", True, f"Reachable at {settings.comfy_base_url}")


def check_workflow(path: Path, *, name: str = "Workflow file") -> CheckResult:
    if not path.exists():
        return CheckResult(
            name,
            False,
            f"{path} does not exist",
            "Export a ComfyUI API workflow and set ALCHEMY_WORKFLOW in .env.",
        )

    try:
        load_workflow(path)
    except (OSError, ValueError) as error:
        return CheckResult(
            name,
            False,
            f"{path} could not be loaded: {error}",
            "Re-export the workflow from ComfyUI using API format.",
        )

    return CheckResult(name, True, f"Loaded {path}")


def check_prompt_profile(path: Path) -> CheckResult:
    if not path.exists():
        return CheckResult(
            "Prompt profile",
            False,
            f"{path} does not exist",
            "Create a prompt profile TOML file or set ALCHEMY_PROMPT_PROFILE in .env.",
        )

    try:
        profile = load_prompt_profile(path)
    except (OSError, KeyError, ValueError) as error:
        return CheckResult(
            "Prompt profile",
            False,
            f"{path} could not be loaded: {error}",
            "Check that the profile contains name, system, template, and style fields.",
        )

    return CheckResult("Prompt profile", True, f"Loaded {profile.name} from {path}")


def check_comfy_output_dir(path: Path | None) -> CheckResult:
    if path is None:
        return CheckResult(
            "ComfyUI output directory",
            False,
            "COMFY_OUTPUT_DIR is not set",
            "Set COMFY_OUTPUT_DIR in .env to your ComfyUI output directory.",
        )

    if not path.exists():
        return CheckResult(
            "ComfyUI output directory",
            False,
            f"{path} does not exist",
            "Set COMFY_OUTPUT_DIR to the directory where ComfyUI saves generated images.",
        )

    return CheckResult("ComfyUI output directory", True, str(path))


def check_comfy_input_dir(path: Path | None) -> CheckResult:
    if path is None:
        return CheckResult(
            "ComfyUI input directory",
            False,
            "COMFY_INPUT_DIR is not set",
            "Set COMFY_INPUT_DIR in .env to your ComfyUI input directory for img2img feedback.",
        )

    if not path.exists():
        return CheckResult(
            "ComfyUI input directory",
            False,
            f"{path} does not exist",
            "Set COMFY_INPUT_DIR to the directory where ComfyUI Load Image reads input images.",
        )

    return CheckResult("ComfyUI input directory", True, str(path))


def check_workflow_checkpoint(settings: Settings) -> CheckResult:
    try:
        workflow = load_workflow(settings.alchemy_workflow)
        checkpoint = _workflow_checkpoint_name(workflow)
    except (OSError, ValueError, KeyError) as error:
        return CheckResult(
            "Workflow checkpoint",
            False,
            f"Could not inspect workflow checkpoint: {error}",
        )

    if checkpoint is None:
        return CheckResult(
            "Workflow checkpoint",
            False,
            "No CheckpointLoaderSimple node found",
            "Use a workflow with a checkpoint loader, or update the workflow inspector.",
        )

    try:
        response = requests.get(
            f"{settings.comfy_base_url}/object_info/CheckpointLoaderSimple",
            timeout=5,
        )
        response.raise_for_status()
        object_info = response.json()
    except requests.RequestException:
        return CheckResult(
            "Workflow checkpoint",
            True,
            f"Workflow expects {checkpoint}; could not confirm against ComfyUI model list",
        )

    known_checkpoints = _checkpoint_options(object_info)
    if known_checkpoints and checkpoint not in known_checkpoints:
        return CheckResult(
            "Workflow checkpoint",
            False,
            f"Workflow expects {checkpoint}, but ComfyUI did not list it",
            "Symlink or copy the checkpoint into ComfyUI/models/checkpoints, or re-export the workflow.",
        )

    return CheckResult("Workflow checkpoint", True, f"Workflow expects {checkpoint}")


def check_ollama(settings: Settings) -> CheckResult:
    client = OllamaClient(settings.ollama_host, settings.ollama_model)
    try:
        models = client.list_models()
    except requests.RequestException as error:
        return CheckResult(
            "Ollama service",
            False,
            f"Could not reach {settings.ollama_host}: {error}",
            "Install/start Ollama, then run `ollama pull "
            f"{settings.ollama_model}` or change OLLAMA_MODEL in .env.",
        )

    if settings.ollama_model not in models:
        return CheckResult(
            "Ollama model",
            False,
            f"{settings.ollama_model} is not installed. Installed: {', '.join(models) or '(none)'}",
            f"Run `ollama pull {settings.ollama_model}` or set OLLAMA_MODEL to an installed model.",
        )

    return CheckResult("Ollama service", True, f"Using {settings.ollama_model}")


def check_whisper_cpp(settings: Settings) -> CheckResult:
    try:
        response = requests.options(settings.whisper_cpp_inference_url, timeout=5)
    except requests.RequestException as error:
        return CheckResult(
            "whisper.cpp service",
            False,
            f"Could not reach {settings.whisper_cpp_inference_url}: {error}",
            "Start whisper-server and confirm the configured inference endpoint is reachable.",
        )

    if response.status_code >= 500:
        return CheckResult(
            "whisper.cpp service",
            False,
            f"{settings.whisper_cpp_inference_url} returned HTTP {response.status_code}",
            "Check whisper-server logs and WHISPER_CPP_* settings in .env.",
        )

    return CheckResult(
        "whisper.cpp service",
        True,
        f"Endpoint reachable at {settings.whisper_cpp_inference_url}",
    )


def _workflow_checkpoint_name(workflow: dict[str, Any]) -> str | None:
    for node in workflow.values():
        if node.get("class_type") == "CheckpointLoaderSimple":
            return node.get("inputs", {}).get("ckpt_name")
    return None


def _checkpoint_options(object_info: dict[str, Any]) -> list[str]:
    inputs = object_info.get("CheckpointLoaderSimple", {}).get("input", {}).get("required", {})
    ckpt_name = inputs.get("ckpt_name", [])
    if not ckpt_name:
        return []
    options = ckpt_name[0]
    return options if isinstance(options, list) else []
