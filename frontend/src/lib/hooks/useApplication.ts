import { browser } from '$app/environment';
import { derived } from 'svelte/store';
import { page } from '$app/stores';
import { createMutation, createQuery, useQueryClient } from '@tanstack/svelte-query';
import {
	LIST_APPLICATIONS_MAX_LIMIT,
	createApplication,
	getApplication,
	listApplications,
	markApplicationSent,
	signedCoverLetterUrl,
	signedCvUrl,
	updateApplicationDocs,
	updateApplicationStatus
} from '$lib/api/applications';
import { markJobNotInterested } from '$lib/api/jobs';
import type { Application } from '$lib/types/applications';
import type { ApplicationStatus } from '$lib/types/enums';
import type { JobEvaluation } from '$lib/types/jobs';

export function useApplicationFromRoute() {
	const options = derived(page, ($p) => {
		const id = $p.params.id;
		return {
			queryKey: ['application', id] as const,
			queryFn: () => getApplication(String(id)),
			enabled: browser && Boolean(id),
			staleTime: 5 * 60_000
		};
	});
	return createQuery(options);
}

export function useApplicationFromQueryParam(paramName: string) {
	const options = derived(page, ($p) => {
		const id = $p.url.searchParams.get(paramName) ?? '';
		return {
			queryKey: ['application', id] as const,
			queryFn: () => getApplication(id),
			enabled: browser && Boolean(id),
			staleTime: 5 * 60_000
		};
	});
	return createQuery(options);
}

export function useCreateApplication() {
	const qc = useQueryClient();
	return createMutation<Application, Error, string>({
		mutationFn: (jobPostingId: string) => createApplication(jobPostingId),
		onSuccess: (_data, jobPostingId) => {
			void qc.invalidateQueries({ queryKey: ['applications'] });
			void qc.invalidateQueries({ queryKey: ['job', jobPostingId, 'evaluation'] });
		}
	});
}

export function useMarkJobNotInterested() {
	const qc = useQueryClient();
	return createMutation<JobEvaluation, Error, string>({
		mutationFn: (jobPostingId: string) => markJobNotInterested(jobPostingId),
		onSuccess: (_data, jobPostingId) => {
			void qc.invalidateQueries({ queryKey: ['job', jobPostingId] });
			void qc.invalidateQueries({ queryKey: ['job', jobPostingId, 'evaluation'] });
			void qc.invalidateQueries({ queryKey: ['applications'] });
			void qc.invalidateQueries({ queryKey: ['jobs'] });
			void qc.invalidateQueries({ queryKey: ['dashboard'] });
		}
	});
}

type UpdateDocsVars = {
	id: string;
	/** When set, refetches job evaluation after doc save (e.g. job detail modal). */
	jobPostingId?: string;
	body: { tailored_cv_text?: string | null; cover_letter_text?: string | null };
};

export function useUpdateApplicationDocs() {
	const qc = useQueryClient();
	return createMutation<Application, Error, UpdateDocsVars>({
		mutationFn: (args: UpdateDocsVars) => updateApplicationDocs(args.id, args.body),
		onSuccess: (_data, args) => {
			void qc.invalidateQueries({ queryKey: ['application', args.id] });
			void qc.invalidateQueries({ queryKey: ['applications'] });
			if (args.jobPostingId) {
				void qc.invalidateQueries({ queryKey: ['job', args.jobPostingId, 'evaluation'] });
			}
		}
	});
}

export function useMarkApplicationSent() {
	const qc = useQueryClient();
	return createMutation<Application, Error, string>({
		mutationFn: (id: string) => markApplicationSent(id),
		onSuccess: (_data, id) => {
			void qc.invalidateQueries({ queryKey: ['application', id] });
			void qc.invalidateQueries({ queryKey: ['applications'] });
		}
	});
}

type UpdateStatusVars = { id: string; status: ApplicationStatus };

export function useUpdateApplicationStatus() {
	const qc = useQueryClient();
	return createMutation<Application, Error, UpdateStatusVars>({
		mutationFn: (args: UpdateStatusVars) => updateApplicationStatus(args.id, args.status),
		onSuccess: (_data, args) => {
			void qc.invalidateQueries({ queryKey: ['application', args.id] });
			void qc.invalidateQueries({ queryKey: ['applications'] });
		}
	});
}

export function useApplicationsBoard() {
	return createQuery({
		queryKey: ['applications', 'board'],
		queryFn: async (): Promise<Application[]> => {
			const { items } = await listApplications({ limit: LIST_APPLICATIONS_MAX_LIMIT });
			return items;
		},
		staleTime: 5 * 60_000
	});
}

export interface ApplicationPdfUrls {
	cvUrl: string | null;
	coverLetterUrl: string | null;
}

export function useApplicationPdfUrlsFromQueryParam(paramName: string) {
	const options = derived(page, ($p) => {
		const id = $p.url.searchParams.get(paramName) ?? '';
		return {
			queryKey: ['application', id, 'pdf-urls'] as const,
			queryFn: async (): Promise<ApplicationPdfUrls> => {
				const [cvUrl, coverLetterUrl] = await Promise.all([
					signedCvUrl(id),
					signedCoverLetterUrl(id)
				]);
				return { cvUrl, coverLetterUrl };
			},
			enabled: browser && Boolean(id),
			staleTime: 10 * 60_000
		};
	});
	return createQuery(options);
}
