"""Fast tests that need neither Ollama nor an embedding model."""
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent import MyMindAgent  # noqa: E402


@pytest.mark.parametrize("msg,expected", [
    ("幫我把這篇加進知識庫", ("ingest", "general")),
    ("please save this note", ("ingest", "general")),
    ("幫我規劃 TOEIC 讀書計畫", ("plan", "study")),
    ("Make a plan for my defense", ("plan", "study")),
    ("Fuzzy Extractor 的參數是什麼", None),
])
def test_keyword_shortcuts(msg, expected):
    assert MyMindAgent._keyword_classify(MyMindAgent, msg) == expected


@pytest.fixture
def chat_request(monkeypatch):
    """Import main.ChatRequest with the heavy agent stubbed out."""
    import agent

    class StubAgent:
        calendar = None

    monkeypatch.setattr(agent, "MyMindAgent", StubAgent)
    sys.modules.pop("main", None)
    import main
    yield main.ChatRequest
    sys.modules.pop("main", None)


def test_ingest_source_accepts_urls(chat_request):
    assert chat_request(message="x", ingest_source="https://example.com/a").ingest_source


@pytest.mark.parametrize("bad", ["/etc/passwd", "../.env", "file:///etc/hosts"])
def test_ingest_source_rejects_local_paths(chat_request, bad):
    with pytest.raises(ValueError):
        chat_request(message="x", ingest_source=bad)
