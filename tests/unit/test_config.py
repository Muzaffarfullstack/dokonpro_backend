from app.core.config import Settings


def test_settings_parses_cors_origins() -> None:
    settings = Settings(
        secret_key="x" * 32,
        backend_cors_origins="http://localhost:3000, http://localhost:5173",
    )

    assert settings.cors_origins == ["http://localhost:3000", "http://localhost:5173"]
    assert settings.is_production is False


def test_settings_detects_production() -> None:
    settings = Settings(secret_key="x" * 32, environment="production", debug=False)

    assert settings.is_production is True
    assert settings.debug is False


def test_settings_normalizes_api_prefix() -> None:
    settings = Settings(secret_key="x" * 32, api_v1_prefix="api/v1")

    assert settings.api_v1_prefix == "/api/v1"


def test_settings_normalizes_git_bash_path_converted_api_prefix() -> None:
    settings = Settings(
        secret_key="x" * 32,
        api_v1_prefix="/C:/Program Files/Git/api/v1",
    )

    assert settings.api_v1_prefix == "/api/v1"
