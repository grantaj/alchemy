from pathlib import Path
from shutil import copy2


def copy_current_image(source: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    copy2(source, destination)
    return destination
