from __future__ import annotations

from datetime import UTC, date, datetime

from django.test import SimpleTestCase

from apps.pipeline.parser_agent import _parse_posted_date


class ParserPostedDateTests(SimpleTestCase):
    reference = datetime(2026, 7, 28, 11, 20, tzinfo=UTC)

    def test_parses_iso_dates_and_timestamps(self) -> None:
        assert _parse_posted_date("2026-07-27", reference=self.reference) == date(2026, 7, 27)
        assert _parse_posted_date("2026-07-27T19:30:00Z", reference=self.reference) == date(
            2026, 7, 27
        )

    def test_parses_provider_relative_dates(self) -> None:
        assert _parse_posted_date("today", reference=self.reference) == date(2026, 7, 28)
        assert _parse_posted_date("yesterday", reference=self.reference) == date(2026, 7, 27)
        assert _parse_posted_date("1 day ago", reference=self.reference) == date(2026, 7, 27)
        assert _parse_posted_date("Posted 3 hours ago", reference=self.reference) == date(
            2026, 7, 28
        )
        assert _parse_posted_date("2 weeks ago", reference=self.reference) == date(2026, 7, 14)
        assert _parse_posted_date("30+ days ago", reference=self.reference) == date(2026, 6, 28)

    def test_unknown_date_does_not_fail_parsing(self) -> None:
        assert _parse_posted_date("recently", reference=self.reference) is None
