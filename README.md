# Alchemy

Alchemy is a local spoken-word-to-image visualiser.

The project is being rebuilt around a cleaner controller package that drives
ComfyUI as a local image-rendering service. The older root-level scripts are
prototype experiments and are kept for reference while the new package takes
shape.

Current working path:

```text
prompt or spoken fragment
  -> Python controller
  -> optional Ollama prompt refinement
  -> ComfyUI workflow API
  -> generated image
  -> output/current.png
```

Planned path:

```text
microphone or audio file
  -> speech-to-text
  -> Ollama prompt refinement
  -> ComfyUI workflow API
  -> generated image
  -> viewer or TouchDesigner
```

## Installation

### 1. Install ComfyUI

Install and run ComfyUI separately from this repository.

Official install docs:

- <https://docs.comfy.org/installation/desktop/macos>
- <https://github.com/comfy-org/ComfyUI>

ComfyUI should be running at:

```text
http://127.0.0.1:8188
```

Add at least one compatible checkpoint to ComfyUI's model directory. The first
exported workflow in this repo currently expects:

```text
sd_xl_turbo_1.0_fp16.safetensors
```

The model name can be changed later by editing or re-exporting the workflow.

### 2. Install Ollama

Install Ollama separately from this repository.

Official install docs:

- <https://docs.ollama.com/macos>
- <https://docs.ollama.com/>

After installing, start Ollama and pull a small local model:

```bash
ollama pull llama3.2:3b
```

The default `.env.example` expects:

```bash
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2:3b
```

You can use a different installed Ollama model by changing `OLLAMA_MODEL`.

### 3. Install uv

This project uses `uv` for Python packaging and dependency management.

On macOS with Homebrew:

```bash
brew install uv
```

### 4. Install project dependencies

From the repository root:

```bash
uv sync
```

This creates a local `.venv` and installs the package dependencies from
`pyproject.toml`.

### 5. Configure local paths

Create a local `.env` file from the example:

```bash
cp .env.example .env
```

Set `COMFY_OUTPUT_DIR` to ComfyUI's output directory.

Example:

```bash
COMFY_OUTPUT_DIR=/Users/alex/ComfyUI/output
```

This lets the controller copy ComfyUI's latest generated file to:

```text
output/current.png
```

Your `.env` file is local-only and should not be committed.

## Service Check

The project depends on multiple local services. Use the doctor command when
something feels unclear:

```bash
uv run alchemy-doctor
```

It checks:

- ComfyUI is reachable.
- The configured workflow exists.
- `COMFY_OUTPUT_DIR` exists.
- The workflow checkpoint is visible to ComfyUI.
- Ollama is reachable.
- The configured Ollama model is installed.

When a check fails, the command prints the next action to take.

## First Tests

With ComfyUI running, submit a prompt:

```bash
uv run alchemy-submit "ink wash projection artwork, luminous fragments of spoken language becoming an abstract landscape, theatrical lighting, soft grain"
```

Expected result:

```text
Submitted prompt ...
Updated output/current.png
```

Open or watch:

```text
output/current.png
```

This is the first stable integration point for a viewer or TouchDesigner.

To test Ollama prompt refinement without generating an image:

```bash
uv run alchemy-refine "the room remembers a storm that has not arrived yet"
```

To refine a spoken fragment and submit the resulting prompt to ComfyUI:

```bash
uv run alchemy-submit --refine "the room remembers a storm that has not arrived yet"
```

## Project Structure

```text
src/alchemy/
  config.py
  comfy_client.py
  ollama_client.py
  prompt_agent.py
  services.py
  workflow.py
  image_state.py
  cli/

workflows/
  sdxl_turbo_txt2img.json

scripts/
  test_submit_prompt.py

output/
  current.png
```

## Current Status

Working:

- `uv` package scaffold.
- ComfyUI API workflow submission.
- Local service detection with `alchemy-doctor`.
- Ollama prompt refinement.
- Prompt replacement.
- Seed randomisation.
- Generated image discovery through ComfyUI history.
- Copying latest image to `output/current.png`.

Next:

- Speech-to-text input.
- img2img feedback workflow.
- Simple viewer or TouchDesigner reload path.

See [demo-plan.md](demo-plan.md) for the short-term demo plan.
