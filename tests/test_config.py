"""Tests for configuration module."""

import pytest
from app.config import Config, ModelDefinition, get_model_definition, list_available_models


def test_config_has_required_fields():
    """Test that Config has all required fields."""
    assert hasattr(Config, 'GEMINI_API_KEY')
    assert hasattr(Config, 'STORAGE_PATH')
    assert hasattr(Config, 'DEFAULT_MODEL')


def test_model_definition_creation():
    """Test ModelDefinition creation."""
    model = ModelDefinition(
        model_id="test-model",
        display_name="Test Model",
        context_window=100000,
        supports_multimodal=True,
        description="A test model"
    )

    assert model.model_id == "test-model"
    assert model.display_name == "Test Model"
    assert model.context_window == 100000
    assert model.supports_multimodal is True


def test_model_definition_to_dict():
    """Test ModelDefinition.to_dict()."""
    model = ModelDefinition(
        model_id="test-model",
        display_name="Test Model",
        context_window=100000
    )

    model_dict = model.to_dict()
    assert isinstance(model_dict, dict)
    assert model_dict['model_id'] == "test-model"
    assert model_dict['context_window'] == 100000


def test_get_model_definition():
    """Test getting a model definition."""
    model = get_model_definition("gemini-2.0-flash-exp")
    assert isinstance(model, ModelDefinition)
    assert model.model_id == "gemini-2.0-flash-exp"


def test_get_model_definition_invalid():
    """Test getting invalid model definition."""
    with pytest.raises(ValueError):
        get_model_definition("invalid-model")


def test_list_available_models():
    """Test listing available models."""
    models = list_available_models()
    assert isinstance(models, list)
    assert len(models) > 0
    assert all(isinstance(m, ModelDefinition) for m in models)
