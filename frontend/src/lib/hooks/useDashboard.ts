import { createQuery } from '@tanstack/svelte-query';
import { listApplications } from '$lib/api/applications';
import { listJobs } from '$lib/api/jobs';

export interface DashboardSnapshot {
	jobsSample: number;
	goodFitSample: number;
	applicationsTotalSample: number;
	sentCount: number;
	recent: { id: string; label: string; at: string }[];
}

export function useDashboard() {
	return createQuery({
		queryKey: ['dashboard'],
		staleTime: 30_000,
		queryFn: async (): Promise<DashboardSnapshot> => {
			const [jobsPage, goodPage, appsPage] = await Promise.all([
				listJobs({ limit: 100 }),
				listJobs({ limit: 100, classification: ['GOOD_FIT'] }),
				listApplications({ limit: 50 })
			]);
			const sentCount = appsPage.items.filter((a) => a.status === 'SENT').length;
			const recent = appsPage.items.slice(0, 12).map((a) => ({
				id: a.id,
				label: `${a.job_posting?.title ?? 'Application'} — ${a.status}`,
				at: a.updated_at
			}));
			return {
				jobsSample: jobsPage.items.length,
				goodFitSample: goodPage.items.length,
				applicationsTotalSample: appsPage.items.length,
				sentCount,
				recent
			};
		}
	});
}
