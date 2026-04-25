# JSearch API — RapidAPI

This document mirrors the **JSearch** product on RapidAPI
(`jsearch.p.rapidapi.com`). It is embedded in the backend prompt that builds
RapidAPI query parameters. Keep it aligned with the **Endpoints** tab when the
provider changes.

## HTTP basics

- **Scheme**: `https`
- **Host**: value of the `X-RapidAPI-Host` header — must match your
  RapidAPI subscription (typically `jsearch.p.rapidapi.com`).
- **Method**: `GET` for search endpoints.
- **Headers** (required on every request):
  - `X-RapidAPI-Key`: your RapidAPI application key.
  - `X-RapidAPI-Host`: same host as in the URL hostname.
  - `Accept: application/json`
- **Full URL shape**: `https://<RAPIDAPI_HOST>/<path>?<query>`

## Path

Use exactly:

| Path | Meaning |
|------|---------|
| `search` | Main job search endpoint |

Example:

`GET /search?query=developer%20jobs%20in%20chicago&page=1&num_pages=1&country=us&date_posted=all`

## Query parameters (JSearch semantics)

- **`query`** (required, string): free-form jobs query. Include title and
  location in natural language (e.g. `data engineer jobs in berlin`).
- **`page`** (optional, integer): first page to return. Range `1-50`.
  Default `1`.
- **`num_pages`** (optional, integer): number of pages to fetch starting at
  `page`. Range `1-20`. Default `1`.
- **`country`** (optional, string): ISO-3166-1 alpha-2 country code
  (e.g. `us`, `de`, `gb`).
- **`language`** (optional, string): ISO-639 language code.
- **`location`** (optional, string): search location/uule-like hint.
- **`date_posted`** (optional, enum): one of `all`, `today`, `3days`,
  `week`, `month`. Default `all`.
- **`work_from_home`** (optional, boolean): remote-only jobs.
- **`employment_types`** (optional, string): comma-separated list of
  `FULLTIME,CONTRACTOR,PARTTIME,INTERN`.
- **`job_requirements`** (optional, string): comma-separated list from
  `under_3_years_experience,more_than_3_years_experience,no_experience,no_degree`.
- **`radius`** (optional, number): search radius in km.
- **`exclude_job_publishers`** (optional, string): comma-separated publisher
  names to exclude.
- **`fields`** (optional, string): field projection list
  (e.g. `employer_name,job_publisher,job_title,job_country`).

## Response body

The JSON shape can vary by endpoint revision. Common patterns:

- An object with a **`data`** array of jobs (most common), or
- A top-level **array** of jobs, or
- An object with **`items`** / **`jobs`** array.

Each job object should include at least one stable identifier, usually `job_id`.
Downstream code also accepts `id`, `jobId`, `external_id`, `url`, or `job_url`.

## Operational notes

- Build a natural-language `query` from keywords and location.
- Use `work_from_home=true` when remote-only is requested.
- Prefer `num_pages=1` for lower quota usage unless larger fetches are needed.
- Use `country` only when a clear country code can be inferred.
