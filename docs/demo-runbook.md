# Demo Runbook

This is the shortest reliable path for running the current Alchemy demo.

## 1. Start Local Services

Start these separately:

```text
ComfyUI
Ollama
whisper.cpp whisper-server
```

Then from the repo root, verify everything:

```bash
uv run alchemy-doctor
```

Expected result: every check prints `OK`.

## 2. Start The Viewer

In terminal 1:

```bash
uv run alchemy-viewer
```

Open this in a browser:

```text
http://127.0.0.1:8765
```

Put the browser fullscreen for projection.

## 3. Run The Demo

In terminal 2:

```bash
uv run alchemy-demo examples/example-poem.m4a
```

This runs:

```text
audio file
  -> whisper.cpp transcription
  -> transcript chunking
  -> realtime scheduling
  -> Ollama prompt refinement
  -> ComfyUI txt2img for the first chunk
  -> ComfyUI img2img feedback for later chunks
  -> output/current.png
  -> browser viewer refresh
```

## Useful Variations

Run faster than realtime:

```bash
uv run alchemy-demo examples/example-poem.m4a --delay-scale 0.5
```

Use fewer, larger chunks:

```bash
uv run alchemy-demo examples/example-poem.m4a --max-words 40 --max-seconds 14
```

Run without realtime scheduling:

```bash
uv run alchemy-demo examples/example-poem.m4a --no-realtime
```

Run without img2img feedback:

```bash
uv run alchemy-demo examples/example-poem.m4a --no-feedback
```

Skip service checks once everything is known to be running:

```bash
uv run alchemy-demo examples/example-poem.m4a --skip-doctor
```

## Common Fixes

If ComfyUI fails:

```text
Open http://127.0.0.1:8188 and confirm the server is running.
Confirm the workflow checkpoint exists in ComfyUI.
```

If `COMFY_OUTPUT_DIR` fails:

```text
Set COMFY_OUTPUT_DIR in .env to ComfyUI's output directory.
```

If `COMFY_INPUT_DIR` fails:

```text
Set COMFY_INPUT_DIR in .env to ComfyUI's input directory.
This is required for img2img feedback.
```

If Ollama fails:

```bash
ollama list
ollama pull llama3.2:3b
```

Or set `OLLAMA_MODEL` in `.env` to an installed model.

If whisper.cpp fails:

```text
Start whisper-server and confirm the /inference endpoint is reachable.
```

Example:

```bash
./build/bin/whisper-server \
  -m models/ggml-base.en.bin \
  --host 127.0.0.1 \
  --port 8080
```

## Tuning Notes

If images lag too far behind the audio, use larger chunks:

```bash
--max-words 40 --max-seconds 14
```

If you want the visuals to react more often, use smaller chunks:

```bash
--max-words 20 --max-seconds 6
```

If ComfyUI cannot keep up, keep:

```bash
--backpressure latest
```

If you need to inspect the relationship between source text and images, keep:

```bash
--monitor
```
