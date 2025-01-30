import whisper
import torch

model = whisper.load_model("base")  # or "tiny", "small", "medium", "large"

result = model.transcribe("example.m4a")  # Just pass the .m4a file
print(result["text"])
