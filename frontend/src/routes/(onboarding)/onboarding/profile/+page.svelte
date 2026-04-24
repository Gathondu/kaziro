<script lang="ts">
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import WizardProgress from '$lib/components/onboarding/WizardProgress.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import { useUpsertProfile } from '$lib/hooks/useProfile';
	import { profileBasicsSchema } from '$lib/schemas/profile';
	import { saveOnboardingDraft } from '$lib/utils/onboarding';

	let full_name = $state('');
	let professional_summary = $state('');
	let domain = $state('');
	let experience_years = $state<number | ''>('');
	let skills = $state('');
	let fieldErrors = $state<Record<string, string>>({});

	const mutation = useUpsertProfile();

	async function submit(e: Event): Promise<void> {
		e.preventDefault();
		fieldErrors = {};
		const parsed = profileBasicsSchema.safeParse({
			full_name,
			professional_summary,
			domain,
			experience_years: experience_years === '' ? undefined : experience_years,
			skills
		});
		if (!parsed.success) {
			for (const iss of parsed.error.issues) {
				const k = String(iss.path[0] ?? 'form');
				fieldErrors = { ...fieldErrors, [k]: iss.message };
			}
			return;
		}
		const skillsList = parsed.data.skills
			? parsed.data.skills
					.split(',')
					.map((s) => s.trim())
					.filter(Boolean)
			: [];
		await get(mutation).mutateAsync({
			full_name: parsed.data.full_name,
			professional_summary: parsed.data.professional_summary || undefined,
			domain: parsed.data.domain || undefined,
			experience_years: parsed.data.experience_years ?? undefined,
			skills: skillsList
		});
		saveOnboardingDraft({ step: 2, profile: { full_name, professional_summary, domain } });
		await goto('/onboarding/cv');
	}
</script>

<svelte:head>
	<title>Onboarding — Profile</title>
</svelte:head>

<WizardProgress step={1} />
<h1 class="mb-2 text-xl font-semibold">Tell us about you</h1>
<p class="mb-6 text-sm text-base-content/70">
	We use this to evaluate job fit and tailor documents.
</p>
<form class="space-y-4" onsubmit={submit}>
	<label class="form-control">
		<span class="label-text font-medium">Full name</span>
		<input
			class="input input-bordered rounded-xl border-base-300 bg-base-200 {fieldErrors.full_name
				? 'input-error'
				: ''}"
			bind:value={full_name}
			required
		/>
		{#if fieldErrors.full_name}<span class="label-text-alt text-error">{fieldErrors.full_name}</span
			>{/if}
	</label>
	<label class="form-control">
		<span class="label-text font-medium">Professional summary</span>
		<textarea
			class="textarea textarea-bordered min-h-24 rounded-xl border-base-300 bg-base-200 {fieldErrors.professional_summary
				? 'textarea-error'
				: ''}"
			bind:value={professional_summary}
		></textarea>
		{#if fieldErrors.professional_summary}<span class="label-text-alt text-error"
				>{fieldErrors.professional_summary}</span
			>{/if}
	</label>
	<label class="form-control">
		<span class="label-text font-medium">Domain</span>
		<span class="label-text-alt text-base-content/60">Short field of focus (max 100 characters).</span>
		<input
			class="input input-bordered rounded-xl border-base-300 bg-base-200 {fieldErrors.domain
				? 'input-error'
				: ''}"
			maxlength={100}
			bind:value={domain}
		/>
		{#if fieldErrors.domain}<span class="label-text-alt text-error">{fieldErrors.domain}</span>{/if}
	</label>
	<label class="form-control">
		<span class="label-text font-medium">Years of experience</span>
		<input
			class="input input-bordered rounded-xl border-base-300 bg-base-200 {fieldErrors.experience_years
				? 'input-error'
				: ''}"
			type="number"
			min="0"
			bind:value={experience_years}
		/>
		{#if fieldErrors.experience_years}<span class="label-text-alt text-error"
				>{fieldErrors.experience_years}</span
			>{/if}
	</label>
	<label class="form-control">
		<span class="label-text font-medium">Skills (comma-separated)</span>
		<input
			class="input input-bordered rounded-xl border-base-300 bg-base-200"
			bind:value={skills}
		/>
		{#if fieldErrors.skills}<span class="label-text-alt text-error">{fieldErrors.skills}</span>{/if}
	</label>
	<Button type="submit" disabled={$mutation.isPending}>
		{$mutation.isPending ? 'Saving…' : 'Continue'}
	</Button>
</form>
