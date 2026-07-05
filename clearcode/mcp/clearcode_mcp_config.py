import os
import re
import json
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent / "clearcode_mcp_servers.json"

def load_clearcode_mcp_configs() -> dict:
    """Return mcp_servers dict from clearcode_mcp_servers.json with env vars resolved.
    
     CWD is injected at load time so ${CWD} in the config always resolves to the
     directory where clearcode was launched — not the package install location.
    """
    os.environ.setdefault("CWD", str(Path.cwd()))
    raw = json.loads(_CONFIG_PATH.read_text())
    resolved = re.sub(r"\$\{(\w+)\}", lambda m: os.getenv(m.group(1), ""), json.dumps(raw))
    return json.loads(resolved).get("mcp_servers", {})
