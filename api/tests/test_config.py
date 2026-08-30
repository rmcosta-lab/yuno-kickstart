"""Tests for deployment-facing settings parsing."""

import pytest
from app.config import Settings
from pydantic import ValidationError


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("https://volta-control-tower.vercel.app", ["https://volta-control-tower.vercel.app"]),
        (
            "https://volta-control-tower.vercel.app,https://preview.vercel.app",
            ["https://volta-control-tower.vercel.app", "https://preview.vercel.app"],
        ),
        (
            '["https://volta-control-tower.vercel.app"]',
            ["https://volta-control-tower.vercel.app"],
        ),
    ],
)
def test_cors_origins_accepts_render_friendly_values(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
    expected: list[str],
) -> None:
    monkeypatch.setenv("CORS_ORIGINS", value)

    assert Settings().cors_origins == expected


def test_cors_origins_rejects_wildcard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "*")

    with pytest.raises(ValidationError, match="explicit origins"):
        Settings()
