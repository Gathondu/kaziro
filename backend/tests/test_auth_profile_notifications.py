from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.test import AsyncClient, Client, TransactionTestCase
from django.utils import timezone

from apps.accounts.email import EmailDeliveryResult
from apps.accounts.models import User
from apps.accounts.services import issue_token_pair
from apps.jobs import fetcher
from apps.jobs.models import (
    DraftStatus,
    JobSourceConfigDraft,
    JobSourceProvider,
    ProviderStatus,
    RawJob,
)
from apps.notifications.models import Notification
from apps.notifications.tasks import create_notification_task


def post_json(client: Client, path: str, payload: dict[str, object], **extra: Any):
    return client.post(
        path,
        data=json.dumps(payload),
        content_type="application/json",
        **extra,
    )


async def async_post_json(client: AsyncClient, path: str, payload: dict[str, object], **extra: Any):
    return await client.post(
        path,
        data=json.dumps(payload),
        content_type="application/json",
        **extra,
    )


def put_json(client: Client, path: str, payload: dict[str, object], **extra: Any):
    return client.put(
        path,
        data=json.dumps(payload),
        content_type="application/json",
        **extra,
    )


async def async_put_json(client: AsyncClient, path: str, payload: dict[str, object], **extra: Any):
    return await client.put(
        path,
        data=json.dumps(payload),
        content_type="application/json",
        **extra,
    )


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class AuthProfileNotificationTests(TransactionTestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.async_client = AsyncClient()

    async def test_signup_confirmation_login_and_me_flow(self) -> None:
        with patch(
            "apps.accounts.services.send_confirmation_email",
            return_value=EmailDeliveryResult(sent=True, provider_id="email_123"),
        ) as send_email:
            signup_response = await async_post_json(
                self.async_client,
                "/api/v1/auth/signup",
                {
                    "email": "candidate@example.com",
                    "password": "strong-password-123",
                    "username": "Jamie",
                },
            )

        assert signup_response.status_code == 200
        signup_payload = signup_response.json()
        assert signup_payload["data"]["confirmation_required"] is True
        assert signup_payload["data"]["confirmation_sent"] is True

        login_before_confirm = await async_post_json(
            self.async_client,
            "/api/v1/auth/login",
            {
                "identifier": "candidate@example.com",
                "password": "strong-password-123",
            },
        )
        assert login_before_confirm.status_code == 403
        assert login_before_confirm.json()["error"]["code"] == "email_not_confirmed"

        confirmation_url = send_email.call_args.kwargs["confirmation_url"]
        token = parse_qs(urlparse(confirmation_url).query)["token"][0]
        confirm_response = await async_post_json(
            self.async_client,
            "/api/v1/auth/confirm-email",
            {"token": token},
        )
        assert confirm_response.status_code == 200
        access_token = confirm_response.json()["data"]["token"]["access_token"]

        me_response = await self.async_client.get(
            "/api/v1/auth/me", headers=auth_header(access_token)
        )
        assert me_response.status_code == 200
        assert me_response.json()["data"]["email"] == "candidate@example.com"

    async def test_profile_config_and_notification_flow(self) -> None:
        user = await self._confirmed_user()
        token = issue_token_pair(user).access_token

        profile_response = await async_put_json(
            self.async_client,
            "/api/v1/profile",
            {
                "full_name": "Jamie Candidate",
                "professional_summary": "Backend engineer",
                "skills": ["Python", "Django"],
                "experience_years": 7,
                "domain": "job search automation",
            },
            headers=auth_header(token),
        )
        assert profile_response.status_code == 200
        assert profile_response.json()["data"]["skills"] == [
            "Python",
            "Django",
        ]

        config_response = await async_post_json(
            self.async_client,
            "/api/v1/job-configs",
            {
                "name": "Backend roles",
                "keywords": ["django", "Django Ninja"],
                "location": "Remote",
                "remote_only": True,
                "fetch_schedule_cron": "0 6 * * *",
            },
            headers=auth_header(token),
        )
        assert config_response.status_code == 200
        config_id = config_response.json()["data"]["id"]

        with patch("apps.jobs.services.run_pipeline_for_config.delay") as enqueue_pipeline:
            enqueue_pipeline.return_value.id = "pipeline-task-1"
            run_response = await async_post_json(
                self.async_client,
                f"/api/v1/job-configs/{config_id}/run",
                {},
                headers=auth_header(token),
            )
        assert run_response.status_code == 200
        assert run_response.json()["data"]["task_id"] == "pipeline-task-1"

        with (
            patch(
                "apps.jobs.services.run_pipeline_for_config.delay",
                side_effect=RuntimeError("broker unavailable"),
            ),
            patch(
                "apps.jobs.services.create_notification_task.delay",
                side_effect=RuntimeError("broker unavailable"),
            ),
        ):
            fallback_response = await async_post_json(
                self.async_client,
                f"/api/v1/job-configs/{config_id}/run",
                {},
                headers=auth_header(token),
            )
        assert fallback_response.status_code == 200
        assert await Notification.objects.filter(
            user=user, event_type="job_config_queued"
        ).aexists()

        notifications_response = await self.async_client.get(
            "/api/v1/notifications?unread_only=true",
            headers=auth_header(token),
        )
        assert notifications_response.status_code == 200
        assert notifications_response.json()["data"]["unread_count"] == 1

    async def test_notification_task_creates_user_notification(self) -> None:
        user = await self._confirmed_user(email="task@example.com")
        notification_id = create_notification_task(
            user.id,
            "documents_ready",
            "Documents ready",
            "Your documents are ready to review.",
            None,
        )
        notification = await Notification.objects.aget(id=notification_id)
        # pyrefly: ignore [missing-attribute]
        assert notification.user_id == user.id

    async def test_notification_stream_uses_proxy_safe_headers(self) -> None:
        user = await self._confirmed_user(email="stream@example.com")
        token = issue_token_pair(user).access_token

        response = await self.async_client.get(
            "/api/v1/notifications/stream",
            headers=auth_header(token),
        )

        assert response.status_code == 200
        assert response["Content-Type"] == "text/event-stream"
        assert response["Cache-Control"] == "no-cache, no-transform"
        assert response["X-Accel-Buffering"] == "no"
        assert "Connection" not in response.headers
        response.close()

    async def test_job_source_admin_flow_requires_validated_draft(self) -> None:
        staff = await self._confirmed_user(email="staff@example.com", is_staff=True)
        token = issue_token_pair(staff).access_token

        provider_response = await async_post_json(
            self.async_client,
            "/api/v1/job-sources",
            {
                "slug": "example-jobs",
                "display_name": "Example Jobs",
                "docs_url": "https://example.com/docs",
            },
            headers=auth_header(token),
        )
        assert provider_response.status_code == 200
        provider_id = provider_response.json()["data"]["id"]

        provider = await JobSourceProvider.objects.aget(id=provider_id)
        draft = await JobSourceConfigDraft.objects.acreate(
            provider=provider,
            status=DraftStatus.GENERATED,
            confidence_score=0.8,
            config={
                "base_url": "https://api.example.com",
                "endpoint_path": "/v1/jobs",
                "method": "GET",
                "query_params": {"keywords": "query"},
                "pagination": {
                    "type": "page",
                    "page_param": "page",
                    "page_size_param": "limit",
                    "default_page_size": 10,
                },
                "auth": {"type": "none"},
                "response_mapping": {"external_id": "id"},
                "confidence_score": 0.8,
                "evidence_urls": ["https://example.com/docs"],
            },
        )

        rejected_approval = await async_post_json(
            self.async_client,
            f"/api/v1/job-sources/drafts/{draft.id}/approve",
            {},
            headers=auth_header(token),
        )
        assert rejected_approval.status_code == 400

        draft.status = DraftStatus.VALIDATED
        await draft.asave(update_fields=["status", "updated_at"])
        approval = await async_post_json(
            self.async_client,
            f"/api/v1/job-sources/drafts/{draft.id}/approve",
            {},
            headers=auth_header(token),
        )
        assert approval.status_code == 200
        assert approval.json()["data"]["status"] == DraftStatus.APPROVED
        provider = await JobSourceProvider.objects.aget(id=provider_id)
        assert provider.status == ProviderStatus.ACTIVE

    async def test_approved_provider_fetch_stores_and_dedupes_raw_jobs(self) -> None:
        user = await self._confirmed_user(email="fetch@example.com")
        config = await self._job_config(user)
        provider = await JobSourceProvider.objects.acreate(
            slug="fixture",
            display_name="Fixture",
            docs_url="https://example.com/docs",
            status=ProviderStatus.ACTIVE,
        )
        await JobSourceConfigDraft.objects.acreate(
            provider=provider,
            status=DraftStatus.APPROVED,
            confidence_score=1,
            config={
                "base_url": "https://api.example.com",
                "endpoint_path": "/jobs",
                "method": "GET",
                "query_params": {"keywords": "q", "location": "where"},
                "pagination": {
                    "type": "page",
                    "page_param": "page",
                    "page_size_param": "limit",
                    "default_page_size": 5,
                },
                "auth": {"type": "none"},
                "response_mapping": {"external_id": "id"},
                "confidence_score": 1,
                "evidence_urls": ["https://example.com/docs"],
            },
        )

        with patch(
            "apps.jobs.fetcher._get_json",
            return_value=(
                200,
                {"jobs": [{"id": "job-1", "title": "Engineer"}]},
                {},
            ),
        ):
            first_run = await fetcher.fetch_jobs_for_config(config)
            second_run = await fetcher.fetch_jobs_for_config(config)

        assert len(first_run) == 1
        assert second_run == []
        assert await RawJob.objects.filter(provider=provider, external_job_id="job-1").acount() == 1

    def test_protected_routes_return_envelope_401(self) -> None:
        response = self.client.get("/api/v1/profile")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"

    async def _confirmed_user(
        self,
        email: str = "confirmed@example.com",
        *,
        is_staff: bool = False,
    ) -> User:
        return await User.objects.acreate(
            email=email,
            password="strong-password-123",
            username="Jamie",
            is_active=True,
            is_staff=is_staff,
            email_confirmed_at=timezone.now(),
        )

    async def _job_config(self, user: User):
        from apps.jobs.models import JobSearchConfig

        return await JobSearchConfig.objects.acreate(
            user=user,
            name="Fetch roles",
            keywords=["django"],
            location="Remote",
        )
