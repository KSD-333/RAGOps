"""Unit tests for retrieval evaluation metrics."""

from __future__ import annotations

import pytest
from ragops.evaluation.retrieval import mrr, precision_at_k, recall_at_k


def test_recall_at_k_calculation():
    expected = ["c1", "c2", "c3"]
    retrieved = ["c1", "c4", "c2", "c5"]

    assert recall_at_k(expected, retrieved, k=2) == 1 / 3
    assert recall_at_k(expected, retrieved, k=3) == 2 / 3
    assert recall_at_k(expected, retrieved, k=4) == 2 / 3
    assert recall_at_k([], retrieved) == 1.0


def test_precision_at_k_calculation():
    expected = ["c1", "c2"]
    retrieved = ["c1", "c3", "c2", "c4"]

    assert precision_at_k(expected, retrieved, k=1) == 1.0
    assert precision_at_k(expected, retrieved, k=2) == 0.5
    assert precision_at_k(expected, retrieved, k=4) == 0.5
    assert precision_at_k(expected, []) == 0.0


def test_mrr_calculation():
    expected = ["c2"]
    retrieved1 = ["c2", "c1", "c3"]
    retrieved2 = ["c1", "c2", "c3"]
    retrieved3 = ["c1", "c3", "c4"]

    assert mrr(expected, retrieved1) == 1.0
    assert mrr(expected, retrieved2) == 0.5
    assert mrr(expected, retrieved3) == 0.0
