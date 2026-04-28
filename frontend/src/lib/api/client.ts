import { goto } from '$app/navigation';
import { browser } from '$app/environment';
import { getPublicApiUrl } from '$lib/env/public';
import { ApiError } from './errors';
import { getJwt, signOutEverywhere, waitForAuthReady } from './auth';
import type { Envelope } from '$lib/types/api';
import { logger } from '$lib/utils/logger';

function joinUrl(path: string): string {
	if (path.startsWith('http')) return path;
	const base = getPublicApiUrl();
	const p = path.startsWith('/') ? path : `/${path}`;
	return `${base}${p}`;
}

function isRecord(v: unknown): v is Record<string, unknown> {
	return typeof v === 'object' && v !== null;
}

async function readJsonBody(res: Response, path: string): Promise<unknown> {
	const ct = res.headers.get('content-type') ?? '';
	const raw = await res.text();
	if (!ct.includes('application/json')) {
		throw new ApiError('Invalid non-JSON response from API', {
			code: 'invalid_response',
			status: res.status,
			details: {
				path,
				contentType: ct,
				bodyPreview: raw.slice(0, 120)
			}
		});
	}
	try {
		return JSON.parse(raw) as unknown;
	} catch {
		throw new ApiError('Invalid JSON response from API', {
			code: 'invalid_response',
			status: res.status,
			details: {
				path,
				contentType: ct,
				bodyPreview: raw.slice(0, 120)
			}
		});
	}
}

export function parseErrorBody(json: unknown, status: number): ApiError {
	if (!isRecord(json)) {
		return new ApiError('Request failed', { code: 'http_error', status });
	}
	const err = json.error;
	if (!isRecord(err) || typeof err.message !== 'string' || typeof err.code !== 'string') {
		return new ApiError('Request failed', { code: 'http_error', status });
	}
	return new ApiError(err.message, {
		code: err.code,
		status,
		details: 'details' in err ? err.details : undefined,
		traceId: typeof err.trace_id === 'string' ? err.trace_id : undefined
	});
}

/** App user disabled in DB while Supabase session is still valid — end client session. */
export async function flushSessionIfDeactivatedAccount(
	status: number,
	json: unknown
): Promise<boolean> {
	if (!browser || status !== 403 || !isRecord(json)) return false;
	const err = json.error;
	if (!isRecord(err) || err.code !== 'user_deactivated') return false;
	await signOutEverywhere();
	await goto('/login?deactivated=1');
	return true;
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
	if (browser) {
		await waitForAuthReady();
	}
	const headers = new Headers(init.headers);
	const token = getJwt();
	if (token) {
		headers.set('Authorization', `Bearer ${token}`);
	}
	if (!headers.has('Accept')) {
		headers.set('Accept', 'application/json');
	}

	const res = await fetch(joinUrl(path), { ...init, headers });

	if (res.status === 401 && browser) {
		await signOutEverywhere();
		const next = encodeURIComponent(`${window.location.pathname}${window.location.search}`);
		await goto(`/login?next=${next}`);
	}

	const ct = res.headers.get('content-type') ?? '';
	const isJson = ct.includes('application/json');
	const json = isJson ? await readJsonBody(res, path) : null;

	if (!res.ok) {
		if (isJson && isRecord(json)) {
			await flushSessionIfDeactivatedAccount(res.status, json);
			throw parseErrorBody(json, res.status);
		}
		throw new ApiError(res.statusText || 'Request failed', {
			code: 'http_error',
			status: res.status
		});
	}

	if (!isJson || json === null) {
		throw new ApiError('Empty response', { code: 'invalid_response', status: res.status });
	}

	const envelope = json as Envelope<T>;
	if (envelope.error) {
		throw new ApiError(envelope.error.message, {
			code: envelope.error.code,
			status: res.status,
			details: envelope.error.details,
			traceId: envelope.error.trace_id
		});
	}
	if (envelope.data === null || envelope.data === undefined) {
		logger.warn('apiFetch.success_without_data', { path });
	}
	return envelope.data as T;
}

export async function apiFetchMeta<T>(
	path: string,
	init?: RequestInit
): Promise<{ data: T; nextCursor: string | null }> {
	if (browser) {
		await waitForAuthReady();
	}
	const headers = new Headers(init?.headers);
	const token = getJwt();
	if (token) {
		headers.set('Authorization', `Bearer ${token}`);
	}
	if (!headers.has('Accept')) {
		headers.set('Accept', 'application/json');
	}

	const res = await fetch(joinUrl(path), { ...init, headers });

	if (res.status === 401 && browser) {
		await signOutEverywhere();
		const next = encodeURIComponent(`${window.location.pathname}${window.location.search}`);
		await goto(`/login?next=${next}`);
	}

	const json = await readJsonBody(res, path);
	if (!res.ok) {
		if (isRecord(json)) {
			await flushSessionIfDeactivatedAccount(res.status, json);
			throw parseErrorBody(json, res.status);
		}
		throw new ApiError(res.statusText || 'Request failed', {
			code: 'http_error',
			status: res.status
		});
	}

	const envelope = json as Envelope<T>;
	if (envelope.error) {
		throw new ApiError(envelope.error.message, {
			code: envelope.error.code,
			status: res.status,
			details: envelope.error.details
		});
	}
	return {
		data: envelope.data as T,
		nextCursor: envelope.meta?.next_cursor ?? null
	};
}

/** Follow auth redirect for PDF downloads; returns final signed URL. */
/** For ``204 No Content`` responses (e.g. DELETE). */
export async function apiFetchEmpty(path: string, init: RequestInit = {}): Promise<void> {
	if (browser) {
		await waitForAuthReady();
	}
	const headers = new Headers(init.headers);
	const token = getJwt();
	if (token) {
		headers.set('Authorization', `Bearer ${token}`);
	}
	const res = await fetch(joinUrl(path), { ...init, headers });

	if (res.status === 401 && browser) {
		await signOutEverywhere();
		const next = encodeURIComponent(`${window.location.pathname}${window.location.search}`);
		await goto(`/login?next=${next}`);
	}

	if (res.status === 204) {
		return;
	}

	const ct = res.headers.get('content-type') ?? '';
	if (ct.includes('application/json')) {
		const json = await readJsonBody(res, path);
		if (isRecord(json) && json.error && isRecord(json.error)) {
			await flushSessionIfDeactivatedAccount(res.status, json);
			throw parseErrorBody(json, res.status);
		}
	}
	if (!res.ok) {
		throw new ApiError(res.statusText || 'Request failed', {
			code: 'http_error',
			status: res.status
		});
	}
}

export async function resolveAuthenticatedRedirect(path: string): Promise<string> {
	if (browser) {
		await waitForAuthReady();
	}
	const headers = new Headers();
	const token = getJwt();
	if (token) {
		headers.set('Authorization', `Bearer ${token}`);
	}
	const res = await fetch(joinUrl(path), { headers, redirect: 'manual' });
	if (res.status === 302 || res.status === 301) {
		const loc = res.headers.get('Location');
		if (loc) return loc;
	}
	if (!res.ok) {
		const text = await res.text();
		throw new ApiError(text || 'Download failed', { code: 'download_failed', status: res.status });
	}
	return res.url;
}
