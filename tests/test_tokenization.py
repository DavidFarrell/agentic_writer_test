"""Tests for tokenization service."""

import pytest
from app.services.tokenization import TokenizationService, count_tokens, max_context_tokens
from app.config import Config


def test_tokenization_service_init():
    """Test TokenizationService initialization."""
    service = TokenizationService()
    assert service is not None
    assert isinstance(service._token_cache, dict)


def test_count_tokens_basic():
    """Test basic token counting."""
    if not Config.GEMINI_API_KEY:
        pytest.skip("No API key configured")

    text = "Hello, world! This is a test."
    model_id = "gemini-2.0-flash-exp"

    tokens = count_tokens(text, model_id)
    assert tokens > 0
    assert isinstance(tokens, int)


def test_count_tokens_empty():
    """Test token counting with empty string."""
    if not Config.GEMINI_API_KEY:
        pytest.skip("No API key configured")

    text = ""
    model_id = "gemini-2.0-flash-exp"

    tokens = count_tokens(text, model_id)
    assert tokens >= 0


def test_max_context_tokens():
    """Test getting max context tokens."""
    model_id = "gemini-2.0-flash-exp"
    max_tokens = max_context_tokens(model_id)

    assert max_tokens > 0
    assert max_tokens == 1_000_000  # Expected for this model


def test_max_context_tokens_invalid_model():
    """Test getting max context for invalid model."""
    with pytest.raises(ValueError):
        max_context_tokens("invalid-model-id")
