<script lang="ts">
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import Button from '$lib/components/ui/Button.svelte';
	import { validateProfileDraftForSubmit } from '$lib/utils/onboarding-profile.functions';
	import { omitFieldErrors } from '$lib/utils/form-errors.utils';
	import {
		loadOnboardingDraft,
		resumeOnboardingPath,
		saveOnboardingDraft
	} from '$lib/utils/onboarding';
	import { get } from 'svelte/store';

	let skillsText = $state('');
	let fieldErrors = $state<Record<string, string>>({});

	const skillsFilled = $derived(skillsText.trim().length > 0);
	const primaryLabel = $derived(skillsFilled ? 'Next' : 'Skip');

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
		if (d?.profile?.skillsText !== undefined) {
			skillsText = d.profile.skillsText ?? '';
		}
	});

	function skillsListFromText(text: string): string[] {
		return text
			.split(',')
			.map((s) => s.trim())
			.filter(Boolean);
	}

	function goCv(): void {
		const prev = loadOnboardingDraft();
		if (!prev?.profile?.full_name) {
			void goto('/onboarding/about-you');
			return;
		}
		const mergedProfile = {
			...prev.profile,
			skillsText: skillsFilled ? skillsText.trim() : undefined
		};
		const validated = validateProfileDraftForSubmit(mergedProfile);
		if (!validated.ok) {
			fieldErrors = validated.fieldErrors;
			return;
		}
		fieldErrors = {};
		saveOnboardingDraft({
			step: 2,
			profile: {
				...mergedProfile,
				skillsText: skillsFilled ? skillsListFromText(skillsText).join(', ') : undefined
			}
		});
		void goto('/onboarding/cv');
	}

	function skipOrNext(e: Event): void {
		e.preventDefault();
		goCv();
	}

	function onSkillsInput(): void {
		fieldErrors = omitFieldErrors(fieldErrors, 'skills', 'form');
	}
</script>

<svelte:head>
	<title>Onboarding — Skills</title>
</svelte:head>

<h1 class="mb-2 text-xl font-semibold">Skills</h1>
<p class="text-base-content/70 mb-6 text-sm">
	Optional — list strengths as comma-separated keywords (for example, TypeScript, Postgres, team
	leadership). Skip if you want to add these later in Settings.
</p>
<form class="space-y-4" onsubmit={skipOrNext}>
	{#if fieldErrors.form}
		<p class="text-error text-sm" role="alert">{fieldErrors.form}</p>
	{/if}
	<label class="form-control">
		<span class="label-text font-medium">Skills (comma-separated)</span>
		<input
			class="input input-bordered border-base-300 bg-base-200 rounded-xl {fieldErrors.skills
				? 'input-error'
				: ''}"
			autocomplete="off"
			bind:value={skillsText}
			oninput={onSkillsInput}
		/>
		{#if fieldErrors.skills}<span class="label-text-alt text-error">{fieldErrors.skills}</span>{/if}
	</label>
	<Button type="submit">{primaryLabel}</Button>
</form>
