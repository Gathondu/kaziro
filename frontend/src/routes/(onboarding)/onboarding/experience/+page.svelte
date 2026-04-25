<script lang="ts">
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import Button from '$lib/components/ui/Button.svelte';
	import { useUpsertProfile } from '$lib/hooks/useProfile';
	import { onboardingExperienceSchema } from '$lib/schemas/profile';
	import {
		loadOnboardingDraft,
		resumeOnboardingPath,
		saveOnboardingDraft
	} from '$lib/utils/onboarding';
	import { get } from 'svelte/store';

	let experience_years = $state<number | ''>('');
	let fieldErrors = $state<Record<string, string>>({});

	const mutation = useUpsertProfile();

	const yearsFilled = $derived(experience_years !== '' && experience_years !== null);
	const primaryLabel = $derived(yearsFilled ? 'Next' : 'Skip');

	$effect(() => {
		if (!browser) return;
		const path = get(page).url.pathname;
		const d = loadOnboardingDraft();
		const want = resumeOnboardingPath(d);
		if (want !== path) void goto(want);
	});

	$effect(() => {
		if (!browser) return;
		const d = loadOnboardingDraft();
		const y = d?.profile?.experience_years;
		if (y !== undefined && y !== null) experience_years = y;
	});

	async function goSkills(years: number | undefined): Promise<void> {
		const prev = loadOnboardingDraft();
		if (!prev?.profile?.full_name) {
			void goto('/onboarding/about-you');
			return;
		}
		const body: Record<string, unknown> = { full_name: prev.profile.full_name };
		if (prev.profile.professional_summary !== undefined) {
			body.professional_summary = prev.profile.professional_summary;
		}
		if (prev.profile.domain !== undefined) {
			body.domain = prev.profile.domain;
		}
		if (years !== undefined) {
			body.experience_years = years;
		}
		await get(mutation).mutateAsync(body);
		saveOnboardingDraft({
			step: 1,
			profileSubStep: 'skills',
			profile: {
				...prev.profile,
				experience_years: years ?? prev.profile.experience_years
			}
		});
		await goto('/onboarding/skills');
	}

	async function skipOrNext(e: Event): Promise<void> {
		e.preventDefault();
		fieldErrors = {};
		if (yearsFilled) {
			const parsed = onboardingExperienceSchema.safeParse({
				experience_years: experience_years === '' ? null : experience_years
			});
			if (!parsed.success) {
				for (const iss of parsed.error.issues) {
					const k = String(iss.path[0] ?? 'form');
					fieldErrors = { ...fieldErrors, [k]: iss.message };
				}
				return;
			}
			await goSkills(parsed.data.experience_years ?? undefined);
			return;
		}
		await goSkills(undefined);
	}
</script>

<svelte:head>
	<title>Onboarding — Experience</title>
</svelte:head>

<h1 class="mb-2 text-xl font-semibold">Years of experience</h1>
<p class="mb-6 text-sm text-base-content/70">
	Optional — rough total years in roles relevant to your search. Skip if you prefer not to say.
</p>
<form class="space-y-4" onsubmit={skipOrNext}>
	<label class="form-control">
		<span class="label-text font-medium">Years of experience</span>
		<input
			class="input input-bordered rounded-xl border-base-300 bg-base-200 {fieldErrors.experience_years
				? 'input-error'
				: ''}"
			type="number"
			min="0"
			max="80"
			bind:value={experience_years}
		/>
		{#if fieldErrors.experience_years}<span class="label-text-alt text-error"
				>{fieldErrors.experience_years}</span
			>{/if}
	</label>
	<Button type="submit" disabled={$mutation.isPending}>
		{$mutation.isPending ? 'Saving…' : primaryLabel}
	</Button>
</form>
