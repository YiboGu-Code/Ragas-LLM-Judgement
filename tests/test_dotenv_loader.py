import os


def test_dotenv_loader_sets_env_var_from_file(monkeypatch, tmp_path):
    monkeypatch.delenv("ARK_API_KEY", raising=False)
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("ARK_API_KEY=from_file\n", encoding="utf-8")

    from app.core.dotenv import load_dotenv

    load_dotenv(dotenv_path)
    assert os.environ.get("ARK_API_KEY") == "from_file"


def test_dotenv_loader_does_not_override_existing_env(monkeypatch, tmp_path):
    monkeypatch.setenv("ARK_API_KEY", "from_env")
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("ARK_API_KEY=from_file\n", encoding="utf-8")

    from app.core.dotenv import load_dotenv

    load_dotenv(dotenv_path)
    assert os.environ.get("ARK_API_KEY") == "from_env"
