from __future__ import annotations

from functools import partial
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.db import migrations

TRACKING_QUERY_PARAMETERS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "referrer",
    "source",
}


def normalize_url(value):
    text = str(value or "").strip()
    if not text:
        return ""
    parsed = urlsplit(text)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return text
    hostname = parsed.hostname.lower()
    port = parsed.port
    default_port = (parsed.scheme.lower() == "http" and port == 80) or (
        parsed.scheme.lower() == "https" and port == 443
    )
    netloc = hostname if port is None or default_port else f"{hostname}:{port}"
    path = parsed.path.rstrip("/") or "/"
    query = urlencode(
        sorted(
            (key, item)
            for key, item in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.lower().startswith("utm_") and key.lower() not in TRACKING_QUERY_PARAMETERS
        )
    )
    return urlunsplit((parsed.scheme.lower(), netloc, path, query, ""))


def posting_rank(
    row,
    *,
    evaluation_ids,
    protected_ids,
    document_evaluation_ids,
    summary_ids,
):
    evaluation_id = evaluation_ids.get(row["id"])
    return (
        row["id"] in protected_ids,
        evaluation_id in document_evaluation_ids,
        evaluation_id is not None,
        row["id"] in summary_ids,
        row["parsed_at"],
        str(row["id"]),
    )


def deduplicate_job_postings(apps, schema_editor):
    JobPosting = apps.get_model("jobs", "JobPosting")
    JobEvaluation = apps.get_model("jobs", "JobEvaluation")
    CompanySummary = apps.get_model("jobs", "CompanySummary")
    ApplicationDoc = apps.get_model("documents", "ApplicationDoc")
    Application = apps.get_model("applications", "Application")

    groups = {}
    rows = JobPosting.objects.exclude(application_url="").values(
        "id",
        "raw_job__user_id",
        "application_url",
        "parsed_at",
    )
    for row in rows.iterator():
        normalized = normalize_url(row["application_url"])
        if normalized:
            groups.setdefault((row["raw_job__user_id"], normalized), []).append(row)

    for (_, normalized_url), postings in groups.items():
        posting_ids = [row["id"] for row in postings]
        if len(posting_ids) < 2:
            JobPosting.objects.filter(id=posting_ids[0]).update(application_url=normalized_url)
            continue

        protected_ids = set(
            Application.objects.filter(job_posting_id__in=posting_ids).values_list(
                "job_posting_id", flat=True
            )
        )
        evaluation_ids = dict(
            JobEvaluation.objects.filter(job_posting_id__in=posting_ids).values_list(
                "job_posting_id", "id"
            )
        )
        document_evaluation_ids = set(
            ApplicationDoc.objects.filter(
                job_evaluation_id__in=evaluation_ids.values()
            ).values_list("job_evaluation_id", flat=True)
        )
        summary_ids = set(
            CompanySummary.objects.filter(job_posting_id__in=posting_ids).values_list(
                "job_posting_id", flat=True
            )
        )

        ranker = partial(
            posting_rank,
            evaluation_ids=evaluation_ids,
            protected_ids=protected_ids,
            document_evaluation_ids=document_evaluation_ids,
            summary_ids=summary_ids,
        )
        survivor = max(postings, key=ranker)
        retained_ids = protected_ids or {survivor["id"]}
        JobPosting.objects.filter(id__in=retained_ids).update(application_url=normalized_url)
        JobPosting.objects.filter(id__in=posting_ids).exclude(id__in=retained_ids).delete()


class Migration(migrations.Migration):
    dependencies = [  # noqa: RUF012
        ("applications", "0002_alter_application_status"),
        ("documents", "0001_initial"),
        ("jobs", "0007_alter_jobposting_external_job_id"),
    ]

    operations = [  # noqa: RUF012
        migrations.RunPython(
            deduplicate_job_postings,
            reverse_code=migrations.RunPython.noop,
        )
    ]
