"""Tests for :mod:`backend.tasks.async_runner`."""

from __future__ import annotations

import pytest

from backend.tasks.async_runner import run_sqlalchemy_async


@pytest.mark.parametrize("raise_in_work", [False, True])
def test_run_sqlalchemy_async_always_disposes(
    monkeypatch: pytest.MonkeyPatch, raise_in_work: bool
) -> None:
    disposed = False

    async def fake_dispose() -> None:
        nonlocal disposed
        disposed = True

    monkeypatch.setattr(
        "backend.tasks.async_runner.dispose_engine",
        fake_dispose,
    )

    async def work() -> int:
        if raise_in_work:
            msg = "boom"
            raise RuntimeError(msg)
        return 7

    if raise_in_work:
        with pytest.raises(RuntimeError, match="boom"):
            run_sqlalchemy_async(work)
    else:
        assert run_sqlalchemy_async(work) == 7

    assert disposed is True
