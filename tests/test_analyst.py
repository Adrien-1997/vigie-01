from backend.agents import analyst


def _raw_item(raw_text: str, country: str = "US") -> dict:
    return {
        "source": "s",
        "lang": "en",
        "country": country,
        "state_affiliated": False,
        "title": "titre",
        "link": "l",
        "published": "",
        "raw_text": raw_text,
    }


class _FakeAnalysis:
    def __init__(
        self,
        category,
        citation,
        location="",
        location_country="",
        domestic=False,
        title_fr="Titre",
        summary="Résumé",
    ):
        self.category = category
        self.citation = citation
        self.location = location
        self.location_country = location_country
        self.domestic = domestic
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


def test_analyze_skips_an_unparsable_classification_without_losing_the_rest_of_the_run(monkeypatch):
    """Constaté en run réel : le modèle a renvoyé « diplomacia_defense » sur une source
    hispanophone. L'erreur de validation remontait jusqu'au graphe et faisait perdre tous les items
    déjà analysés — coût sans rapport avec celui d'un item raté."""
    from pydantic import ValidationError

    def _classify(item):
        if item["link"] == "bad":
            raise ValidationError.from_exception_data("_Analysis", [])
        return _FakeAnalysis("contrat_armement", "source text about a contract")

    monkeypatch.setattr(analyst, "classify_item", _classify)

    good, bad = _raw_item("Actual source text about a contract."), _raw_item("Autre texte")
    bad["link"] = "bad"

    result = analyst.analyze({"raw_items": [bad, good], "analyzed_items": []})

    assert [i["link"] for i in result["analyzed_items"]] == ["l"]


def test_analyze_blanks_unverified_location_instead_of_trusting_it(monkeypatch):
    monkeypatch.setattr(
        analyst,
        "classify_item",
        lambda item: _FakeAnalysis(
            "contrat_armement",
            "source text about a contract",
            location="Nowhereland",
            location_country="Nowhereland",
        ),
    )

    result = analyst.analyze({"raw_items": [_raw_item("Actual source text about a contract.")], "analyzed_items": []})

    assert result["analyzed_items"][0]["location"] == ""
    # Le pays déduit n'est pas vérifiable verbatim : son seul ancrage est le lieu dont il est
    # déduit. Lieu rejeté, pays rejeté — sinon un lieu non vérifié reviendrait placer l'item
    # sur la carte par un champ que le garde-fou ne couvre pas.
    assert result["analyzed_items"][0]["location_country"] == ""


def test_analyze_keeps_deduced_country_when_location_is_verified(monkeypatch):
    monkeypatch.setattr(
        analyst,
        "classify_item",
        lambda item: _FakeAnalysis(
            "contrat_armement",
            "source text about a contract",
            location="Darwin",
            location_country="Australia",
        ),
    )

    result = analyst.analyze(
        {"raw_items": [_raw_item("Source text about a contract signed in Darwin.")], "analyzed_items": []}
    )

    assert result["analyzed_items"][0]["location"] == "Darwin"
    assert result["analyzed_items"][0]["location_country"] == "Australia"


def test_analyze_presumes_domestic_only_when_no_location_was_extracted(monkeypatch):
    monkeypatch.setattr(
        analyst,
        "classify_item",
        lambda item: _FakeAnalysis("contrat_armement", "source text about a contract", domestic=True),
    )

    result = analyst.analyze({"raw_items": [_raw_item("Actual source text about a contract.")], "analyzed_items": []})

    assert result["analyzed_items"][0]["location"] == ""
    assert result["analyzed_items"][0]["domestic_to_source"] is True


def test_analyze_ignores_domestic_when_a_location_was_extracted(monkeypatch):
    # Un lieu extrait est une réponse : le pays du média ne doit pas s'y substituer, même si
    # l'événement est aussi domestique. Le repli est un dernier recours, pas un concurrent.
    monkeypatch.setattr(
        analyst,
        "classify_item",
        lambda item: _FakeAnalysis(
            "contrat_armement", "source text about a contract", location="Darwin", domestic=True
        ),
    )

    result = analyst.analyze(
        {"raw_items": [_raw_item("Source text about a contract signed in Darwin.")], "analyzed_items": []}
    )

    assert result["analyzed_items"][0]["domestic_to_source"] is False


def test_analyze_refuses_domestic_presumption_for_international_sources(monkeypatch):
    # "INT" désigne une source multi-pays ou institutionnelle UE : elle n'a pas de pays
    # d'origine, il n'y a donc rien à présumer.
    monkeypatch.setattr(
        analyst,
        "classify_item",
        lambda item: _FakeAnalysis("contrat_armement", "source text about a contract", domestic=True),
    )

    result = analyst.analyze(
        {"raw_items": [_raw_item("Actual source text about a contract.", country="INT")], "analyzed_items": []}
    )

    assert result["analyzed_items"][0]["domestic_to_source"] is False
