import json
from pathlib import Path

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
_MANIFEST_PATH = _STATIC_DIR / "dist" / ".vite" / "manifest.json"
_manifest = json.loads(_MANIFEST_PATH.read_text()) if _MANIFEST_PATH.exists() else {}


def vite_asset(entry: str) -> dict:
    info = _manifest.get(entry, {})
    return {
        "js": "/static/dist/" + info["file"] if "file" in info else "",
        "css": "/static/dist/" + info["css"][0] if info.get("css") else "",
    }
