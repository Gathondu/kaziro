from __future__ import annotations

from django import forms

from apps.jobs.models import JobSourceConfigDraft
from apps.jobs.source_config import validate_provider_config


class DiscoveryRunForm(forms.Form):
    known_auth_type = forms.ChoiceField(
        required=False,
        choices=(
            ("", "Discover from documentation"),
            ("none", "No authentication"),
            ("bearer", "Bearer token"),
            ("static_header", "Static header"),
            ("query_param_key", "Query parameter API key"),
        ),
    )
    keywords = forms.CharField(
        required=False,
        help_text="Optional comma-separated terms that identify job-listing endpoints.",
    )

    def cleaned_keywords(self) -> list[str]:
        value = self.cleaned_data.get("keywords", "")
        return [item.strip() for item in value.split(",") if item.strip()]


class JobSourceConfigDraftAdminForm(forms.ModelForm):
    class Meta:
        model = JobSourceConfigDraft
        fields = "__all__"

    def clean_config(self) -> dict[str, object]:
        config = self.cleaned_data["config"]
        try:
            return validate_provider_config(config).model_dump(mode="json")
        except ValueError as exc:
            raise forms.ValidationError(f"Invalid provider configuration: {exc}") from exc


__all__ = ["DiscoveryRunForm", "JobSourceConfigDraftAdminForm"]
