import { apiFetch, apiFetchEmpty } from './client';
import type { CvDownloadResult, CvUploadResult, Profile } from '$lib/types/profile';

export function getProfile(): Promise<Profile> {
	return apiFetch<Profile>(`/api/v1/profile`);
}

export function putProfile(body: Record<string, unknown>): Promise<Profile> {
	return apiFetch<Profile>(`/api/v1/profile`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});
}

/** Soft-deactivates the app user; caller should sign out and redirect. */
export function postDisableOwnAccount(): Promise<void> {
	return apiFetchEmpty(`/api/v1/profile/account/disable`, { method: 'POST' });
}

export async function signedProfileCvPdfUrl(): Promise<string> {
	const result = await apiFetch<CvDownloadResult>(`/api/v1/profile/cv-url`);
	return result.signed_url;
}

export async function uploadCvPdf(file: File): Promise<CvUploadResult> {
	const fd = new FormData();
	fd.append('file', file);
	return apiFetch<CvUploadResult>(`/api/v1/profile/cv`, { method: 'POST', body: fd });
}
