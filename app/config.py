"""Configuration module for Agentic Writer.

Per spec section 11.2, this module centralises:
- Model definitions (ID, display name, context size)
- File size limits
- Chunking parameters
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""

    # API Keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

    # Storage
    STORAGE_PATH = os.getenv("STORAGE_PATH", "./storage")
    FILES_PATH = os.path.join(STORAGE_PATH, "files")
    IMAGES_PATH = os.path.join(STORAGE_PATH, "images")
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{STORAGE_PATH}/agentic_writer.db")

    # Server
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "5001"))

    # Default Model
    DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-2.0-flash-exp")

    # File Processing
    MAX_FILE_SIZE_MB = 100
    CHUNK_SIZE_TOKENS = 8000  # For chunking oversized resources

    # Image Generation
    IMAGE_GEN_MODEL = "imagen-3.0-generate-001"  # "Nano Banana" model
    IMAGE_GEN_CANDIDATES = 4  # Number of image options to generate


class ModelDefinition:
    """Definition of an LLM model with its capabilities."""

    def __init__(
        self,
        model_id: str,
        display_name: str,
        context_window: int,
        supports_multimodal: bool = True,
        description: str = ""
    ):
        self.model_id = model_id
        self.display_name = display_name
        self.context_window = context_window
        self.supports_multimodal = supports_multimodal
        self.description = description

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "model_id": self.model_id,
            "display_name": self.display_name,
            "context_window": self.context_window,
            "supports_multimodal": self.supports_multimodal,
            "description": self.description
        }


# Model Registry
# Per spec section 2.2, support Gemini 3 Pro (default), 2.5 Pro, 2.5 Flash, 2.5 Flash-lite
MODELS = {
    "gemini-2.0-flash-exp": ModelDefinition(
        model_id="gemini-2.0-flash-exp",
        display_name="Gemini 2.0 Flash (Experimental)",
        context_window=1_000_000,
        supports_multimodal=True,
        description="Latest experimental flash model with 1M context"
    ),
    "gemini-1.5-pro": ModelDefinition(
        model_id="gemini-1.5-pro",
        display_name="Gemini 1.5 Pro",
        context_window=2_000_000,
        supports_multimodal=True,
        description="High-capability model with 2M context window"
    ),
    "gemini-1.5-flash": ModelDefinition(
        model_id="gemini-1.5-flash",
        display_name="Gemini 1.5 Flash",
        context_window=1_000_000,
        supports_multimodal=True,
        description="Fast model with 1M context window"
    ),
    "gemini-1.5-flash-8b": ModelDefinition(
        model_id="gemini-1.5-flash-8b",
        display_name="Gemini 1.5 Flash-8B",
        context_window=1_000_000,
        supports_multimodal=True,
        description="Lightweight flash model with 1M context"
    ),
}


def get_model_definition(model_id: str) -> ModelDefinition:
    """Get model definition by ID.

    Args:
        model_id: Model identifier

    Returns:
        ModelDefinition object

    Raises:
        ValueError: If model_id not found
    """
    if model_id not in MODELS:
        raise ValueError(f"Unknown model: {model_id}. Available models: {list(MODELS.keys())}")
    return MODELS[model_id]


def get_max_context_tokens(model_id: str) -> int:
    """Get maximum context window size for a model.

    Args:
        model_id: Model identifier

    Returns:
        Maximum context tokens
    """
    return get_model_definition(model_id).context_window


def list_available_models() -> list[ModelDefinition]:
    """List all available models.

    Returns:
        List of ModelDefinition objects
    """
    return list(MODELS.values())
