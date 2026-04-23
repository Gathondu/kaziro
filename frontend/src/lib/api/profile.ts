import { getPublicApiUrl } from '$lib/env/public';
import { apiFetch } from './client';
import { getJwt } from './auth';
import type { CvUploadResult, Profile } from '$lib/types/profile';

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

export async function uploadCvPdf(file: File): Promise<CvUploadResult> {
	const token = getJwt();
	const base = getPublicApiUrl();
	const fd = new FormData();
	fd.append('file', file);
	const res = await fetch(`${base}/api/v1/profile/cv`, {
		method: 'POST',
		headers: token ? { Authorization: `Bearer ${token}` } : {},
		body: fd
	});
	const json = (await res.json()) as {
		data: CvUploadResult | null;
		error: { code: string; message: string } | null;
	};
	if (!res.ok || json.error || !json.data) {
		throw new Error(json.error?.message ?? 'Upload failed');
	}
	return json.data;
}
