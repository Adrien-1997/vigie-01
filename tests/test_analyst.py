from backend.agents import analyst


def _raw_item(raw_text: str) -> dict:
    return {
        "source": "s",
        "lang": "en",
        "title": "titre",
        "link": "l",
        "published": "",
        "raw_text": raw_text,
    }


class _FakeAnalysis:
    def __init__(self, category, citation, location="", title_fr="Titre", summary="Résumé"):
        self.category = category
        self.citation = citation
        self.location = location
        self.title_fr = title_fr
        self.summary = summary


def test_clean_text_strips_html_and_unescapes_entities():
    assert analyst._clean_text("<p>Rafale &amp; export</p>") == "Rafale & export"


def test_extract_verified_true_for_verbatim_substring():
    assert analyst._extract_verified("Rafale export deal", "The Rafale export deal was signed today.")


def test_extract_verified_false_when_not_in_source():
    assert not analyst._extract_verified("Rafale export deal", "No mention of that aircraft here.")


def test_extract_verified_false_for_empty_extract():
    assert not analyst._extract_verified("", "Some source text.")


def test_analyze_drops_hors_perimetre(monkeypatch):
    monkeypatch.setattr(analyst, "classify_item", lambda item: _FakeAnalysis("hors_perimetre", ""))

    result = analyst.analyze({"raw_items": [_raw_item("some text")], "analyzed_items": []})

    assert result["analyzed_items"] == []


def test_analyze_rejects_items_without_verified_citation(monkeypatch):
    monkeypatch.setattr(
        analyst,
        "classify_item",
        lambda item: _FakeAnalysis("contrat_armement", "this citation is not in the source"),
    )

    result = analyst.analyze({"raw_items": [_raw_item("Actual source text.")], "analyzed_items": []})

    assert result["analyzed_items"] == []


def test_analyze_keeps_items_with_verified_citation(monkeypatch):
    monkeypatch.setattr(
        analyst,
        "classify_item",
        lambda item: _FakeAnalysis("contrat_armement", "source text about a contract"),
    )

    result = analyst.analyze({"raw_items": [_raw_item("Actual source text about a contract.")], "analyzed_items": []})

    assert len(result["analyzed_items"]) == 1
    assert result["analyzed_items"][0]["category"] == "contrat_armement"


def test_analyze_blanks_unverified_location_instead_of_trusting_it(monkeypatch):
    monkeypatch.setattr(
        analyst,
        "classify_item",
        lambda item: _FakeAnalysis("contrat_armement", "source text about a contract", location="Nowhereland"),
    )

    result = analyst.analyze({"raw_items": [_raw_item("Actual source text about a contract.")], "analyzed_items": []})

    assert result["analyzed_items"][0]["location"] == ""
