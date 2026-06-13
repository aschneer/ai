"""Write Gantt data JSON and deploy static viewer assets."""

from __future__ import annotations

import http.server
import json
import os
import socket
import sys
from dataclasses import dataclass
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any

GANTT_DATA_FILENAME = "gantt_data.json"
GANTT_HTML_FILENAME = "gantt.html"
GANTT_JS_FILENAME = "gantt.js"
ASSET_NAMES = (GANTT_HTML_FILENAME, GANTT_JS_FILENAME)


@dataclass(frozen=True)
class ViewerUrls:
    """Local and optional network URLs for the Gantt viewer."""

    local: str
    network: str | None = None


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


def resolve_bind_host(host: str) -> str:
    """Map CLI host mode to a bind address."""
    if host == "auto":
        return "0.0.0.0"
    return host


def is_ssh_session() -> bool:
    """True when running under SSH (remote shell)."""
    return bool(os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_CLIENT"))


def guess_lan_address() -> str | None:
    """Best-effort LAN IP for a network URL (same idea as Vite's Network line)."""
    override = os.environ.get("SCHEDULE_VIEWER_HOST")
    if override:
        return override
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            address = sock.getsockname()[0]
    except OSError:
        return None
    if address and not address.startswith("127."):
        return address
    return None


def build_viewer_urls(port: int, page: str = GANTT_HTML_FILENAME) -> ViewerUrls:
    """Build local and optional network viewer URLs."""
    local = f"http://127.0.0.1:{port}/{page}"
    lan = guess_lan_address()
    network = f"http://{lan}:{port}/{page}" if lan else None
    return ViewerUrls(local=local, network=network)


def print_viewer_links(urls: ViewerUrls) -> None:
    """Print clickable Gantt URLs to stderr."""
    _print_link("Gantt chart (local)", urls.local)
    if urls.network and urls.network != urls.local:
        _print_link("Gantt chart (network)", urls.network)
    if is_ssh_session():
        print(
            "Remote session: use the local URL in your laptop browser "
            "(Cursor/VS Code forward the port automatically, or use ssh -L).",
            file=sys.stderr,
        )


def serve_project_directory(
    directory: Path,
    *,
    port: int = 8000,
    host: str = "auto",
    page: str = GANTT_HTML_FILENAME,
) -> None:
    """Serve the project directory until interrupted."""
    directory = directory.resolve()
    bind_host = resolve_bind_host(host)
    urls = build_viewer_urls(port, page)

    print_viewer_links(urls)

    print(f"Serving {directory} on {bind_host}:{port} (Ctrl+C to stop)", file=sys.stderr)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(directory), **kwargs)

    http.server.ThreadingHTTPServer((bind_host, port), Handler).serve_forever()


def _print_link(label: str, url: str) -> None:
    """Print anOSC 8 hyperlink when supported, else plain text."""
    print(f"{label}: \033]8;;{url}\033\\{url}\033]8;;\033\\", file=sys.stderr)


def _read_asset(name: str) -> str:
    asset = files("schedule.assets") / name
    with as_file(asset) as path:
        return path.read_text(encoding="utf-8")
