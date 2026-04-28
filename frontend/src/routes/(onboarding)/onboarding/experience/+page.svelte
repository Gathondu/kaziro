<script lang="ts">
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import Button from '$lib/components/ui/Button.svelte';
	import { onboardingExperienceSchema } from '$lib/schemas/profile';
	import {
		loadOnboardingDraft,
		resumeOnboardingPath,
		saveOnboardingDraft
	} from '$lib/utils/onboarding';
	import { omitFieldErrors } from '$lib/utils/form-errors.utils';
	import {
		EXPERIENCE_YEARS_MAX,
		sanitizeExperienceYearsInput
	} from '$lib/utils/experience-years-input.utils';
	import { get } from 'svelte/store';

	let yearsInput = $state('');
	let fieldErrors = $state<Record<string, string>>({});

	const yearsFilled = $derived(yearsInput.trim() !== '');
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
		if (y !== undefined && y !== null) {
			const clamped = Math.min(EXPERIENCE_YEARS_MAX, Math.max(0, y));
			yearsInput = String(clamped);
		} else {
			yearsInput = '';
		}
	});

	function goSkills(years: number | undefined): void {
		const prev = loadOnboardingDraft();
		if (!prev?.profile?.full_name) {
			void goto('/onboarding/about-you');
			return;
		}
		saveOnboardingDraft({
			step: 1,
			profileSubStep: 'skills',
			profile: {
				...prev.profile,
				experience_years: years
			}
		});
		void goto('/onboarding/skills');
	}

	function skipOrNext(e: Event): void {
		e.preventDefault();
		fieldErrors = {};
		if (yearsFilled) {
			const parsed = onboardingExperienceSchema.safeParse({
				experience_years: yearsInput.trim() === '' ? null : yearsInput
			});
			if (!parsed.success) {
				for (const iss of parsed.error.issues) {
					const k = String(iss.path[0] ?? 'form');
					fieldErrors = { ...fieldErrors, [k]: iss.message };
				}
				return;
			}
			goSkills(parsed.data.experience_years ?? undefined);
			return;
		}
		goSkills(undefined);
	}
</script>

<svelte:head>
	<title>Onboarding — Experience</title>
</svelte:head>

<h1 class="mb-2 text-xl font-semibold">Years of experience</h1>
<p class="text-base-content/70 mb-6 text-sm">
	Optional — rough total years in roles relevant to your search. Skip if you prefer not to say.
</p>
<form class="space-y-4" onsubmit={skipOrNext}>
	<label class="block space-y-1.5">
		<span class="text-sm font-medium">Years of experience</span>
		<input
			class="bg-base-200 text-base-content placeholder:text-base-content/45 block w-full rounded-xl border px-3 py-2.5 transition-colors focus:ring-2 focus:outline-none {fieldErrors.experience_years
				? 'border-error focus:ring-error/35'
				: 'border-base-300 focus:border-primary focus:ring-primary/25'}"
			type="text"
			inputmode="numeric"
			pattern="[0-9]*"
			autocomplete="off"
			maxlength="2"
			value={yearsInput}
			oninput={(e) => {
				const el = e.currentTarget as HTMLInputElement;
				const next = sanitizeExperienceYearsInput(el.value);
				yearsInput = next;
				// If normalized value equals prior state, Svelte may skip a render; keep DOM in sync.
				if (el.value !== next) el.value = next;
				fieldErrors = omitFieldErrors(fieldErrors, 'experience_years');
			}}
		/>
		{#if fieldErrors.experience_years}<span class="text-error text-xs"
				>{fieldErrors.experience_years}</span
			>{/if}
	</label>
	<Button type="submit" class="h-11 w-full justify-center">{primaryLabel}</Button>
</form>
