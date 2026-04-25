import { createQuery } from '@tanstack/svelte-query';
import { listApplications } from '$lib/api/applications';
import {
	API_LIST_MAX_LIMIT
} from '$lib/api/limits';
import { listJobs } from '$lib/api/jobs';
import type { Application } from '$lib/types/applications';
import type { JobPosting } from '$lib/types/jobs';

export interface DashboardSnapshot {
	jobsTotal: number;
	goodFitUninteracted: number;
	applicationsDraft: number;
	sentCount: number;
	recent: { id: string; label: string; at: string }[];
}

async function listAllJobs(): Promise<JobPosting[]> {
	let cursor: string | null = null;
	const all: JobPosting[] = [];
	for (;;) {
		const page = await listJobs({ limit: API_LIST_MAX_LIMIT, cursor });
		all.push(...page.items);
		if (!page.nextCursor) break;
		cursor = page.nextCursor;
	}
	return all;
}

async function listAllGoodFitJobs(): Promise<JobPosting[]> {
	let cursor: string | null = null;
	const all: JobPosting[] = [];
	for (;;) {
		const page = await listJobs({ limit: API_LIST_MAX_LIMIT, cursor, classification: ['GOOD_FIT'] });
		all.push(...page.items);
		if (!page.nextCursor) break;
		cursor = page.nextCursor;
	}
	return all;
}

async function listAllApplications(): Promise<Application[]> {
	let cursor: string | null = null;
	const all: Application[] = [];
	for (;;) {
		const page = await listApplications({ limit: API_LIST_MAX_LIMIT, cursor });
		all.push(...page.items);
		if (!page.nextCursor) break;
		cursor = page.nextCursor;
	}
	return all;
}

export function useDashboard() {
	return createQuery({
		queryKey: ['dashboard'],
		staleTime: 5 * 60_000,
		queryFn: async (): Promise<DashboardSnapshot> => {
			const [allJobs, allGoodFitJobs, allApplications] = await Promise.all([
				listAllJobs(),
				listAllGoodFitJobs(),
				listAllApplications()
			]);
			const interactedJobIds = new Set(allApplications.map((a) => a.job_posting_id));
			const jobsTotal = allJobs.length;
			const goodFitUninteracted = allGoodFitJobs.filter((job) => !interactedJobIds.has(job.id)).length;
			const applicationsDraft = allApplications.filter((a) => a.status === 'DRAFT').length;
			const sentCount = allApplications.filter((a) => a.status === 'SENT').length;
			const recent = allApplications.slice(0, 12).map((a) => ({
				id: a.id,
				label: `${a.job_posting?.title ?? 'Application'} — ${a.status}`,
				at: a.updated_at
			}));
			return {
				jobsTotal,
				goodFitUninteracted,
				applicationsDraft,
				sentCount,
				recent
			};
		}
	});
}
