import { createMutation, createQuery, useQueryClient } from '@tanstack/svelte-query';
import { API_LIST_JOB_CONFIGS_PAGE_LIMIT } from '$lib/api/limits';
import {
	createJobConfig,
	disableJobConfig,
	listJobConfigs,
	listSchedulePresets,
	runJobConfigPipeline,
	updateJobConfig
} from '$lib/api/jobConfigs';
import type { JobConfig } from '$lib/types/jobConfig';
import type { SchedulePreset } from '$lib/types/schedulePreset';

export function useSchedulePresets() {
	return createQuery({
		queryKey: ['job-configs', 'schedule-presets'],
		queryFn: listSchedulePresets,
		staleTime: 86_400_000
	});
}

export function useJobConfigs(activeOnly = false) {
	return createQuery({
		queryKey: ['job-configs', { activeOnly }],
		queryFn: async () =>
			(await listJobConfigs({ active_only: activeOnly, limit: API_LIST_JOB_CONFIGS_PAGE_LIMIT }))
				.items,
		staleTime: 60_000
	});
}

export function useCreateJobConfig() {
	const qc = useQueryClient();
	return createMutation<JobConfig, Error, Record<string, unknown>>({
		mutationFn: (body: Record<string, unknown>) => createJobConfig(body),
		onSuccess: () => {
			void qc.invalidateQueries({ queryKey: ['job-configs'] });
		}
	});
}

export function useUpdateJobConfig() {
	const qc = useQueryClient();
	return createMutation<JobConfig, Error, { id: string; body: Record<string, unknown> }>({
		mutationFn: (args) => updateJobConfig(args.id, args.body),
		onSuccess: (data) => {
			void qc.invalidateQueries({ queryKey: ['job-configs'] });
			void qc.invalidateQueries({ queryKey: ['job-config', data.id] });
		}
	});
}

export function useDisableJobConfig() {
	const qc = useQueryClient();
	return createMutation<JobConfig, Error, string>({
		mutationFn: (id: string) => disableJobConfig(id),
		onSuccess: () => {
			void qc.invalidateQueries({ queryKey: ['job-configs'] });
		}
	});
}

export function useRunJobConfigPipeline() {
	return createMutation<{ task_id: string }, Error, string>({
		mutationFn: (id: string) => runJobConfigPipeline(id)
	});
}
