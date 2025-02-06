import whisper
import torch
import warnings

warnings.filterwarnings("ignore", message="FP16 is not supported on CPU")

device = "cpu"#"mps" if torch.backends.mps.is_available() else "cpu"
model = whisper.load_model("small", device=device)  # or "tiny", "small", "medium", "large"

result = model.transcribe("example.m4a", language="en")  # Just pass the .m4a file
print(result["text"])


