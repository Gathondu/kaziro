import { apiFetch, apiFetchMeta } from './client';
import { clampListLimit } from './limits';
import type { JobConfig } from '$lib/types/jobConfig';

export interface ListJobConfigsParams {
	cursor?: string | null;
	limit?: number;
	active_only?: boolean;
}

function qc(p: ListJobConfigsParams): string {
	const q = new URLSearchParams();
	if (p.cursor) q.set('cursor', p.cursor);
	if (p.limit != null) {
		q.set('limit', String(clampListLimit(p.limit)));
	}
	if (p.active_only) q.set('active_only', 'true');
	const s = q.toString();
	return s ? `?${s}` : '';
}

export async function listJobConfigs(
	params: ListJobConfigsParams
): Promise<{ items: JobConfig[]; nextCursor: string | null }> {
	const { data, nextCursor } = await apiFetchMeta<JobConfig[]>(`/api/v1/job-configs${qc(params)}`);
	return { items: data, nextCursor };
}

export function createJobConfig(body: Record<string, unknown>): Promise<JobConfig> {
	return apiFetch<JobConfig>(`/api/v1/job-configs`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});
}

export function updateJobConfig(id: string, body: Record<string, unknown>): Promise<JobConfig> {
	return apiFetch<JobConfig>(`/api/v1/job-configs/${id}`, {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	});
}

export function disableJobConfig(id: string): Promise<JobConfig> {
	return apiFetch<JobConfig>(`/api/v1/job-configs/${id}`, { method: 'DELETE' });
}

export function runJobConfigPipeline(id: string): Promise<{ task_id: string }> {
	return apiFetch<{ task_id: string }>(`/api/v1/job-configs/${id}/run`, { method: 'POST' });
}
