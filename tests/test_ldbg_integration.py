"""
Integration tests that make real API calls using OpenRouter.

These tests verify that all default models from PROVIDERS can be accessed through OpenRouter,
without requiring accounts on each individual provider.

Set OPENROUTER_API_KEY environment variable to run these tests.
Run with: pytest tests/test_ldbg_integration.py -v

To skip integration tests, run: pytest tests/test_ldbg_integration.py -v -m "not integration"
"""

import os
import inspect
import pytest

import ldbg.ldbg as ldbg


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


def to_openrouter_model(provider: str, model: str | None = None) -> str:
    """
    Map a provider's model name to the corresponding OpenRouter model ID.
    Falls back to the provider's default_model if model is None.

    Args:
        provider: The provider name (e.g., 'openai', 'anthropic')
        model: Optional specific model name. If None, uses provider's default_model

    Returns:
        The OpenRouter model ID in the format "provider/model"

    Raises:
        ValueError: If provider is not found in PROVIDERS
    """
    if provider not in ldbg.PROVIDERS:
        raise ValueError(f"Unknown provider: {provider}")

    model = model or ldbg.PROVIDERS[provider]["default_model"]

    # Already an OpenRouter ID
    if provider == "openrouter" or "/" in model:
        return model

    # Map provider/model to OpenRouter's naming convention
    return f"{provider}/{model}"


@pytest.fixture(scope="module")
def openrouter_api_key():
    """Get OpenRouter API key from environment."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        pytest.skip("OPENROUTER_API_KEY not set")
    return api_key


@pytest.fixture
def setup_openrouter(monkeypatch, openrouter_api_key):
    """Setup OpenRouter as the provider for tests."""
    monkeypatch.setenv("LDBG_API", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", openrouter_api_key)
    # Reinitialize the client
    client, model = ldbg.initialize_client()
    # Monkeypatch the global client in ldbg module
    monkeypatch.setattr(ldbg, "client", client)
    monkeypatch.setattr(ldbg, "DEFAULT_MODEL", model)
    return client, model


def get_openrouter_model(provider_name: str, model: str | None = None) -> str:
    """Convert a provider's model name to OpenRouter model ID."""
    return to_openrouter_model(provider_name, model)


# Dynamically generate test parameters from PROVIDERS
def get_provider_models():
    """Get list of (provider_name, default_model, openrouter_model) tuples from PROVIDERS."""
    models = []
    for provider_name, config in ldbg.PROVIDERS.items():
        if provider_name == "ollama":
            # Skip ollama as it requires local setup
            continue
        default_model = config["default_model"]
        openrouter_model = get_openrouter_model(provider_name, default_model)
        models.append((provider_name, default_model, openrouter_model))
    return models


@pytest.mark.parametrize(
    "provider_name,default_model,openrouter_model",
    get_provider_models(),
    ids=lambda x: x[0],  # Use provider name as test ID
)
def test_default_models_via_openrouter(
    setup_openrouter,
    monkeypatch,
    capsys,
    provider_name,
    default_model,
    openrouter_model,
):
    """
    Test that each provider's default model can be accessed through OpenRouter.

    This test dynamically reads all providers from PROVIDERS and tests each one.
    """
    client, _ = setup_openrouter

    # Ensure VSCode warning doesn't interfere
    monkeypatch.setattr(ldbg, "display_vscode_warning", False)
    monkeypatch.setattr(ldbg, "execute_blocks", lambda resp_text, locals: None)

    # Make a real API call with a simple prompt
    prompt = f"Respond briefly with: 'Hello from {provider_name}'."

    ldbg.generate_commands(
        prompt, frame=inspect.currentframe(), model=openrouter_model, print_prompt=False
    )

    captured = capsys.readouterr()
    # Verify we got a response from the model
    assert f"Model {openrouter_model} says:" in captured.out, (
        f"Failed to get response from {openrouter_model} (provider: {provider_name})"
    )
    assert len(captured.out) > 0, (
        f"Empty response from {openrouter_model} (provider: {provider_name})"
    )
    # Verify we got actual content (not just error)
    assert (
        "Hello from" in captured.out or provider_name.lower() in captured.out.lower()
    ), (
        f"Response doesn't contain expected content from {openrouter_model} (provider: {provider_name})"
    )
