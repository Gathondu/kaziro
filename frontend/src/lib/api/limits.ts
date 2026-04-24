/**
 * Shared bounds for cursor-style list endpoints.
 *
 * Keep in sync with FastAPI ``Query(..., ge=1, le=100)`` on:
 * ``GET /api/v1/jobs``, ``GET /api/v1/applications``, ``GET /api/v1/job-configs``,
 * and ``GET /api/v1/admin/users``.
 */
export const API_LIST_MAX_LIMIT = 100;

/** Matches list endpoints’ ``Query(default=20, …)`` page size. */
export const API_LIST_DEFAULT_LIMIT = 20;

/** ``useJobConfigs`` — ``GET /job-configs`` list page size (≤ ``API_LIST_MAX_LIMIT``). */
export const API_LIST_JOB_CONFIGS_PAGE_LIMIT = 50;

/** ``useDashboard`` — applications sample fetch (≤ ``API_LIST_MAX_LIMIT``). */
export const API_LIST_DASHBOARD_APPLICATIONS_SAMPLE_LIMIT = 50;

export function clampListLimit(limit: number): number {
	return Math.min(Math.max(1, limit), API_LIST_MAX_LIMIT);
}

/** ``GET /api/v1/jobs`` — ``min_score`` query is ``ge=0, le=10``. */
export function clampMinScore(score: number): number {
	return Math.min(10, Math.max(0, score));
}
