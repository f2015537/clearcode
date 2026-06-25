import yaml
from pathlib import Path


def load_config() -> dict:
    path = Path(__file__).parent / "config.yaml"
    if not path.exists():
        raise FileNotFoundError(f"config.yaml not found at {path}")
    return yaml.safe_load(path.read_text())


config = load_config()
