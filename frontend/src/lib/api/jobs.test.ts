import { describe, expect, it, vi } from 'vitest';
import { importJobUrl } from './jobs';
import { apiFetch } from './client';

vi.mock('./client', () => ({
	apiFetch: vi.fn()
}));

describe('jobs api', () => {
	it('posts pasted job URLs to the import endpoint', async () => {
		vi.mocked(apiFetch).mockResolvedValueOnce({ task_id: 'task-1', duplicate: false });

		const result = await importJobUrl({ url: 'https://jobs.example.com/role' });

		expect(result.task_id).toBe('task-1');
		expect(apiFetch).toHaveBeenCalledWith('/api/v1/jobs/import-url', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ url: 'https://jobs.example.com/role' })
		});
	});
});
