from __future__ import annotations

import uuid

from django.test import SimpleTestCase
from django.utils import timezone

from apps.profiles.models import UserProfile
from apps.profiles.services import _safe_original_filename, to_response


class ProfileCvTests(SimpleTestCase):
    def test_uploaded_cv_filename_is_sanitized(self) -> None:
        assert _safe_original_filename(r"C:\fakepath\Denis Resume.pdf") == "Denis Resume.pdf"
        assert _safe_original_filename("../../Denis Resume.pdf") == "Denis Resume.pdf"
        assert _safe_original_filename(None) == "master-cv.pdf"

    def test_profile_response_includes_original_cv_filename(self) -> None:
        now = timezone.now()
        profile = UserProfile(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            full_name="Denis Gathondu",
            cv_storage_path="profiles/user-id/master-cv.pdf",
            cv_original_filename="Denis Resume.pdf",
            created_at=now,
            updated_at=now,
        )

        response = to_response(profile)

        assert response.has_master_cv is True
        assert response.cv_original_filename == "Denis Resume.pdf"
