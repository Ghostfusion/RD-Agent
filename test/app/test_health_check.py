"""Regression tests for `rdagent.app.utils.health_check.env_check`.

Both tests are offline: the network-touching `test_chat`/`test_embedding` helpers
are patched, and the environment is constructed explicitly by the fixture so the
tests never depend on ambient credentials.
"""

from unittest import mock

import pytest
from rdagent.app.utils import health_check

# Every variable `env_check` inspects. Cleared per test so the branch taken is
# determined only by what the test sets.
_CREDENTIAL_VARS = (
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_API_BASE",
    "OPENAI_API_KEY",
    "OPENAI_API_BASE",
    "OPENROUTER_API_KEY",
    "LITELLM_PROXY_API_KEY",
    "LITELLM_PROXY_API_BASE",
    "CHAT_MODEL",
    "EMBEDDING_MODEL",
)


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for name in _CREDENTIAL_VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


@pytest.mark.offline
@pytest.mark.usefixtures("clean_env")
def test_env_check_without_credentials_reports_and_returns() -> None:
    """An unrecognised configuration must report an error, not raise UnboundLocalError."""
    with (
        mock.patch.object(health_check, "test_chat") as patched_chat,
        mock.patch.object(health_check, "test_embedding") as patched_embedding,
    ):
        health_check.env_check()  # must not raise

    patched_chat.assert_not_called()
    patched_embedding.assert_not_called()


@pytest.mark.offline
def test_env_check_routes_openrouter_key_to_chat_and_embedding(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    clean_env.setenv("CHAT_MODEL", "openrouter/deepseek/deepseek-v4.1-flash")
    clean_env.setenv("EMBEDDING_MODEL", "openrouter/openai/text-embedding-3-small")

    with (
        mock.patch.object(health_check, "test_chat", return_value=True) as patched_chat,
        mock.patch.object(health_check, "test_embedding", return_value=True) as patched_embedding,
    ):
        health_check.env_check()

    # OpenRouter serves embeddings too, so the one key must reach both calls.
    assert patched_chat.call_args.kwargs["chat_api_key"] == "test-openrouter-key"
    assert patched_chat.call_args.kwargs["chat_model"] == "openrouter/deepseek/deepseek-v4.1-flash"
    assert patched_embedding.call_args.kwargs["embedding_api_key"] == "test-openrouter-key"
    assert patched_embedding.call_args.kwargs["embedding_model"] == "openrouter/openai/text-embedding-3-small"
