from backend.agents import verifier


def _analyzed_item(category: str, link: str = "l") -> dict:
    return {
        "source": "s",
        "lang": "en",
        "country": "US",
        "state_affiliated": False,
        "title": "titre",
        "title_fr": "titre fr",
        "link": link,
        "published": "",
        "category": category,
        "summary": "résumé original",
        "citation": "citation originale",
        "location": "",
        "confidence_score": None,
        "corroborated": None,
    }


class _FakeToolCallResponse:
    def __init__(self, tool_calls):
        self.tool_calls = tool_calls


class _FakeNoToolResponse:
    tool_calls = []


class _FakeConclusion:
    def __init__(self, confidence_score=0.7, corroborated=False):
        self.confidence_score = confidence_score
        self.corroborated = corroborated


def _fake_chat_anthropic(tool_responses, conclusion, invoke_counter=None):
    """Fabrique un ChatAnthropic factice : .bind_tools() rejoue tool_responses puis répond sans
    outil, .with_structured_output() retourne toujours `conclusion`."""

    class _LoopLLM:
        def __init__(self):
            self._remaining = list(tool_responses)

        def invoke(self, messages):
            if invoke_counter is not None:
                invoke_counter[0] += 1
            if self._remaining:
                return self._remaining.pop(0)
            return _FakeNoToolResponse()

    class _Concluder:
        def invoke(self, messages):
            return conclusion

    class _FakeChatAnthropic:
        def __init__(self, model, temperature):
            pass

        def bind_tools(self, tools):
            return _LoopLLM()

        def with_structured_output(self, schema):
            return _Concluder()

    return _FakeChatAnthropic


def _patch_llm(monkeypatch, tool_responses=(), conclusion=None, invoke_counter=None):
    monkeypatch.setattr(verifier, "check_and_increment_llm_call", lambda: None)
    monkeypatch.setattr(
        verifier,
        "ChatAnthropic",
        _fake_chat_anthropic(tool_responses, conclusion or _FakeConclusion(), invoke_counter),
    )


def test_verify_escalates_only_configured_categories(tmp_path, monkeypatch):
    import backend.memory.store as store

    monkeypatch.setattr(store, "_ANALYZED_STORE_FILE", tmp_path / "history.json")
    _patch_llm(monkeypatch, conclusion=_FakeConclusion(0.8, True))

    items = [_analyzed_item("export_control", "a"), _analyzed_item("mouvement_militaire", "b")]
    result = verifier.verify({"raw_items": [], "analyzed_items": items})

    escalated = {i["link"]: i for i in result["analyzed_items"]}
    assert escalated["a"]["confidence_score"] == 0.8
    assert escalated["a"]["corroborated"] is True
    assert escalated["b"]["confidence_score"] is None
    assert escalated["b"]["corroborated"] is None


def test_verify_respects_max_escalations_per_run(tmp_path, monkeypatch):
    import backend.memory.store as store

    monkeypatch.setattr(store, "_ANALYZED_STORE_FILE", tmp_path / "history.json")
    monkeypatch.setattr(verifier, "MAX_VERIFIER_ESCALATIONS_PER_RUN", 1)
    _patch_llm(monkeypatch, conclusion=_FakeConclusion(0.9, False))

    items = [_analyzed_item("export_control", "a"), _analyzed_item("export_control", "b")]
    result = verifier.verify({"raw_items": [], "analyzed_items": items})

    escalated = {i["link"]: i for i in result["analyzed_items"]}
    assert escalated["a"]["confidence_score"] == 0.9
    assert escalated["b"]["confidence_score"] is None


def test_verify_stops_tool_loop_at_max_steps(tmp_path, monkeypatch):
    import backend.memory.store as store

    monkeypatch.setattr(store, "_ANALYZED_STORE_FILE", tmp_path / "history.json")
    monkeypatch.setattr(verifier, "MAX_VERIFIER_STEPS_PER_ITEM", 2)

    always_tool = [
        _FakeToolCallResponse([{"name": "search_related_items", "args": {"query": "x"}, "id": "c1"}]) for _ in range(10)
    ]
    counter = [0]
    _patch_llm(monkeypatch, tool_responses=always_tool, conclusion=_FakeConclusion(), invoke_counter=counter)

    verifier.verify({"raw_items": [], "analyzed_items": [_analyzed_item("export_control", "a")]})

    assert counter[0] == 2  # plafonné, jamais le nombre de réponses factices disponibles (10)


def test_verify_never_touches_summary_or_citation(tmp_path, monkeypatch):
    import backend.memory.store as store

    monkeypatch.setattr(store, "_ANALYZED_STORE_FILE", tmp_path / "history.json")
    _patch_llm(monkeypatch, conclusion=_FakeConclusion(0.5, False))

    item = _analyzed_item("contrat_armement", "a")
    result = verifier.verify({"raw_items": [], "analyzed_items": [item]})

    assert result["analyzed_items"][0]["summary"] == "résumé original"
    assert result["analyzed_items"][0]["citation"] == "citation originale"


def test_verify_records_history_before_escalating(tmp_path, monkeypatch):
    import backend.memory.store as store

    history_file = tmp_path / "history.json"
    monkeypatch.setattr(store, "_ANALYZED_STORE_FILE", history_file)
    _patch_llm(monkeypatch, conclusion=_FakeConclusion(0.5, False))

    verifier.verify({"raw_items": [], "analyzed_items": [_analyzed_item("contrat_armement", "a")]})

    assert history_file.exists()
