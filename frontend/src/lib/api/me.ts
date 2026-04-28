import { browser } from '$app/environment';
import { getPublicApiUrl } from '$lib/env/public';
import { ApiError } from './errors';
import { apiFetch, parseErrorBody } from './client';

export type MeResponse = { user_id: string };

export function getMe(): Promise<MeResponse> {
	return apiFetch<MeResponse>('/api/v1/me');
}

/**
 * Verify Kaziro app account using a freshly issued access token (store JWT may lag).
 * On deactivated account: clears Supabase session and throws {@link ApiError} with
 * code `user_deactivated` (no redirect — caller stays on login for inline error).
 */
export async function assertAppAccountWithAccessToken(accessToken: string): Promise<MeResponse> {
	const base = getPublicApiUrl();
	const res = await fetch(`${base}/api/v1/me`, {
		method: 'GET',
		headers: {
			Authorization: `Bearer ${accessToken}`,
			Accept: 'application/json'
		}
	});
	const ct = res.headers.get('content-type') ?? '';
	if (!ct.includes('application/json')) {
		const bodyPreview = (await res.text()).slice(0, 120);
		throw new ApiError('Invalid non-JSON response from API', {
			code: 'invalid_response',
			status: res.status,
			details: {
				base,
				contentType: ct,
				bodyPreview
			}
		});
	}
	const json = (await res.json()) as unknown;
	if (res.status === 403 && browser) {
		const err =
			json && typeof json === 'object' && 'error' in json
				? (json as { error?: unknown }).error
				: null;
		if (
			err &&
			typeof err === 'object' &&
			'code' in err &&
			(err as { code: string }).code === 'user_deactivated'
		) {
			const { signOutEverywhere } = await import('./auth');
			await signOutEverywhere();
			throw parseErrorBody(json, res.status);
		}
	}
	if (!res.ok) {
		throw parseErrorBody(json, res.status);
	}
	if (typeof json !== 'object' || json === null || !('data' in json)) {
		throw new ApiError('Invalid response', { code: 'invalid_response', status: res.status });
	}
	const data = (json as { data: MeResponse | null }).data;
	if (data === null || typeof data.user_id !== 'string') {
		throw new ApiError('Invalid response', { code: 'invalid_response', status: res.status });
	}
	return data;
}
