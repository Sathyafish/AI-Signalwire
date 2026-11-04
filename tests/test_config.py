from src.config import load_settings, load_sources


def test_azure_chosen_when_azure_vars_set():
    s = load_settings({"AZURE_OPENAI_ENDPOINT": "https://x", "AZURE_OPENAI_API_KEY": "k", "OPENAI_API_KEY": "o"})
    assert s.provider == "azure"


def test_openai_chosen_otherwise():
    assert load_settings({"OPENAI_API_KEY": "o"}).provider == "openai"


def test_evaluator_model_defaults_to_agent_model():
    s = load_settings({"AGENT_MODEL": "gpt-4o-mini"})
    assert s.agent_model == "gpt-4o-mini" and s.evaluator_model == "gpt-4o-mini"
    assert load_settings({"AGENT_MODEL": "a", "EVALUATOR_MODEL": "b"}).evaluator_model == "b"


def test_items_per_source_default_is_3():
    assert load_settings({}).items_per_source == 3
    assert load_settings({"ITEMS_PER_SOURCE": "5"}).items_per_source == 5


def test_flags_and_db_path():
    s = load_settings({"DEMO_MODE": "1", "FAKE_LLM": "1", "DB_PATH": "x.db"})
    assert s.demo_mode and s.fake_llm and s.db_path == "x.db"
    d = load_settings({})
    assert not d.demo_mode and not d.fake_llm and d.db_path == "data/signalwire.db"


def test_load_sources_skips_disabled(tmp_path):
    p = tmp_path / "s.yaml"
    p.write_text(
        "sources:\n"
        "  - {name: A, type: lab_post, url: 'https://a', adapter: feed}\n"
        "  - {name: B, type: release, url: 'https://b', enabled: false}\n"
    )
    srcs = load_sources(str(p))
    assert [s.name for s in srcs] == ["A"]


def test_default_sources_file_loads():
    names = [s.name for s in load_sources("config/sources.yaml")]
    assert "OpenAI" in names and "LangGraph" in names and "Anthropic" in names
