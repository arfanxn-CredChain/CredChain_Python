"""Shared pytest fixtures for the CredChain_Python test suite."""

from unittest.mock import MagicMock

import numpy as np
import pytest


@pytest.fixture
def mock_embedding_model() -> MagicMock:
    """Mocked SentenceTransformer that returns a deterministic float vector."""
    model = MagicMock()
    fixed_vector = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    model.encode.return_value = fixed_vector
    return model


@pytest.fixture
def mock_gemini_client() -> MagicMock:
    """Mocked google.genai.Client."""
    return MagicMock()
