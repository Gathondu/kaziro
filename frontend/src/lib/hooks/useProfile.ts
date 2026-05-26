import { createMutation, createQuery, useQueryClient } from '@tanstack/svelte-query';
import { browser } from '$app/environment';
import { derived } from 'svelte/store';
import { ApiError } from '$lib/api/errors';
import { getProfile, putProfile, signedProfileCvPdfUrl, uploadCvPdf } from '$lib/api/profile';
import type { CvUploadResult, Profile } from '$lib/types/profile';

export function useProfile() {
	return createQuery({
		queryKey: ['profile'],
		queryFn: () => getProfile(),
		staleTime: 5 * 60_000,
		retry: (failureCount, error) => {
			if (error instanceof ApiError && error.status === 404) return false;
			return failureCount < 1;
		},
		refetchOnWindowFocus: (query) => {
			const err = query.state.error;
			if (err instanceof ApiError && err.status === 404) return false;
			return true;
		}
	});
}

export function useUpsertProfile() {
	const qc = useQueryClient();
	return createMutation<Profile, Error, Record<string, unknown>>({
		mutationFn: (body: Record<string, unknown>) => putProfile(body),
		onSuccess: (data: Profile) => {
			qc.setQueryData(['profile'], data);
		}
	});
}

export function useProfileCvPdfUrl() {
	const profile = useProfile();
	const options = derived(profile, ($profile) => ({
		queryKey: ['profile', 'cv-pdf-url'] as const,
		queryFn: () => signedProfileCvPdfUrl(),
		enabled: browser && Boolean($profile.data?.has_master_cv),
		staleTime: 4 * 60_000
	}));
	return createQuery(options);
}

export function useCvUpload() {
	const qc = useQueryClient();
	return createMutation<CvUploadResult, Error, File>({
		mutationFn: (file: File) => uploadCvPdf(file),
		onSuccess: () => {
			void qc.invalidateQueries({ queryKey: ['profile'] });
			void qc.invalidateQueries({ queryKey: ['profile', 'cv-pdf-url'] });
		}
	});
}
