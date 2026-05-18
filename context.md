# context.md — Local Speech-to-Image ComfyUI Uplift

## Project summary

This project is an uplift of an existing prototype speech-to-image generator.

The older prototype pipeline was approximately:

```text
microphone / speech
  → Whisper
  → Ollama
  → Stable Diffusion
  → generated image output
```

The goal is to modernise this into a more robust, modular, local-first system using ComfyUI as the image-generation backend.

The target platform is macOS, preferably Apple Silicon, running everything locally.

The desired result is not a polished consumer app, but a working creative/performance system suitable for live experimentation, installation, projection, or integration with tools such as TouchDesigner.

---

## Core design goal

Build a local speech-driven image system with this architecture:

```text
microphone
  → local speech-to-text
  → local prompt-refinement LLM
  → ComfyUI workflow API
  → generated image
  → display / output folder / TouchDesigner
```

ComfyUI should be treated as a local image-rendering service, not as the whole application.

The controller application should own:

- audio capture
- speech segmentation
- prompt refinement
- workflow parameter mutation
- job submission
- progress tracking
- output handling
- state across generations

ComfyUI should own:

- model loading
- image-generation workflow
- img2img / txt2img / VAE / sampler nodes
- output image generation

---

## Local-first constraints

The system should run locally as much as possible.

Preferred local components:

- ComfyUI for image generation
- Ollama for local prompt refinement
- whisper.cpp or faster-whisper for speech-to-text
- Python controller script/app
- local filesystem for image output
- optional TouchDesigner folder watch / input integration

Avoid cloud APIs in the core path.

---

## Existing model assumption

The user may already have an SD Turbo 1.5 model downloaded.

The first implementation should target SD1.5 Turbo / SD Turbo-style workflows because they are fast, responsive, and likely to run acceptably on macOS.

Prioritise latency and creative continuity over maximum photorealistic quality.

---

## Why ComfyUI

ComfyUI is useful here because it allows visual construction of image-generation workflows and then external control via API.

The intended workflow is:

1. Build and test a workflow manually in the ComfyUI UI.
2. Save/export the workflow JSON.
3. Treat the workflow JSON as a template.
4. Write Python code that mutates only the important fields:
   - positive prompt
   - negative prompt
   - seed
   - denoise strength
   - previous image path
   - resolution
   - sampler settings
   - output prefix
5. Submit the mutated workflow to ComfyUI using its local HTTP API.
6. Track generation progress using WebSocket events.
7. Retrieve or locate the output image.

---

## Suggested repository structure

```text
speech-comfy/
  README.md
  context.md
  requirements.txt
  .env.example
  workflows/
    sd15_turbo_txt2img.json
    sd15_turbo_img2img.json
  src/
    main.py
    config.py
    audio_input.py
    speech_to_text.py
    prompt_agent.py
    comfy_client.py
    image_state.py
    output_viewer.py
  scripts/
    run_comfy.sh
    test_submit_prompt.py
    test_microphone.py
  output/
    .gitkeep
```

---

## MVP milestones

### Milestone 1 — ComfyUI running locally

Install and run ComfyUI on macOS.

Expected launch shape:

```bash
python main.py
```

or, if using Comfy CLI:

```bash
comfy launch -- --listen 127.0.0.1 --port 8188
```

Expected browser URL:

```text
http://127.0.0.1:8188
```

The SD Turbo / SD1.5 Turbo checkpoint should be placed in:

```text
ComfyUI/models/checkpoints/
```

Then restart ComfyUI and confirm the checkpoint appears in the checkpoint loader node.

---

### Milestone 2 — Manual ComfyUI workflow

Create a simple txt2img workflow manually in ComfyUI.

Minimum workflow:

```text
Checkpoint Loader
  → CLIP Text Encode positive
  → CLIP Text Encode negative
  → Empty Latent Image
  → KSampler
  → VAE Decode
  → Save Image
```

For SD Turbo-like models, start with low step counts.

Useful starting parameters:

```text
steps: 1–4
CFG: low, often around 1–2
resolution: 512x512 or 768x768
sampler: start with whatever the SD Turbo workflow recommends
scheduler: start with the model/workflow default
```

Save/export this as:

```text
workflows/sd15_turbo_txt2img.json
```

---

### Milestone 3 — Python can submit one prompt

Create a minimal `comfy_client.py` that can:

- load workflow JSON
- replace the positive prompt
- optionally replace the negative prompt
- randomise or set seed
- submit to ComfyUI `/prompt`
- wait for completion or poll history
- return output image filename/path

This milestone proves the controller can drive ComfyUI.

---

### Milestone 4 — Add WebSocket progress tracking

Add WebSocket support to track:

- job queued
- node executing
- generation completed
- errors

The UI does not need to be fancy. Console logs are fine.

---

### Milestone 5 — Add Ollama prompt refinement

Create `prompt_agent.py`.

Input:

```text
raw spoken text
current visual state summary
optional previous prompt
optional performance style
```

Output:

```json
{
  "positive_prompt": "...",
  "negative_prompt": "...",
  "state_summary": "...",
  "seed_mode": "reuse|random|increment",
  "denoise_strength": 0.45
}
```

Keep the local LLM prompt short and deterministic.

The LLM should not write essays. It should transform speech into compact visual instructions.

Example system behaviour:

```text
You convert fragments of spoken language into concise image-generation prompts.
Preserve continuity with the previous image.
Prefer vivid concrete visual language.
Do not explain.
Return JSON only.
```

---

### Milestone 6 — Add speech input

Use either:

- whisper.cpp
- faster-whisper

The first version can be phrase-based rather than truly streaming.

Acceptable MVP behaviour:

```text
record until silence
transcribe phrase
send phrase to prompt_agent
generate image
repeat
```

Later this can become more continuous.

---

### Milestone 7 — Add image feedback / img2img

This is the most important creative upgrade.

Create a second ComfyUI workflow:

```text
previous generated image
  → VAE Encode
  → KSampler with denoise < 1.0
  → VAE Decode
  → Save Image
```

Save/export as:

```text
workflows/sd15_turbo_img2img.json
```

The controller should keep track of the latest generated image and pass it back into the next generation.

This allows the system to evolve rather than reset on every spoken phrase.

Suggested starting denoise values:

```text
0.25 subtle evolution
0.45 noticeable transformation
0.70 major transformation
1.00 full reset
```

---

## Important creative behaviour

The system should feel alive, responsive, and cumulative.

Better to generate a slightly rough image quickly than a polished image slowly.

Key behaviours to support:

- each spoken phrase modifies the existing visual state
- silence can allow slow mutation or drift
- repeated words can reinforce image features
- emotional tone can modify colour, contrast, abstraction, or denoise
- the user can reset the visual state manually
- the user can pin a style for a session

---

## Suggested runtime modes

### Mode 1 — txt2img

Every phrase creates a new image from scratch.

Useful for testing.

### Mode 2 — img2img feedback

Every phrase transforms the previous output.

Best for live performance.

### Mode 3 — hybrid

Occasionally reset to txt2img if:

- the user says “reset”
- the image becomes visually muddy
- denoise has remained low for too long
- a new scene is requested explicitly

---

## Example controller loop

```python
while True:
    phrase = speech_to_text.listen_for_phrase()

    if not phrase:
        continue

    prompt_packet = prompt_agent.refine(
        phrase=phrase,
        previous_prompt=image_state.previous_prompt,
        state_summary=image_state.summary,
    )

    if image_state.latest_image is None or prompt_packet.reset:
        workflow = workflow_loader.load("sd15_turbo_txt2img.json")
    else:
        workflow = workflow_loader.load("sd15_turbo_img2img.json")
        workflow = workflow_editor.set_input_image(
            workflow,
            image_state.latest_image,
        )

    workflow = workflow_editor.set_positive_prompt(
        workflow,
        prompt_packet.positive_prompt,
    )

    workflow = workflow_editor.set_negative_prompt(
        workflow,
        prompt_packet.negative_prompt,
    )

    workflow = workflow_editor.set_seed(
        workflow,
        image_state.next_seed(prompt_packet.seed_mode),
    )

    workflow = workflow_editor.set_denoise(
        workflow,
        prompt_packet.denoise_strength,
    )

    result = comfy_client.submit_and_wait(workflow)

    image_state.update(
        latest_image=result.image_path,
        previous_prompt=prompt_packet.positive_prompt,
        summary=prompt_packet.state_summary,
    )

    output_viewer.show(result.image_path)
```

---

## Configuration

Use a simple config file or environment variables.

Example `.env.example`:

```bash
COMFY_HOST=127.0.0.1
COMFY_PORT=8188
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2:3b
OUTPUT_DIR=./output
DEFAULT_WORKFLOW=workflows/sd15_turbo_txt2img.json
FEEDBACK_WORKFLOW=workflows/sd15_turbo_img2img.json
DEFAULT_WIDTH=512
DEFAULT_HEIGHT=512
DEFAULT_STEPS=4
DEFAULT_CFG=1.5
DEFAULT_DENOISE=0.45
```

---

## macOS notes

On macOS, especially Apple Silicon, PyTorch uses the MPS backend rather than CUDA.

Useful ComfyUI launch flags to try if needed:

```bash
python main.py --force-fp16
```

If memory is constrained:

```bash
python main.py --lowvram
```

Start with SD1.5-class models before trying SDXL or FLUX.

For this project, SD Turbo / SD1.5 Turbo is probably a better first target than a much larger model.

---

## TouchDesigner integration option

The simplest TouchDesigner integration is filesystem-based.

ComfyUI writes images to an output directory.

TouchDesigner watches or periodically reloads the latest image.

Possible approaches:

- Folder DAT watching output directory
- Movie File In TOP pointed to latest symlink or stable filename
- Python script copies latest image to `output/current.png`
- TouchDesigner reloads `current.png`

Recommended controller behaviour:

```text
generated image path
  → copy to output/current.png
  → optionally also archive timestamped image
```

This avoids needing a complicated live texture bridge in the first version.

---

## Testing checklist

Create small scripts before building the full loop.

### `scripts/test_submit_prompt.py`

- Loads workflow JSON
- Sets prompt to `"a luminous abstract painting of a garden at night"`
- Submits to ComfyUI
- Waits for output
- Prints image path

### `scripts/test_ollama_prompt.py`

- Sends a sample spoken phrase to Ollama
- Confirms JSON response
- Validates required fields

### `scripts/test_microphone.py`

- Records a short phrase
- Runs transcription
- Prints text

### `scripts/test_feedback.py`

- Generates one txt2img image
- Uses it as input to img2img
- Confirms the second image is derived from the first

---

## Error handling requirements

The controller should handle:

- ComfyUI not running
- model missing
- invalid workflow JSON
- prompt submission failure
- WebSocket disconnect
- Ollama not running
- malformed Ollama JSON
- microphone unavailable
- speech-to-text returns empty phrase
- generated image path not found

Do not crash the whole performance loop on a single bad generation.

Log the error, skip or retry, and continue.

---

## Minimal success criterion

The first successful version should do this:

```text
User speaks a phrase.
System transcribes it locally.
Ollama converts it into a visual prompt.
Python submits the prompt to ComfyUI.
ComfyUI generates an image locally.
The image appears in an output folder and/or viewer.
The next spoken phrase modifies the previous image through img2img.
```

---

## Development priorities

1. Make one local ComfyUI prompt submission work.
2. Make one workflow template easy to mutate.
3. Make output image retrieval reliable.
4. Add prompt refinement.
5. Add speech input.
6. Add image feedback.
7. Add display / TouchDesigner output.
8. Optimise latency.

---

## Avoid overbuilding early

Do not start with:

- a complex GUI
- a database
- a plugin system
- multi-user networking
- cloud sync
- perfect streaming transcription
- FLUX dev or very large models
- elaborate installation packaging

The useful MVP is a robust local loop.

---

## Longer-term ideas

Once the MVP works, consider:

- style presets
- session memory
- multiple image streams
- semantic decay over time
- silence-driven mutation
- OSC control from TouchDesigner
- MIDI/knob control of denoise, CFG, seed, style, and prompt weight
- voice commands such as “reset”, “hold”, “mutate slowly”, “make it darker”
- saving the full transcript/prompt/image history as a performance archive
- live projection mode
- web UI for monitoring
- automatic performance logging
