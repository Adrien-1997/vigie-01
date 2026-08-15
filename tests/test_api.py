from fastapi.testclient import TestClient

from backend.api import main as api_main
from backend.guardrails import BudgetExceeded

FAKE_ITEM = {
    "source": "s",
    "lang": "fr",
    "country": "FR",
    "state_affiliated": False,
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


def _client() -> TestClient:
    return TestClient(api_main.app)


def test_health():
    assert _client().get("/health").json() == {"status": "ok"}


def test_events_404_when_the_pipeline_has_never_run():
    assert _client().get("/events").status_code == 404


def test_run_then_events_roundtrip(monkeypatch):
    from backend.memory import store

    def _fake_pipeline() -> dict:
        # Le vrai pipeline écrit l'historique dans son nœud verify ; /events le relit depuis là.
        store.record_analyzed([FAKE_ITEM])
        return {"analyzed_items": [FAKE_ITEM]}

    monkeypatch.setattr(api_main, "run_pipeline", _fake_pipeline)

    run_res = _client().post("/run")
    assert run_res.status_code == 200
    assert run_res.json()["item_count"] == 1

    events_res = _client().get("/events")
    assert events_res.status_code == 200
    assert [i["link"] for i in events_res.json()["items"]] == ["l"]


def test_events_keeps_previous_items_when_a_later_run_brings_nothing_new(monkeypatch):
    """Le défaut d'origine : un run sans item neuf (tout dédoublonné) écrasait le digest précédent.
    Le digest étant désormais une fenêtre sur l'historique, il doit survivre à un run vide."""
    from backend.memory import store

    store.record_analyzed([FAKE_ITEM])
    monkeypatch.setattr(api_main, "run_pipeline", lambda: {"analyzed_items": []})

    client = _client()
    assert client.post("/run").json()["item_count"] == 0
    assert [i["link"] for i in client.get("/events").json()["items"]] == ["l"]


def test_events_window_is_bounded_by_history_retention():
    from backend.memory.store import RELATED_ITEMS_WINDOW_DAYS

    client = _client()
    assert client.get(f"/events?days={RELATED_ITEMS_WINDOW_DAYS + 1}").status_code == 422
    assert client.get("/events?days=0").status_code == 422


def test_events_reports_the_window_it_served():
    from backend.memory import store

    store.record_analyzed([FAKE_ITEM])

    body = _client().get("/events?days=3").json()

    assert body["window_days"] == 3
    assert body["generated_at"] is not None


def test_events_returns_an_empty_window_rather_than_404_when_history_exists():
    """404 veut dire « le pipeline n'a jamais tourné ». Une fenêtre trop étroite sur un historique
    non vide reste un digest navigable, sinon le sélecteur de période disparaîtrait de l'écran."""
    from datetime import date, timedelta

    from backend.memory.persistence import get_persistence

    old = (date.today() - timedelta(days=20)).isoformat()
    get_persistence().put_analyzed([{**FAKE_ITEM, "date": old, "first_seen": old}])

    res = _client().get("/events?days=2")

    assert res.status_code == 200
    assert res.json()["items"] == []


def test_run_maps_budget_exceeded_to_429_not_500(monkeypatch):
    def _raise():
        raise BudgetExceeded("plafond atteint")

    monkeypatch.setattr(api_main, "run_pipeline", _raise)

    assert _client().post("/run").status_code == 429
