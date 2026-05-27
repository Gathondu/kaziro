# Entity Relationship Diagram

**Status**: Active
**Last updated**: 2026-04-22
**Source**: Section 4 of [`Kaziro_Design_Document.pdf`](../../../Kaziro_Design_Document.pdf)
**Referenced from**: [`../03-data-model.md`](../03-data-model.md)

```mermaid
erDiagram
  users ||--|| user_profiles : has
  users ||--o{ job_search_configs : owns
  users ||--o{ raw_jobs : "fetched_for"
  users ||--o{ job_evaluations : "evaluated_for"
  users ||--o{ application_docs : owns
  users ||--o{ applications : owns

  job_search_configs ||--o{ raw_jobs : produces
  raw_jobs ||--o| job_postings : "parses_to"
  job_postings ||--o{ job_evaluations : "evaluated_as"
  job_postings ||--o| company_summaries : "summarised_by"
  job_evaluations ||--|| application_docs : generates
  application_docs ||--|| applications : "tracked_as"
  applications ||--o{ application_events : history

  users {
    uuid id PK
    text email UK
    text subscription_tier
    bool is_active
    timestamptz created_at
  }

  user_profiles {
    uuid id PK
    uuid user_id FK
    text full_name
    text professional_summary
    text[] skills
    int experience_years
    text domain
    text values_statement
    text cv_storage_path
    text linkedin_url
    vector profile_embedding "2048"
  }

  job_search_configs {
    uuid id PK
    uuid user_id FK
    text[] keywords
    text location
    bool remote_only
    int salary_min
    int salary_max
    text[] employment_types
    text fetch_schedule_cron
    bool is_active
  }

  raw_jobs {
    uuid id PK
    uuid user_id FK
    uuid config_id FK
    text source_api
    jsonb raw_payload
    timestamptz fetched_at
    enum parse_status
    int retry_count
  }

  job_postings {
    uuid id PK
    uuid raw_job_id FK
    text external_job_id UK
    text title
    text company_name
    text company_website
    text location
    bool remote_flag
    int salary_min
    int salary_max
    text employment_type
    text description
    text[] requirements
    text application_url
    date posted_date
    vector description_embedding "2048"
    timestamptz parsed_at
  }

  job_evaluations {
    uuid id PK
    uuid job_posting_id FK
    uuid user_id FK
    jsonb pass1_scores
    text pass1_notes
    text pass2_critique
    jsonb pass2_revised_scores
    text final_classification
    text final_feedback
    numeric overall_score
    timestamptz evaluated_at
  }

  company_summaries {
    uuid id PK
    uuid job_posting_id FK
    text company_name
    text mission
    text values
    text culture
    text tech_stack
    text team_size_approx
    text recent_news
    text raw_scraped_content
    text ai_summary
    timestamptz summary_generated_at
  }

  application_docs {
    uuid id PK
    uuid job_evaluation_id FK
    uuid user_id FK
    text tailored_cv_text
    text cover_letter_text
    text cv_pdf_path
    text cover_letter_pdf_path
    text generation_model
    bool quality_passed
    text quality_notes
    timestamptz last_edited_at
  }

  applications {
    uuid id PK
    uuid application_doc_id FK
    uuid user_id FK
    uuid job_posting_id FK
    enum status
    timestamptz applied_at
    text notes
  }

  application_events {
    uuid id PK
    uuid application_id FK
    text event_type
    timestamptz event_date
    text notes
  }
```

## Foreign-key cascade rules

| FK                                                | On delete       |
| ------------------------------------------------- | --------------- |
| Any `user_id` →  `users.id`                       | `CASCADE`       |
| `raw_jobs.config_id` → `job_search_configs.id`    | `CASCADE`       |
| `job_postings.raw_job_id` → `raw_jobs.id`         | `RESTRICT`      |
| `job_evaluations.job_posting_id` → `job_postings.id` | `CASCADE`    |
| `company_summaries.job_posting_id` → `job_postings.id` | `CASCADE`  |
| `application_docs.job_evaluation_id` → `job_evaluations.id` | `CASCADE` |
| `applications.application_doc_id` → `application_docs.id` | `RESTRICT` |
| `application_events.application_id` → `applications.id`  | `CASCADE`  |

`RESTRICT` is used where deletion would lose audit-quality data; cascading
deletes propagate from `users` (account deletion) and from upstream
pipeline rows. Account deletion runs through the dedicated soft-delete +
async-purge flow described in
[`../07-security.md`](../07-security.md#3-data-privacy).
