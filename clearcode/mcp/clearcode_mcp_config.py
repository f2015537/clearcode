import os
import re
import json
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent / "clearcode_mcp_servers.json"

def load_clearcode_mcp_configs() -> dict:
    """Return mcp_servers dict from clearcode_mcp_servers.json with env vars resolved."""
    raw = json.loads(_CONFIG_PATH.read_text())
    # Replace ${VAR} placeholders in the config with actual env var values
    resolved = re.sub(
        r"\$\{(\w+)\}", lambda m: os.getenv(m.group(1), ""), json.dumps(raw)
    )
    return json.loads(resolved).get("mcp_servers", {})
