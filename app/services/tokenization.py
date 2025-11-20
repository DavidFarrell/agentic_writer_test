"""Tokenization service for Gemini models.

Per spec section 6.1, this module:
- Loads the appropriate tokeniser for each supported model
- Provides count_tokens(text, model_id) and max_context_tokens(model_id)
- Caches results per (resource_id, model_id) pair
"""

import google.generativeai as genai
from app.config import Config, get_max_context_tokens as get_max_from_config
from typing import Dict, Tuple, Optional
import hashlib

# Configure Gemini
genai.configure(api_key=Config.GEMINI_API_KEY)


class TokenizationService:
    """Service for tokenizing text using Gemini models."""

    def __init__(self):
        self._token_cache: Dict[Tuple[str, str], int] = {}  # (text_hash, model_id) -> token_count
        self._models: Dict[str, genai.GenerativeModel] = {}

    def _get_model(self, model_id: str) -> genai.GenerativeModel:
        """Get or create a model instance.

        Args:
            model_id: Model identifier

        Returns:
            GenerativeModel instance
        """
        if model_id not in self._models:
            self._models[model_id] = genai.GenerativeModel(model_id)
        return self._models[model_id]

    def _hash_text(self, text: str) -> str:
        """Create a hash of the text for caching.

        Args:
            text: Input text

        Returns:
            Hash string
        """
        return hashlib.md5(text.encode()).hexdigest()

    def count_tokens(
        self,
        text: str,
        model_id: str,
        use_cache: bool = True,
        resource_id: Optional[int] = None
    ) -> int:
        """Count tokens in text using specified model's tokenizer.

        Args:
            text: Text to tokenize
            model_id: Model identifier
            use_cache: Whether to use cache
            resource_id: Optional resource ID for cache key

        Returns:
            Token count
        """
        # Create cache key
        if resource_id is not None:
            cache_key = (f"resource_{resource_id}", model_id)
        else:
            cache_key = (self._hash_text(text), model_id)

        # Check cache
        if use_cache and cache_key in self._token_cache:
            return self._token_cache[cache_key]

        # Get model and count tokens
        try:
            model = self._get_model(model_id)
            result = model.count_tokens(text)
            token_count = result.total_tokens

            # Cache result
            if use_cache:
                self._token_cache[cache_key] = token_count

            return token_count

        except Exception as e:
            # Fallback: rough estimate (4 chars per token)
            print(f"Warning: Token counting failed for {model_id}: {e}")
            print(f"Using fallback estimation")
            estimated = len(text) // 4
            return estimated

    def max_context_tokens(self, model_id: str) -> int:
        """Get maximum context window size for a model.

        Args:
            model_id: Model identifier

        Returns:
            Maximum context tokens
        """
        return get_max_from_config(model_id)

    def clear_cache(self):
        """Clear the token count cache."""
        self._token_cache.clear()


# Global instance
_tokenization_service = TokenizationService()


def count_tokens(text: str, model_id: str, resource_id: Optional[int] = None) -> int:
    """Count tokens in text using specified model.

    Convenience function that uses the global TokenizationService instance.

    Args:
        text: Text to tokenize
        model_id: Model identifier
        resource_id: Optional resource ID for caching

    Returns:
        Token count
    """
    return _tokenization_service.count_tokens(text, model_id, resource_id=resource_id)


def max_context_tokens(model_id: str) -> int:
    """Get maximum context window size for a model.

    Convenience function that uses the global TokenizationService instance.

    Args:
        model_id: Model identifier

    Returns:
        Maximum context tokens
    """
    return _tokenization_service.max_context_tokens(model_id)
