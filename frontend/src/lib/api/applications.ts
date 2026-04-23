import { apiFetch, apiFetchEmpty, apiFetchMeta, resolveAuthenticatedRedirect } from './client';
import type { Application, ApplicationDetail } from '$lib/types/applications';
import type { ApplicationStatus } from '$lib/types/enums';

export interface ListApplicationsParams {
	cursor?: string | null;
	limit?: number;
	status?: ApplicationStatus | null;
}

function appsQuery(p: ListApplicationsParams): string {
	const q = new URLSearchParams();
	if (p.cursor) q.set('cursor', p.cursor);
	if (p.limit != null) q.set('limit', String(p.limit));
	if (p.status) q.set('status', p.status);
	const s = q.toString();
	return s ? `?${s}` : '';
}

export async function listApplications(
	params: ListApplicationsParams
): Promise<{ items: Application[]; nextCursor: string | null }> {
	const { data, nextCursor } = await apiFetchMeta<Application[]>(
		`/api/v1/applications${appsQuery(params)}`
	);
	return { items: data, nextCursor };
}

export function getApplication(id: string): Promise<ApplicationDetail> {
	return apiFetch<ApplicationDetail>(`/api/v1/applications/${id}`);
}

export function createApplication(jobPostingId: string): Promise<Application> {
	return apiFetch<Application>(`/api/v1/applications`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ job_posting_id: jobPostingId })
	});
}

export function patchApplicationNotes(id: string, notes: string | null): Promise<Application> {
	return apiFetch<Application>(`/api/v1/applications/${id}`, {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ notes })
	});
}

export function updateApplicationDocs(
	id: string,
	body: { tailored_cv_text?: string | null; cover_letter_text?: string | null }
): Promise<Application> {
	return apiFetch<Application>(`/api/v1/applications/${id}/docs`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});
}

export function updateApplicationStatus(
	id: string,
	status: ApplicationStatus
): Promise<Application> {
	return apiFetch<Application>(`/api/v1/applications/${id}/status`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ status })
	});
}

export function markApplicationSent(id: string): Promise<Application> {
	return apiFetch<Application>(`/api/v1/applications/${id}/mark-sent`, {
		method: 'POST'
	});
}

export function deleteApplication(id: string): Promise<void> {
	return apiFetchEmpty(`/api/v1/applications/${id}`, { method: 'DELETE' });
}

export function signedCvUrl(applicationId: string): Promise<string> {
	return resolveAuthenticatedRedirect(`/api/v1/applications/${applicationId}/cv.pdf`);
}

export function signedCoverLetterUrl(applicationId: string): Promise<string> {
	return resolveAuthenticatedRedirect(`/api/v1/applications/${applicationId}/cover-letter.pdf`);
}
