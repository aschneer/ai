import os
from unittest.mock import patch

from schedule.gantt_lib import (
    build_viewer_urls,
    is_ssh_session,
    resolve_bind_host,
)


def test_resolve_bind_host_auto() -> None:
    assert resolve_bind_host("auto") == "0.0.0.0"
    assert resolve_bind_host("127.0.0.1") == "127.0.0.1"


def test_build_viewer_urls_local() -> None:
    urls = build_viewer_urls(8000)
    assert urls.local == "http://127.0.0.1:8000/gantt.html"


def test_build_viewer_urls_network_override() -> None:
    with patch.dict(os.environ, {"SCHEDULE_VIEWER_HOST": "mybox.tailnet.ts.net"}):
        urls = build_viewer_urls(9000)
    assert urls.network == "http://mybox.tailnet.ts.net:9000/gantt.html"


def test_is_ssh_session_detects_connection_env() -> None:
    with patch.dict(os.environ, {"SSH_CONNECTION": "1.2.3.4 5678 1.2.3.5 22"}):
        assert is_ssh_session() is True
