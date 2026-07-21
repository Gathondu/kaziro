from __future__ import annotations

from unittest.mock import patch

from django.test import Client, TestCase

from apps.accounts.models import User
from apps.jobs.models import (
    DraftStatus,
    JobSourceConfigDraft,
    JobSourceProvider,
    ProviderStatus,
)


class JobSourceAdminActionTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="strong-password-123",
        )
        self.client.force_login(self.admin_user)

    def test_provider_admin_action_queues_discovery(self) -> None:
        provider = JobSourceProvider.objects.create(
            slug="example-jobs",
            display_name="Example Jobs",
            docs_url="https://example.com/docs",
        )

        with patch("apps.jobs.admin.discover_provider_task.delay") as enqueue_discovery:
            response = self.client.post(
                "/admin/jobs/jobsourceprovider/",
                {
                    "action": "run_discovery",
                    "_selected_action": [str(provider.id)],
                    "index": "0",
                },
                follow=True,
            )

        assert response.status_code == 200
        enqueue_discovery.assert_called_once_with(str(provider.id))

    def test_draft_admin_action_queues_validation(self) -> None:
        provider = JobSourceProvider.objects.create(
            slug="example-jobs",
            display_name="Example Jobs",
            docs_url="https://example.com/docs",
        )
        draft = JobSourceConfigDraft.objects.create(
            provider=provider,
            status=DraftStatus.GENERATED,
            config={"base_url": "https://api.example.com", "endpoint_path": "/jobs"},
        )

        with patch("apps.jobs.admin.validate_provider_draft_task.delay") as enqueue_validation:
            response = self.client.post(
                "/admin/jobs/jobsourceconfigdraft/",
                {
                    "action": "validate_drafts",
                    "_selected_action": [str(draft.id)],
                    "index": "0",
                },
                follow=True,
            )

        assert response.status_code == 200
        enqueue_validation.assert_called_once_with(str(draft.id))

    def test_draft_admin_action_approves_only_validated_drafts(self) -> None:
        provider = JobSourceProvider.objects.create(
            slug="example-jobs",
            display_name="Example Jobs",
            docs_url="https://example.com/docs",
        )
        validated_draft = JobSourceConfigDraft.objects.create(
            provider=provider,
            status=DraftStatus.VALIDATED,
            config={"base_url": "https://api.example.com", "endpoint_path": "/jobs"},
        )
        generated_draft = JobSourceConfigDraft.objects.create(
            provider=provider,
            status=DraftStatus.GENERATED,
            config={"base_url": "https://api.example.com", "endpoint_path": "/jobs"},
        )

        response = self.client.post(
            "/admin/jobs/jobsourceconfigdraft/",
            {
                "action": "approve_validated_drafts",
                "_selected_action": [str(validated_draft.id), str(generated_draft.id)],
                "index": "0",
            },
            follow=True,
        )

        assert response.status_code == 200
        validated_draft.refresh_from_db()
        generated_draft.refresh_from_db()
        provider.refresh_from_db()
        assert validated_draft.status == DraftStatus.APPROVED
        assert validated_draft.approved_at is not None
        assert generated_draft.status == DraftStatus.GENERATED
        assert provider.status == ProviderStatus.ACTIVE
