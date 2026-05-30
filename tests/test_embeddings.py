from unittest.mock import MagicMock

import numpy as np
import pytest

from app import embeddings
from app.errors import AppError


def test_encode_returns_python_floats():
    model = MagicMock()
    model.encode.return_value = np.array([0.1, 0.2, -0.3], dtype=np.float32)
    out = embeddings.encode(model, "hello world")
    assert isinstance(out, list)
    assert all(isinstance(x, float) for x in out)
    assert out == pytest.approx([0.1, 0.2, -0.3], rel=1e-6)


def test_encode_calls_model_with_normalize_true():
    model = MagicMock()
    model.encode.return_value = np.zeros(768, dtype=np.float32)
    embeddings.encode(model, "any text")
    assert model.encode.called
    kwargs = model.encode.call_args.kwargs
    assert kwargs.get("normalize_embeddings") is True


def test_encode_empty_text_raises():
    model = MagicMock()
    with pytest.raises(AppError):
        embeddings.encode(model, "")


def test_cosine_similarity_identical_vectors():
    a = [1.0, 0.0, 0.0]
    sim = embeddings.cosine_similarity(a, a)
    assert sim == pytest.approx(1.0, rel=1e-6)


def test_cosine_similarity_orthogonal():
    sim = embeddings.cosine_similarity([1.0, 0.0], [0.0, 1.0])
    assert sim == pytest.approx(0.0, abs=1e-6)


def test_cosine_similarity_opposite():
    sim = embeddings.cosine_similarity([1.0, 0.0], [-1.0, 0.0])
    assert sim == pytest.approx(-1.0, rel=1e-6)


def test_cosine_similarity_mismatched_lengths_raises():
    with pytest.raises(AppError):
        embeddings.cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0])


def test_cosine_similarity_zero_vector_returns_zero():
    sim = embeddings.cosine_similarity([0.0, 0.0], [1.0, 1.0])
    assert sim == 0.0
