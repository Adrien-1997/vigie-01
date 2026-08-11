from fastapi.testclient import TestClient

from backend.api import main as api_main
from backend.guardrails import BudgetExceeded


def _client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setattr(api_main, "_DIGEST_FILE", tmp_path / "digest.json")
    return TestClient(api_main.app)


def test_health():
    assert TestClient(api_main.app).get("/health").json() == {"status": "ok"}


def test_events_404_when_no_digest_generated_yet(tmp_path, monkeypatch):
    res = _client(tmp_path, monkeypatch).get("/events")
    assert res.status_code == 404


def test_run_then_events_roundtrip(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    fake_item = {
        "source": "s",
        "lang": "fr",
        "title": "t",
        "title_fr": "t",
        "link": "l",
        "published": "",
        "category": "contrat_armement",
        "summary": "r",
        "citation": "c",
        "location": "",
        "confidence_score": None,
        "corroborated": None,
    }
    monkeypatch.setattr(api_main, "run_pipeline", lambda: {"analyzed_items": [fake_item]})

    run_res = client.post("/run")
    assert run_res.status_code == 200
    assert run_res.json()["item_count"] == 1

    events_res = client.get("/events")
    assert events_res.status_code == 200
    assert events_res.json()["items"] == [fake_item]


def test_run_maps_budget_exceeded_to_429_not_500(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    def _raise():
        raise BudgetExceeded("plafond atteint")

    monkeypatch.setattr(api_main, "run_pipeline", _raise)

    res = client.post("/run")

    assert res.status_code == 429
