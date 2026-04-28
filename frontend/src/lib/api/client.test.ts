import { describe, it, expect, vi, afterEach } from 'vitest';
import { apiFetch } from './client';
import { ApiError } from './errors';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));
vi.mock('$app/environment', () => ({ browser: true }));
vi.mock('$env/dynamic/public', () => ({
	env: { PUBLIC_API_URL: 'http://localhost:8000' }
}));

vi.mock('./auth', () => ({
	getJwt: () => 'test-token',
	signOutEverywhere: vi.fn(),
	waitForAuthReady: vi.fn().mockResolvedValue(undefined)
}));

describe('apiFetch', () => {
	afterEach(() => {
		vi.restoreAllMocks();
	});

	it('returns data on success', async () => {
		vi.stubGlobal(
			'fetch',
			vi.fn().mockResolvedValue({
				ok: true,
				headers: new Headers({ 'content-type': 'application/json' }),
				json: async () => ({ data: { ok: true }, meta: null, error: null })
			})
		);
		const out = await apiFetch<{ ok: boolean }>('/api/v1/profile');
		expect(out.ok).toBe(true);
	});

	it('throws ApiError on 401', async () => {
		const { goto } = await import('$app/navigation');
		vi.stubGlobal(
			'fetch',
			vi.fn().mockResolvedValue({
				ok: false,
				status: 401,
				headers: new Headers({ 'content-type': 'application/json' }),
				json: async () => ({
					data: null,
					meta: null,
					error: { code: 'unauthorized', message: 'nope' }
				})
			})
		);
		await expect(apiFetch('/api/v1/jobs')).rejects.toBeInstanceOf(ApiError);
		expect(goto).toHaveBeenCalled();
	});

	it('throws ApiError on envelope error', async () => {
		vi.stubGlobal(
			'fetch',
			vi.fn().mockResolvedValue({
				ok: true,
				status: 200,
				headers: new Headers({ 'content-type': 'application/json' }),
				json: async () => ({
					data: null,
					meta: null,
					error: { code: 'internal_server_error', message: 'boom' }
				})
			})
		);
		await expect(apiFetch('/api/v1/jobs')).rejects.toMatchObject({
			code: 'internal_server_error'
		});
	});
});
