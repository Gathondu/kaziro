import { browser } from '$app/environment';
import { derived } from 'svelte/store';
import { page } from '$app/stores';
import {
	createInfiniteQuery,
	createMutation,
	createQuery,
	useQueryClient
} from '@tanstack/svelte-query';
import { API_LIST_DEFAULT_LIMIT } from '$lib/api/limits';
import {
	getJob,
	getJobEvaluation,
	listJobs,
	regenerateJobDocuments,
	triggerJobEvaluation,
	type ListJobsParams,
	type RegenerateDocumentsPart
} from '$lib/api/jobs';
import type { TriggerEvaluationBody } from '$lib/types/jobs';
import type { Classification } from '$lib/types/enums';

function classificationFromFitParam(fit: string | null): Classification[] | undefined {
	if (fit === 'GOOD_FIT' || fit === 'MAYBE' || fit === 'REJECT') {
		return [fit];
	}
	return undefined;
}

export type JobsFilter = Omit<ListJobsParams, 'cursor'>;

function jobFiltersFromPage(): JobsFilter {
	const s = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null;
	if (!s) {
		return { limit: API_LIST_DEFAULT_LIMIT };
	}
	const keyword = s.get('q') ?? '';
	const postedAfter = s.get('posted') ?? '';
	const classification = classificationFromFitParam(s.get('fit'));
	return {
		limit: API_LIST_DEFAULT_LIMIT,
		keyword: keyword || undefined,
		posted_after: postedAfter || undefined,
		classification
	};
}

export function useJobsInfiniteFromUrl() {
	const options = derived(page, ($p) => {
		const s = $p.url.searchParams;
		const keyword = s.get('q') ?? '';
		const postedAfter = s.get('posted') ?? '';
		const classification = classificationFromFitParam(s.get('fit'));
		const f: JobsFilter = {
			limit: API_LIST_DEFAULT_LIMIT,
			keyword: keyword || undefined,
			posted_after: postedAfter || undefined,
			classification
		};
		return {
			queryKey: ['jobs', f] as const,
			initialPageParam: null as string | null,
			queryFn: async ({ pageParam }: { pageParam: string | null }) => {
				const { items, nextCursor } = await listJobs({
					...f,
					cursor: pageParam ?? undefined,
					limit: f.limit ?? API_LIST_DEFAULT_LIMIT
				});
				return { items, nextCursor };
			},
			getNextPageParam: (lastPage: { nextCursor: string | null }) =>
				lastPage.nextCursor ?? undefined
		};
	});
	return createInfiniteQuery(options);
}

export function useJobFromRoute() {
	const options = derived(page, ($p) => {
		const id = $p.params.id;
		return {
			queryKey: ['job', id] as const,
			queryFn: () => getJob(String(id)),
			enabled: browser && Boolean(id),
			staleTime: 5 * 60_000
		};
	});
	return createQuery(options);
}

export function useJobEvaluationFromRoute() {
	const options = derived(page, ($p) => {
		const id = $p.params.id;
		return {
			queryKey: ['job', id, 'evaluation'] as const,
			queryFn: () => getJobEvaluation(String(id)),
			enabled: browser && Boolean(id),
			staleTime: 5 * 60_000
		};
	});
	return createQuery(options);
}

export function useTriggerEvaluation() {
	const qc = useQueryClient();
	return createMutation<TriggerEvaluationBody, Error, string>({
		mutationFn: (jobId: string) => triggerJobEvaluation(jobId),
		onSuccess: () => {
			void qc.invalidateQueries({ queryKey: ['jobs'] });
		}
	});
}

export type RegenerateJobDocumentsInput = {
	jobId: string;
	part?: RegenerateDocumentsPart;
};

export function useRegenerateJobDocuments() {
	const qc = useQueryClient();
	return createMutation<TriggerEvaluationBody, Error, RegenerateJobDocumentsInput>({
		mutationFn: ({ jobId, part }) =>
			regenerateJobDocuments(jobId, part != null ? { part } : {}),
		onSuccess: (_data, { jobId }) => {
			void qc.invalidateQueries({ queryKey: ['job', jobId, 'evaluation'] });
		}
	});
}

export { jobFiltersFromPage };
