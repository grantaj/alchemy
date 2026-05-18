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

### 3. Install whisper.cpp

Install whisper.cpp separately from this repository.

Official install docs:

- <https://github.com/ggml-org/whisper.cpp>

Build from source:

```bash
git clone https://github.com/ggml-org/whisper.cpp.git
cd whisper.cpp
cmake -B build
cmake --build build -j --config Release
```

Download a model. Start with `base.en` or `small.en` for fast local testing:

```bash
./models/download-ggml-model.sh base.en
```

Start the HTTP server:

```bash
./build/bin/whisper-server \
  -m models/ggml-base.en.bin \
  --host 127.0.0.1 \
  --port 8080
```

The default `.env.example` expects:

```bash
WHISPER_CPP_HOST=http://127.0.0.1:8080
WHISPER_CPP_INFERENCE_PATH=/inference
```

The project uses this endpoint for file-based transcription.

Install `ffmpeg` if you want to transcribe compressed audio such as `.m4a`:

```bash
brew install ffmpeg
```

The controller converts non-WAV files to temporary 16 kHz mono WAV files before
sending them to whisper.cpp.

### 4. Install uv

This project uses `uv` for Python packaging and dependency management.

On macOS with Homebrew:

```bash
brew install uv
```

### 5. Install project dependencies

From the repository root:

```bash
uv sync
```

This creates a local `.venv` and installs the package dependencies from
`pyproject.toml`.

### 6. Configure local paths

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
- The configured prompt profile exists and can be loaded.
- `COMFY_OUTPUT_DIR` exists.
- The workflow checkpoint is visible to ComfyUI.
- Ollama is reachable.
- The configured Ollama model is installed.
- whisper.cpp's inference endpoint is reachable.

When a check fails, the command prints the next action to take.

## Speech-To-Text Direction

The first transcription backend will be whisper.cpp over its local HTTP server.
This matches the rest of the system: local-first, scriptable, and easy for
`alchemy-doctor` to detect.

For the demo, the first speech milestone should be file-based:

```text
example spoken poem
  -> whisper.cpp transcription
  -> Ollama prompt profile
  -> ComfyUI image
```

After that, microphone capture can be added as phrase-based transcription.

Other options may be useful later:

- `faster-whisper`: good Python ergonomics, but less directly aligned with
  Apple Silicon/Metal than whisper.cpp.
- Vosk/Vosk server: fast and stream-oriented, but generally less rich for
  poetic spoken-word transcription than Whisper-class models.
- WhisperKit or MLX-based tools: promising on Apple Silicon, but would add a
  different integration surface than the current Python/HTTP controller.

So the current plan is: use whisper.cpp first, keep the STT module abstract
enough to swap later.

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

This prints a poetic response, the resulting image prompt, and the state summary
that can be carried into the next generation.

To refine a spoken fragment and submit the resulting prompt to ComfyUI:

```bash
uv run alchemy-submit --refine "the room remembers a storm that has not arrived yet"
```

To see the full JSON packet:

```bash
uv run alchemy-refine --json "the room remembers a storm that has not arrived yet"
```

To transcribe an audio file with whisper.cpp:

```bash
uv run alchemy-transcribe example-poem-a-summar-day.m4a
```

To inspect timestamped segments or configured chunks:

```bash
uv run alchemy-transcribe --segments example-poem-a-summar-day.m4a
uv run alchemy-transcribe --chunks example-poem-a-summar-day.m4a
```

To run the current full file-based path:

```bash
uv run alchemy-from-audio example-poem-a-summar-day.m4a
```

That performs:

```text
audio file
  -> whisper.cpp transcription
  -> Ollama prompt profile
  -> ComfyUI image
  -> output/current.png
```

To generate a sequence of images from transcript chunks:

```bash
uv run alchemy-from-audio --chunked example-poem-a-summar-day.m4a
```

## Prompt Profiles

Ollama prompt refinement is configured with TOML prompt profiles.

The default profile is:

```text
prompts/default.toml
```

Profiles define:

- `system`: the Ollama system instruction.
- `template`: the user prompt template.
- `style`: the pinned visual style for the session.

The template receives these fields:

- `{transcription}`
- `{style}`
- `{previous_prompt}`
- `{state_summary}`
- `{negative_prompt}`

The expected Ollama JSON response is:

```json
{
  "poetic_response": "...",
  "positive_prompt": "...",
  "negative_prompt": "...",
  "state_summary": "...",
  "denoise_strength": 0.45,
  "reset": false
}
```

The controller pins `negative_prompt` from configuration after parsing, so the
LLM can focus on the poetic response and positive image prompt.

## Transcript Chunking

Longer transcriptions can be split into semi-streaming chunks before prompt
refinement.

Chunking is configured with environment variables:

```bash
ALCHEMY_CHUNK_MAX_SECONDS=8.0
ALCHEMY_CHUNK_MAX_WORDS=35
ALCHEMY_CHUNK_MIN_WORDS=5
ALCHEMY_CHUNK_MIN_SILENCE_GAP=0.7
ALCHEMY_CHUNK_PREFER_SENTENCE_BOUNDARY=true
ALCHEMY_CHUNK_SENTENCE_PUNCTUATION=.?!;:
```

The chunker tries to keep chunks natural by using whisper.cpp word timestamps,
silence gaps, duration limits, word-count limits, and punctuation boundaries.

Useful test overrides:

```bash
uv run alchemy-transcribe --chunks example-poem-a-summar-day.m4a --max-words 20 --max-seconds 6
uv run alchemy-from-audio --chunked example-poem-a-summar-day.m4a --max-words 20 --max-seconds 6
```

## Project Structure

```text
src/alchemy/
  config.py
  comfy_client.py
  ollama_client.py
  prompt_agent.py
  prompt_profile.py
  services.py
  workflow.py
  image_state.py
  cli/

prompts/
  default.toml

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
- Configurable Ollama prompt profiles.
- Poetic response plus image prompt refinement.
- Prompt replacement.
- Seed randomisation.
- Generated image discovery through ComfyUI history.
- Copying latest image to `output/current.png`.

Next:

- Speech-to-text input.
- img2img feedback workflow.
- Simple viewer or TouchDesigner reload path.

See [demo-plan.md](demo-plan.md) for the short-term demo plan.
