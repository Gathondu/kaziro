<script lang="ts">
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import Button from '$lib/components/ui/Button.svelte';
	import { onboardingNameSchema } from '$lib/schemas/profile';
	import { omitFieldErrors } from '$lib/utils/form-errors.utils';
	import {
		loadOnboardingDraft,
		resumeOnboardingPath,
		saveOnboardingDraft
	} from '$lib/utils/onboarding';
	import { get } from 'svelte/store';

	let full_name = $state('');
	let fieldErrors = $state<Record<string, string>>({});

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
		if (d?.profile && d.profile.full_name !== undefined && d.profile.full_name !== null) {
			full_name = d.profile.full_name;
		}
	});

	function submit(e: Event): void {
		e.preventDefault();
		fieldErrors = {};
		const parsed = onboardingNameSchema.safeParse({ full_name });
		if (!parsed.success) {
			for (const iss of parsed.error.issues) {
				const k = String(iss.path[0] ?? 'form');
				fieldErrors = { ...fieldErrors, [k]: iss.message };
			}
			return;
		}
		const prev = loadOnboardingDraft();
		saveOnboardingDraft({
			step: 1,
			profileSubStep: 'summary',
			profile: {
				...prev?.profile,
				full_name: parsed.data.full_name
			}
		});
		void goto('/onboarding/summary');
	}

	function onFullNameInput(): void {
		fieldErrors = omitFieldErrors(fieldErrors, 'full_name');
	}
</script>

<svelte:head>
	<title>Onboarding — About you</title>
</svelte:head>

<h1 class="mb-2 text-xl font-semibold">Tell us about yourself</h1>
<p class="text-base-content/70 mb-6 text-sm">
	We use this to evaluate job fit and tailor documents.
</p>
<form class="space-y-4" onsubmit={submit}>
	<label class="form-control">
		<span class="label-text font-medium">Name</span>
		<input
			class="input input-bordered border-base-300 bg-base-200 rounded-xl {fieldErrors.full_name
				? 'input-error'
				: ''}"
			autocomplete="name"
			bind:value={full_name}
			oninput={onFullNameInput}
		/>
		{#if fieldErrors.full_name}<span class="label-text-alt text-error">{fieldErrors.full_name}</span
			>{/if}
	</label>
	<Button type="submit" disabled={full_name.trim().length === 0}>Next</Button>
</form>
