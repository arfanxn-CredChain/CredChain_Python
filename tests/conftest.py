"""Shared pytest fixtures for the CredChain_Python test suite."""

from unittest.mock import MagicMock

import numpy as np
import pytest


@pytest.fixture
def mock_easyocr_reader() -> MagicMock:
    """Mocked easyocr.Reader. readtext returns a single fragment."""
    reader = MagicMock()
    reader.readtext.return_value = [
        ([[0, 0], [10, 0], [10, 10], [0, 10]], "Mocked OCR text", 0.95),
    ]
    return reader


@pytest.fixture
def mock_embedding_model() -> MagicMock:
    """Mocked SentenceTransformer that returns a deterministic 768-dim vector."""
    model = MagicMock()
    fixed_vector = np.full(768, 0.01, dtype=np.float32)
    model.encode.return_value = fixed_vector
    return model


collect_ignore = ["integration_test.py"]
