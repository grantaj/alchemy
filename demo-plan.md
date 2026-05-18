# Spoken Word Visualiser Demo Plan

## Goal

Create a quick, reliable demo of a local spoken-word-to-image system for a visiting curator.

The demo should show spoken language becoming a responsive visual world:

```text
microphone or audio file
  -> speech-to-text
  -> Ollama prompt refinement
  -> ComfyUI workflow API
  -> generated image
  -> output/current.png
  -> viewer or TouchDesigner
```

The goal is not a polished application. The goal is a working creative/performance system that feels alive, local, and extensible.

## Core Decision

Do not rehabilitate the old scripts directly.

Use the old repo as reference material, but build a new thin controller around ComfyUI.

Useful old files:

- `speech2img.py`: old queue-based pipeline shape.
- `reprompt.py`: Ollama prompt-shaping experiments.
- `sd-top.py`: TouchDesigner integration direction.
- `transcribe-streaming.py`: local microphone transcription experiment.

New work should live in a cleaner structure:

```text
src/
workflows/
scripts/
output/
```

## Target Architecture

```text
controller app
  owns:
    audio capture
    phrase segmentation
    transcription
    prompt refinement
    workflow mutation
    ComfyUI job submission
    output file handling
    state across generations

ComfyUI
  owns:
    model loading
    sampler workflow
    txt2img
    img2img feedback
    image generation
```

ComfyUI should be treated as a local rendering service, not as the whole application.

## MVP Behaviour

Minimum viable demo:

```text
audio file or microphone phrase
  -> transcription printed to console
  -> rewritten visual prompt printed to console
  -> ComfyUI image generated
  -> output/current.png updated
  -> TouchDesigner or simple viewer displays it
```

Best version for the curator:

```text
each new spoken phrase transforms the previous image instead of replacing it
```

That means adding an img2img feedback workflow once txt2img is stable.

## Milestones

### 1. ComfyUI Running Locally

Confirm ComfyUI runs at:

```text
http://127.0.0.1:8188
```

Use a fast SD1.5 Turbo / SD Turbo-style checkpoint if available.

The checkpoint should appear in a ComfyUI checkpoint loader node.

Start with:

```text
resolution: 512x512
steps: 1-4
CFG: 1-2
```

Prioritise speed and continuity over image quality.

### 2. Manual txt2img Workflow

Create and test a simple workflow manually in ComfyUI:

```text
Checkpoint Loader
  -> CLIP Text Encode positive
  -> CLIP Text Encode negative
  -> Empty Latent Image
  -> KSampler
  -> VAE Decode
  -> Save Image
```

Export it as:

```text
workflows/sd15_turbo_txt2img.json
```

### 3. Minimal ComfyUI Submitter

Create a script that can:

- load the workflow JSON
- replace the positive prompt
- optionally replace the negative prompt
- set or randomise the seed
- submit to ComfyUI `/prompt`
- wait for the job to finish
- locate the generated image
- copy the latest output to `output/current.png`

This is the first major proof point.

Once `output/current.png` updates reliably, TouchDesigner integration can be very simple.

### 4. Ollama Prompt Refinement

Add a small prompt agent that turns spoken fragments into compact image instructions.

Input:

```text
spoken phrase
previous visual summary
previous prompt
pinned session style
```

Output:

```json
{
  "positive_prompt": "...",
  "negative_prompt": "...",
  "state_summary": "...",
  "denoise_strength": 0.45,
  "reset": false
}
```

The LLM should return JSON only. No essays, no commentary.

Recommended behaviour:

```text
Preserve continuity with the previous image.
Prefer vivid concrete visual language.
Transform the speech rather than illustrating it literally.
Keep prompts compact.
```

For the demo, pin the overall visual style manually so the system has a coherent artistic identity.

### 5. Speech Input

Support two modes:

```text
file mode:
  transcribe a known audio file, then generate images

mic mode:
  record a phrase, transcribe it, then generate an image
```

File mode is the demo safety net.

Mic mode is the live-performance layer.

Do not aim for true word-by-word streaming in the first demo. Phrase-based transcription is enough and much more reliable.

### 6. img2img Feedback

Add a second ComfyUI workflow:

```text
previous generated image
  -> VAE Encode
  -> KSampler with denoise below 1.0
  -> VAE Decode
  -> Save Image
```

Export it as:

```text
workflows/sd15_turbo_img2img.json
```

Controller behaviour:

```text
if there is no previous image or reset is true:
  use txt2img
else:
  use img2img with previous output
```

Useful denoise values:

```text
0.25 = subtle drift
0.45 = responsive transformation
0.70 = major scene shift
1.00 = full reset
```

This is the main creative upgrade. It should make the system feel cumulative rather than like disconnected images.

## Two-Day Schedule

### Day 1: Prove The Pipeline

- Run ComfyUI locally.
- Load SD Turbo / SD1.5 Turbo checkpoint.
- Create and export txt2img workflow.
- Write/test prompt submitter.
- Confirm images land in `output/current.png`.
- Confirm TouchDesigner or a simple viewer can display the latest image.

### Day 2: Make It Feel Like The Artwork

- Add Ollama prompt refinement.
- Add file transcription.
- Add microphone mode if stable.
- Add img2img feedback if the workflow is ready.
- Tune one strong visual style.
- Prepare a fallback demo using a known audio file such as `poem.m4a`.

## Demo Safety Strategy

The reliable fallback path should be:

```text
known audio file
  -> transcription
  -> prompt refinement
  -> txt2img or img2img
  -> output/current.png
```

Live microphone input can be used if stable, but the demo should not depend on it.

## Open Decisions

- Confirm the first model target: SD Turbo / SD1.5 Turbo.
- Decide whether the main display target is TouchDesigner or a simple fullscreen viewer.
- Decide whether the curator demo should prioritise live mic, pre-recorded audio, or both.
- Choose the pinned visual style for the session.

## Recommended First Build

Build this first:

```text
manual prompt
  -> ComfyUI
  -> output/current.png
```

Then add:

```text
Ollama prompt refinement
```

Then add:

```text
audio transcription
```

Then add:

```text
img2img feedback
```

This order keeps the risky pieces isolated and gives us something demonstrable early.
