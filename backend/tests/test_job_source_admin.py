from __future__ import annotations

from unittest.mock import patch

from django.test import Client, TestCase

from apps.accounts.models import User
from apps.jobs.forms import JobSourceConfigDraftAdminForm
from apps.jobs.models import (
    DraftStatus,
    JobSourceConfigDraft,
    JobSourceDiscoveryRun,
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
        run = JobSourceDiscoveryRun.objects.get(provider=provider)
        enqueue_discovery.assert_called_once_with(str(provider.id), str(run.id))

    def test_provider_detail_form_queues_discovery_with_hints(self) -> None:
        provider = JobSourceProvider.objects.create(
            slug="example-jobs",
            display_name="Example Jobs",
            docs_url="https://example.com/docs",
        )

        with patch("apps.jobs.admin.discover_provider_task.delay") as enqueue_discovery:
            response = self.client.post(
                f"/admin/jobs/jobsourceprovider/{provider.id}/run-discovery/",
                {"known_auth_type": "bearer", "keywords": "jobs, vacancies"},
            )

        assert response.status_code == 302
        run = JobSourceDiscoveryRun.objects.get(provider=provider)
        assert run.known_auth_type == "bearer"
        assert run.keywords == ["jobs", "vacancies"]
        enqueue_discovery.assert_called_once_with(
            str(provider.id), str(run.id), "bearer", ["jobs", "vacancies"]
        )

    def test_non_staff_cannot_open_guided_discovery_form(self) -> None:
        provider = JobSourceProvider.objects.create(
            slug="example-jobs",
            display_name="Example Jobs",
            docs_url="https://example.com/docs",
        )
        normal_user = User.objects.create_user(
            username="member",
            email="member@example.com",
            password="strong-password-123",
        )
        self.client.force_login(normal_user)

        response = self.client.get(f"/admin/jobs/jobsourceprovider/{provider.id}/run-discovery/")

        assert response.status_code == 302
        assert "/admin/login/" in response.headers["Location"]

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

    def test_approving_replacement_supersedes_previous_draft(self) -> None:
        provider = JobSourceProvider.objects.create(
            slug="example-jobs",
            display_name="Example Jobs",
            docs_url="https://example.com/docs",
            status=ProviderStatus.ACTIVE,
        )
        previous = JobSourceConfigDraft.objects.create(
            provider=provider,
            status=DraftStatus.APPROVED,
            config={"base_url": "https://old.example.com", "endpoint_path": "/jobs"},
        )
        replacement = JobSourceConfigDraft.objects.create(
            provider=provider,
            status=DraftStatus.VALIDATED,
            config={"base_url": "https://new.example.com", "endpoint_path": "/jobs"},
        )

        response = self.client.post(f"/admin/jobs/jobsourceconfigdraft/{replacement.id}/approve/")

        assert response.status_code == 302
        previous.refresh_from_db()
        replacement.refresh_from_db()
        assert previous.status == DraftStatus.SUPERSEDED
        assert replacement.status == DraftStatus.APPROVED
        assert (
            JobSourceConfigDraft.objects.filter(
                provider=provider, status=DraftStatus.APPROVED
            ).count()
            == 1
        )

    def test_draft_admin_form_rejects_invalid_config(self) -> None:
        provider = JobSourceProvider.objects.create(
            slug="example-jobs",
            display_name="Example Jobs",
            docs_url="https://example.com/docs",
        )
        form = JobSourceConfigDraftAdminForm(
            data={
                "provider": provider.id,
                "config": {"endpoint_path": "/jobs"},
                "confidence_score": 0.5,
                "evidence_urls": [],
                "validation_errors": [],
            }
        )

        assert not form.is_valid()
        assert "config" in form.errors

    def test_draft_admin_shows_example_urls(self) -> None:
        provider = JobSourceProvider.objects.create(
            slug="example-jobs",
            display_name="Example Jobs",
            docs_url="https://example.com/docs",
        )
        draft = JobSourceConfigDraft.objects.create(
            provider=provider,
            config={
                "base_url": "https://api.example.com",
                "endpoint_path": "/jobs",
                "examples": [{"name": "Search", "final_url": "https://api.example.com/jobs?q=dev"}],
            },
        )

        response = self.client.get(f"/admin/jobs/jobsourceconfigdraft/{draft.id}/change/")

        assert response.status_code == 200
        assert "https://api.example.com/jobs?q=dev" in response.content.decode()
