from backend import graph as graph_module


def test_build_graph_compiles_without_error():
    assert graph_module.build_graph() is not None


def test_run_pipeline_passes_max_steps_per_run_as_recursion_limit(monkeypatch):
    captured = {}

    class _FakeGraph:
        def invoke(self, state, config=None):
            captured["config"] = config
            return {"raw_items": [], "analyzed_items": []}

    monkeypatch.setattr(graph_module, "build_graph", lambda: _FakeGraph())
    monkeypatch.setattr(graph_module, "MAX_STEPS_PER_RUN", 7)

    graph_module.run_pipeline()

    assert captured["config"] == {"recursion_limit": 7}
