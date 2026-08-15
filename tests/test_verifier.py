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


def test_verify_escalates_only_configured_categories(monkeypatch):
    _patch_llm(monkeypatch, conclusion=_FakeConclusion(0.8, True))

    items = [_analyzed_item("export_control", "a"), _analyzed_item("mouvement_militaire", "b")]
    result = verifier.verify({"raw_items": [], "analyzed_items": items})

    escalated = {i["link"]: i for i in result["analyzed_items"]}
    assert escalated["a"]["confidence_score"] == 0.8
    assert escalated["a"]["corroborated"] is True
    assert escalated["b"]["confidence_score"] is None
    assert escalated["b"]["corroborated"] is None


def test_verify_respects_max_escalations_per_run(monkeypatch):
    monkeypatch.setattr(verifier, "MAX_VERIFIER_ESCALATIONS_PER_RUN", 1)
    _patch_llm(monkeypatch, conclusion=_FakeConclusion(0.9, False))

    items = [_analyzed_item("export_control", "a"), _analyzed_item("export_control", "b")]
    result = verifier.verify({"raw_items": [], "analyzed_items": items})

    escalated = {i["link"]: i for i in result["analyzed_items"]}
    assert escalated["a"]["confidence_score"] == 0.9
    assert escalated["b"]["confidence_score"] is None


def test_verify_stops_tool_loop_at_max_steps(monkeypatch):
    monkeypatch.setattr(verifier, "MAX_VERIFIER_STEPS_PER_ITEM", 2)

    always_tool = [
        _FakeToolCallResponse([{"name": "search_related_items", "args": {"query": "x"}, "id": "c1"}]) for _ in range(10)
    ]
    counter = [0]
    _patch_llm(monkeypatch, tool_responses=always_tool, conclusion=_FakeConclusion(), invoke_counter=counter)

    verifier.verify({"raw_items": [], "analyzed_items": [_analyzed_item("export_control", "a")]})

    assert counter[0] == 2  # plafonné, jamais le nombre de réponses factices disponibles (10)


def test_verify_never_touches_summary_or_citation(monkeypatch):
    _patch_llm(monkeypatch, conclusion=_FakeConclusion(0.5, False))

    item = _analyzed_item("contrat_armement", "a")
    result = verifier.verify({"raw_items": [], "analyzed_items": [item]})

    assert result["analyzed_items"][0]["summary"] == "résumé original"
    assert result["analyzed_items"][0]["citation"] == "citation originale"


def test_verify_records_the_scored_items_not_their_pre_verification_version(monkeypatch):
    """L'historique alimente aussi le digest servi par l'API : il doit porter l'item tel qu'il sera
    affiché. Enregistré avant l'escalade, il aurait figé confidence_score/corroborated à None."""
    import backend.memory.store as store

    _patch_llm(monkeypatch, conclusion=_FakeConclusion(0.5, True))

    verifier.verify({"raw_items": [], "analyzed_items": [_analyzed_item("contrat_armement", "a")]})

    recorded = store.load_digest(1)
    assert [r["link"] for r in recorded] == ["a"]
    assert recorded[0]["confidence_score"] == 0.5
    assert recorded[0]["corroborated"] is True


def test_verify_never_lets_two_items_of_the_same_run_corroborate_each_other(monkeypatch):
    """Le nœud écrivait l'historique avant d'escalader, en n'excluant ensuite que le lien de l'item
    courant : un item pouvait donc être « corroboré » par son voisin de lot, qui n'apporte aucune
    confirmation indépendante dans le temps."""
    seen_queries = []

    tool_call = _FakeToolCallResponse([{"name": "search_related_items", "args": {"query": "Rafale"}, "id": "c1"}])
    _patch_llm(monkeypatch, tool_responses=[tool_call], conclusion=_FakeConclusion(0.5, False))

    items = [_analyzed_item("export_control", "a"), _analyzed_item("export_control", "b")]
    items[0]["summary"] = items[1]["summary"] = "Rafale vendu à la Grèce par Dassault"

    original = verifier.search_related

    def _spy(query, exclude_links, limit=5):
        seen_queries.append(set(exclude_links))
        return original(query, exclude_links=exclude_links, limit=limit)

    monkeypatch.setattr(verifier, "search_related", _spy)
    verifier.verify({"raw_items": [], "analyzed_items": items})

    assert seen_queries, "l'outil de recherche n'a pas été appelé"
    assert all(excluded == {"a", "b"} for excluded in seen_queries)
