"""Prompt contract tests for OSS-model-friendly LLM calls."""

from __future__ import annotations

import pytest

from backend.agents.document_agent import (
    DocumentState,
    _build_cover_letter_prompt,
    _build_cv_tailor_prompt,
    _build_quality_check_prompt,
)
from backend.agents.evaluator_agent import (
    DimensionScores,
    EvaluatorState,
    _build_pass1_prompt,
    _build_pass2_prompt,
    _build_pass3_prompt,
)
from backend.agents.parser_agent import (
    JobPostingSchema,
    ParserState,
    _build_parse_prompt,
    embed_node,
    set_embedder_for_tests,
)
from backend.agents.research_agent import (
    ResearchState,
    _build_brief_prompt,
    _domain_matches_company_name,
    _parse_search_results,
)
from backend.config import Settings
from backend.db.models import EMBEDDING_DIM
from backend.db.models.user_profile import EMBEDDING_DIM as PROFILE_EMBEDDING_DIM
from backend.services.rapidapi_providers import jsearch, linkedin_fantastic

_LONG_CV_SENTINEL = "FULL_CV_SENTINEL_AFTER_OLD_6000_BOUNDARY"
_LONG_CV_TEXT = "A" * 6100 + _LONG_CV_SENTINEL


def _assert_common_prompt_contract(prompt: str) -> None:
    for expected in (
        "ROLE",
        "TASK",
        "IMPORTANT RULES",
        "GROUND TRUTH INPUT",
        "OUTPUT FORMAT",
        "VALIDATION CHECKLIST",
        "untrusted data",
    ):
        assert expected in prompt


def _assert_json_contract(prompt: str) -> None:
    _assert_common_prompt_contract(prompt)
    assert "Respond in this exact JSON format" in prompt
    assert "valid JSON only" in prompt
    assert "no markdown fences" in prompt


def _evaluator_state() -> EvaluatorState:
    return EvaluatorState(
        job_posting_id="00000000-0000-0000-0000-000000000001",
        user_id="00000000-0000-0000-0000-000000000002",
        job_title="Backend Engineer",
        job_description="Python services, PostgreSQL, and Kubernetes.",
        job_requirements=["Python", "PostgreSQL", "Kubernetes"],
        job_salary_min=3000,
        job_salary_max=5000,
        user_full_name="Test User",
        user_skills=["Python", "PostgreSQL"],
        user_experience_years=6,
        user_domain="software",
        user_values="Remote-first, learning culture",
        user_summary="Backend engineer focused on data platforms.",
        user_linkedin_url="https://linkedin.example/test-user",
        raw_cv_text=_LONG_CV_TEXT,
        pass1_notes="Strong Python evidence; Kubernetes is weaker.",
        pass2_critique="The first pass was slightly optimistic on Kubernetes.",
    )


def _document_state() -> DocumentState:
    return DocumentState(
        job_evaluation_id="00000000-0000-0000-0000-000000000003",
        user_id="00000000-0000-0000-0000-000000000004",
        job_title="Backend Engineer",
        company_name="Contoso",
        job_requirements=["Python", "SQL"],
        company_mission="Build reliable cloud systems.",
        company_values="Craft, clarity",
        company_culture="Remote-first and pragmatic.",
        company_summary="Contoso builds data tooling.",
        user_full_name="Test User",
        user_skills=["Python", "PostgreSQL"],
        user_experience_years=6,
        user_domain="software",
        user_summary="Backend engineer.",
        user_values="Craft and clarity.",
        user_linkedin_url="https://linkedin.example/test-user",
        raw_cv_text=_LONG_CV_TEXT,
        tailored_cv_text="SUMMARY\nBackend engineer with Python experience.",
        cover_letter_text="Dear Contoso hiring team,\nI am interested in the role.",
    )


def test_parser_prompt_has_strict_json_and_untrusted_input_contract() -> None:
    prompt = _build_parse_prompt(ParserState(raw_job_id="raw-1", raw_payload={"title": "Engineer"}))

    _assert_json_contract(prompt)
    assert "=== BEGIN RAW_JOB_JSON ===" in prompt
    assert "salary_min and salary_max are monthly USD integers" in prompt


def test_evaluator_prompts_have_rubrics_and_json_contracts() -> None:
    state = _evaluator_state()
    draft = DimensionScores(
        skills_match=7,
        seniority_fit=6,
        domain_alignment=8,
        compensation_fit=5,
    )
    revised = DimensionScores(
        skills_match=6,
        seniority_fit=6,
        domain_alignment=7,
        compensation_fit=5,
    )

    prompts = [
        _build_pass1_prompt(state),
        _build_pass2_prompt(state, draft),
        _build_pass3_prompt(state, draft, revised),
    ]

    for prompt in prompts:
        _assert_json_contract(prompt)
        assert "SCORING RUBRIC" in prompt
        assert "=== BEGIN USER_PROFILE ===" in prompt
        assert "=== BEGIN MASTER_CV ===" in prompt
        assert "Backend engineer focused on data platforms." in prompt
        assert _LONG_CV_SENTINEL in prompt
    assert "GOOD_FIT = score >= 6.5" in prompts[-1]


def test_research_prompt_requires_source_grounded_not_available_json() -> None:
    state = ResearchState(
        job_posting_id="00000000-0000-0000-0000-000000000005",
        company_name="Contoso",
        job_title="Backend Engineer",
    )
    prompt = _build_brief_prompt(state, "About Contoso")

    _assert_json_contract(prompt)
    assert "Not available" in prompt
    assert "=== BEGIN SCRAPED_CONTENT ===" in prompt


def test_research_company_domain_match_rejects_job_board_hosts() -> None:
    assert _domain_matches_company_name("https://contoso.com/careers", "Contoso") is True
    assert _domain_matches_company_name("https://www.openai.com", "Open AI") is True
    assert (
        _domain_matches_company_name("https://boards.greenhouse.io/contoso/jobs/1", "Contoso")
        is False
    )
    assert (
        _domain_matches_company_name("https://himalayas.app/companies/contoso", "Contoso") is False
    )


def test_research_parse_search_results_accepts_v1_and_v2_shapes() -> None:
    v1 = {
        "data": [
            {
                "title": "Contoso",
                "description": "Official site",
                "url": "https://contoso.com",
            }
        ]
    }
    v2 = {
        "data": {
            "web": [
                {
                    "title": "Fabrikam",
                    "description": "Official site",
                    "url": "https://fabrikam.com",
                }
            ]
        }
    }

    assert _parse_search_results(v1)[0].url == "https://contoso.com"
    assert _parse_search_results(v2)[0].url == "https://fabrikam.com"


def test_document_prompts_prevent_fabrication_and_define_output() -> None:
    state = _document_state()
    cv_prompt = _build_cv_tailor_prompt(state, requirements_block="- Python")
    cover_prompt = _build_cover_letter_prompt(state, requirements_block="- Python")
    qc_prompt = _build_quality_check_prompt(state)

    for prompt in (cv_prompt, cover_prompt, qc_prompt):
        _assert_common_prompt_contract(prompt)
        assert "No invented facts" in prompt or "DO NOT fabricate" in prompt
        assert "=== BEGIN USER_PROFILE ===" in prompt
        assert "=== BEGIN MASTER_CV ===" in prompt
        assert "Backend engineer." in prompt
        assert _LONG_CV_SENTINEL in prompt
        assert "No CV uploaded" not in prompt
        assert "User skills:" not in prompt
    assert "Plain text only" in cv_prompt
    assert "Plain text only" in cover_prompt
    _assert_json_contract(qc_prompt)


def test_missing_profile_fields_render_not_provided_in_full_context() -> None:
    evaluator_prompt = _build_pass1_prompt(
        EvaluatorState(
            job_posting_id="00000000-0000-0000-0000-000000000011",
            user_id="00000000-0000-0000-0000-000000000012",
            job_title="Backend Engineer",
            job_description="Python services.",
            job_requirements=["Python"],
        )
    )
    document_prompt = _build_cv_tailor_prompt(
        DocumentState(
            job_evaluation_id="00000000-0000-0000-0000-000000000013",
            user_id="00000000-0000-0000-0000-000000000014",
            job_title="Backend Engineer",
            company_name="Contoso",
            job_requirements=["Python"],
        ),
        requirements_block="- Python",
    )

    for prompt in (evaluator_prompt, document_prompt):
        assert "=== BEGIN USER_PROFILE ===" in prompt
        assert "=== BEGIN MASTER_CV ===" in prompt
        assert "Full name: Not provided" in prompt
        assert "Skills: Not provided" in prompt
        assert "Professional summary: Not provided" in prompt
        assert "Not provided" in prompt
        assert "No CV uploaded" not in prompt


def test_rapidapi_provider_prompts_are_allowlisted_json_contracts() -> None:
    for prompt in (jsearch.build_system_prompt(), linkedin_fantastic.build_system_prompt()):
        _assert_json_contract(prompt)
        assert "ALLOWED PATHS" in prompt
        assert "ALLOWED QUERY PARAMS" in prompt
        assert "Return one request only" in prompt


def test_embedding_defaults_match_pgvector_dimension() -> None:
    assert Settings.model_fields["LLM_EMBEDDING_DIM"].default == EMBEDDING_DIM
    assert EMBEDDING_DIM == 2048
    assert PROFILE_EMBEDDING_DIM == EMBEDDING_DIM


@pytest.mark.asyncio
async def test_parser_rejects_wrong_embedding_dimension() -> None:
    class _WrongDimEmbedder:
        async def aembed_query(self, text: str) -> list[float]:
            return [0.1]

    try:
        set_embedder_for_tests(_WrongDimEmbedder())
        state = ParserState(
            raw_job_id="00000000-0000-0000-0000-000000000006",
            raw_payload={},
            parsed=JobPostingSchema(
                title="Backend Engineer",
                company_name="Contoso",
                location="Remote",
                remote_flag=True,
                description="Python services.",
                requirements=["Python"],
                application_url="https://jobs.example",
            ),
        )

        result = await embed_node(state)

        assert result.embedding is None
    finally:
        set_embedder_for_tests(None)
