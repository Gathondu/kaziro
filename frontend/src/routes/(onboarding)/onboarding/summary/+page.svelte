<script lang="ts">
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import Button from '$lib/components/ui/Button.svelte';
	import { onboardingProfessionalSummarySchema } from '$lib/schemas/profile';
	import { omitFieldErrors } from '$lib/utils/form-errors.utils';
	import {
		loadOnboardingDraft,
		resumeOnboardingPath,
		saveOnboardingDraft
	} from '$lib/utils/onboarding';
	import { get } from 'svelte/store';

	let professional_summary = $state('');
	let fieldErrors = $state<Record<string, string>>({});

	const summaryFilled = $derived(professional_summary.trim().length > 0);
	const primaryLabel = $derived(summaryFilled ? 'Next' : 'Skip');

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
		if (d?.profile?.professional_summary !== undefined) {
			professional_summary = d.profile.professional_summary ?? '';
		}
	});

	function goDomain(summary: string | undefined): void {
		const prev = loadOnboardingDraft();
		if (!prev?.profile?.full_name) {
			void goto('/onboarding/about-you');
			return;
		}
		const profile =
			summary === undefined
				? { ...prev.profile, professional_summary: undefined }
				: { ...prev.profile, professional_summary: summary };
		saveOnboardingDraft({
			step: 1,
			profileSubStep: 'domain',
			profile
		});
		void goto('/onboarding/domain');
	}

	function skipOrNext(e: Event): void {
		e.preventDefault();
		fieldErrors = {};
		if (summaryFilled) {
			const parsed = onboardingProfessionalSummarySchema.safeParse({ professional_summary });
			if (!parsed.success) {
				for (const iss of parsed.error.issues) {
					const k = String(iss.path[0] ?? 'form');
					fieldErrors = { ...fieldErrors, [k]: iss.message };
				}
				return;
			}
			const text = parsed.data.professional_summary?.trim() ?? '';
			goDomain(text === '' ? undefined : text);
			return;
		}
		goDomain(undefined);
	}

	function onSummaryInput(): void {
		fieldErrors = omitFieldErrors(fieldErrors, 'professional_summary');
	}
</script>

<svelte:head>
	<title>Onboarding — Professional summary</title>
</svelte:head>

<h1 class="mb-2 text-xl font-semibold">Professional summary</h1>
<p class="mb-6 text-sm text-base-content/70">
	A short overview helps us tailor recommendations. Optional — you can skip.
</p>
<form class="space-y-4" onsubmit={skipOrNext}>
	<label class="form-control">
		<span class="label-text font-medium">Summary</span>
		<textarea
			class="textarea textarea-bordered min-h-28 rounded-xl border-base-300 bg-base-200 {fieldErrors.professional_summary
				? 'textarea-error'
				: ''}"
			bind:value={professional_summary}
			oninput={onSummaryInput}
		></textarea>
		{#if fieldErrors.professional_summary}<span class="label-text-alt text-error"
				>{fieldErrors.professional_summary}</span
			>{/if}
	</label>
	<Button type="submit">{primaryLabel}</Button>
</form>
