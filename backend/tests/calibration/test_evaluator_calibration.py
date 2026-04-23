"""Evaluator calibration harness (T2.5 scaffolding).

Full accuracy gates + VCR replay land in a follow-up when cassettes are
recorded. This module validates the fixture corpus shape and balance so
CI can load the JSON without shipping silent drift.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

_SET_PATH = Path(__file__).resolve().parent / "evaluator_set.json"


@pytest.mark.calibration
def test_evaluator_calibration_fixture_count_and_balance() -> None:
    rows = json.loads(_SET_PATH.read_text(encoding="utf-8"))
    assert len(rows) == 50
    counts = Counter(str(r["expected_classification"]) for r in rows)
    for label in ("GOOD_FIT", "MAYBE", "REJECT"):
        assert counts[label] >= 15, counts
