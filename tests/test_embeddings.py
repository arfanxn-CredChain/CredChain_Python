"""Tests for app/embeddings.py — EmbeddingGemma wrapper."""

from unittest.mock import MagicMock

import numpy as np
import pytest

from app import codes
from app.embeddings import cosine_similarity, encode
from app.errors import AppError


class TestEncode:
    def test_encode_returns_float_list(self):
        model = MagicMock()
        fixed = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        model.encode.return_value = fixed
        result = encode(model, "hello world")
        assert result == pytest.approx([0.1, 0.2, 0.3])
        assert all(isinstance(x, float) for x in result)

    def test_encode_empty_text_raises(self):
        model = MagicMock()
        with pytest.raises(AppError) as exc:
            encode(model, "")
        assert exc.value.code == codes.CODE_AI_INTERNAL

    def test_encode_whitespace_only_raises(self):
        model = MagicMock()
        with pytest.raises(AppError) as exc:
            encode(model, "   ")
        assert exc.value.code == codes.CODE_AI_INTERNAL


class TestCosineSimilarity:
    def test_identical_vectors(self):
        a = [1.0, 2.0, 3.0]
        b = [1.0, 2.0, 3.0]
        assert abs(cosine_similarity(a, b) - 1.0) < 1e-6

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert abs(cosine_similarity(a, b) - 0.0) < 1e-6

    def test_opposite_vectors(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert abs(cosine_similarity(a, b) - (-1.0)) < 1e-6

    def test_mismatched_lengths_raises(self):
        with pytest.raises(AppError) as exc:
            cosine_similarity([1.0, 2.0], [1.0, 2.0, 3.0])
        assert exc.value.code == codes.CODE_AI_INTERNAL

    def test_zero_magnitude_returns_zero(self):
        assert cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0
        assert cosine_similarity([1.0, 2.0], [0.0, 0.0]) == 0.0
