<script lang="ts">
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import Button from '$lib/components/ui/Button.svelte';
	import { useUpsertProfile } from '$lib/hooks/useProfile';
	import { onboardingNameSchema } from '$lib/schemas/profile';
	import { loadOnboardingDraft, resumeOnboardingPath, saveOnboardingDraft } from '$lib/utils/onboarding';
	import { get } from 'svelte/store';

	let full_name = $state('');
	let fieldErrors = $state<Record<string, string>>({});

	const mutation = useUpsertProfile();

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
		if (d?.profile?.full_name) full_name = d.profile.full_name;
	});

	async function submit(e: Event): Promise<void> {
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
		await get(mutation).mutateAsync({ full_name: parsed.data.full_name });
		const prev = loadOnboardingDraft();
		saveOnboardingDraft({
			step: 1,
			profileSubStep: 'summary',
			profile: {
				...prev?.profile,
				full_name: parsed.data.full_name
			}
		});
		await goto('/onboarding/summary');
	}
</script>

<svelte:head>
	<title>Onboarding — About you</title>
</svelte:head>

<h1 class="mb-2 text-xl font-semibold">Tell us about yourself</h1>
<p class="mb-6 text-sm text-base-content/70">
	We use this to evaluate job fit and tailor documents.
</p>
<form class="space-y-4" onsubmit={submit}>
	<label class="form-control">
		<span class="label-text font-medium">Name</span>
		<input
			class="input input-bordered rounded-xl border-base-300 bg-base-200 {fieldErrors.full_name
				? 'input-error'
				: ''}"
			autocomplete="name"
			bind:value={full_name}
		/>
		{#if fieldErrors.full_name}<span class="label-text-alt text-error">{fieldErrors.full_name}</span>{/if}
	</label>
	<Button type="submit" disabled={$mutation.isPending || full_name.trim().length === 0}>
		{$mutation.isPending ? 'Saving…' : 'Continue'}
	</Button>
</form>
