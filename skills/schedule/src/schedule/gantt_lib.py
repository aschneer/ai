"""Write Gantt data JSON and deploy static viewer assets."""

from __future__ import annotations

import http.server
import json
import sys
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any

GANTT_DATA_FILENAME = "gantt_data.json"
GANTT_HTML_FILENAME = "gantt.html"
GANTT_JS_FILENAME = "gantt.js"
ASSET_NAMES = (GANTT_HTML_FILENAME, GANTT_JS_FILENAME)


def schedule_payload(result_dict: dict[str, Any], *, title: str) -> dict[str, Any]:
    """Wrap computed schedule JSON with a display title for the Gantt viewer."""
    return {"title": title, **result_dict}


def write_gantt_data(path: Path, payload: dict[str, Any]) -> None:
    """Write schedule JSON for the Gantt viewer."""
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def deploy_gantt_assets(output_dir: Path) -> list[Path]:
    """Copy gantt.html and gantt.js into the project directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name in ASSET_NAMES:
        destination = output_dir / name
        destination.write_text(_read_asset(name), encoding="utf-8")
        written.append(destination)
    return written


def serve_project_directory(
    directory: Path,
    *,
    port: int = 8000,
    host: str = "127.0.0.1",
    page: str = GANTT_HTML_FILENAME,
) -> None:
    """Serve the project directory until interrupted."""
    directory = directory.resolve()

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(directory), **kwargs)

    url = f"http://{host}:{port}/{page}"
    print(f"Serving {directory} at {url} (Ctrl+C to stop)", file=sys.stderr)
    http.server.ThreadingHTTPServer((host, port), Handler).serve_forever()


def _read_asset(name: str) -> str:
    asset = files("schedule.assets") / name
    with as_file(asset) as path:
        return path.read_text(encoding="utf-8")
