import { apiFetch, apiFetchMeta, resolveAuthenticatedRedirect } from './client';
import { clampListLimit, clampMinScore } from './limits';
import type { Classification } from '$lib/types/enums';
import type { JobEvaluation, JobPosting, TriggerEvaluationBody } from '$lib/types/jobs';

export interface ListJobsParams {
	cursor?: string | null;
	limit?: number;
	classification?: Classification[];
	min_score?: number;
	remote_only?: boolean;
	posted_after?: string;
	keyword?: string | null;
}

function toSearch(params: ListJobsParams): string {
	const q = new URLSearchParams();
	if (params.cursor) q.set('cursor', params.cursor);
	if (params.limit != null) {
		q.set('limit', String(clampListLimit(params.limit)));
	}
	for (const c of params.classification ?? []) {
		q.append('classification', c);
	}
	if (params.min_score != null) {
		q.set('min_score', String(clampMinScore(params.min_score)));
	}
	if (params.remote_only != null) q.set('remote_only', String(params.remote_only));
	if (params.posted_after) q.set('posted_after', params.posted_after);
	if (params.keyword) q.set('keyword', params.keyword);
	const s = q.toString();
	return s ? `?${s}` : '';
}

export async function listJobs(
	params: ListJobsParams
): Promise<{ items: JobPosting[]; nextCursor: string | null }> {
	const { data, nextCursor } = await apiFetchMeta<JobPosting[]>(`/api/v1/jobs${toSearch(params)}`);
	return { items: data, nextCursor };
}

export function getJob(jobId: string): Promise<JobPosting> {
	return apiFetch<JobPosting>(`/api/v1/jobs/${jobId}`);
}

export function getJobEvaluation(jobId: string): Promise<JobEvaluation> {
	return apiFetch<JobEvaluation>(`/api/v1/jobs/${jobId}/evaluation`);
}

export function triggerJobEvaluation(jobId: string): Promise<TriggerEvaluationBody> {
	return apiFetch<TriggerEvaluationBody>(`/api/v1/jobs/${jobId}/trigger-evaluation`, {
		method: 'POST'
	});
}

export function markJobNotInterested(jobId: string): Promise<JobEvaluation> {
	return apiFetch<JobEvaluation>(`/api/v1/jobs/${jobId}/mark-not-interested`, {
		method: 'POST'
	});
}

export type RegenerateDocumentsPart = 'cv' | 'cover_letter';

export function regenerateJobDocuments(
	jobId: string,
	options?: { part?: RegenerateDocumentsPart }
): Promise<TriggerEvaluationBody> {
	const body = JSON.stringify(options?.part != null ? { part: options.part } : {});
	return apiFetch<TriggerEvaluationBody>(`/api/v1/jobs/${jobId}/regenerate-documents`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body
	});
}

export function signedJobCvPdfUrl(jobPostingId: string): Promise<string> {
	return resolveAuthenticatedRedirect(`/api/v1/jobs/${jobPostingId}/cv.pdf`);
}

export function signedJobCoverLetterPdfUrl(jobPostingId: string): Promise<string> {
	return resolveAuthenticatedRedirect(`/api/v1/jobs/${jobPostingId}/cover-letter.pdf`);
}
