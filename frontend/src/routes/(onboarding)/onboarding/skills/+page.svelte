<script lang="ts">
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import Button from '$lib/components/ui/Button.svelte';
	import { useUpsertProfile } from '$lib/hooks/useProfile';
	import { onboardingSkillsSchema } from '$lib/schemas/profile';
	import {
		loadOnboardingDraft,
		resumeOnboardingPath,
		saveOnboardingDraft
	} from '$lib/utils/onboarding';
	import { get } from 'svelte/store';

	let skillsText = $state('');
	let fieldErrors = $state<Record<string, string>>({});

	const mutation = useUpsertProfile();

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

	async function goCv(skills: string[] | undefined): Promise<void> {
		const prev = loadOnboardingDraft();
		if (!prev?.profile?.full_name) {
			void goto('/onboarding/about-you');
			return;
		}
		const body: Record<string, unknown> = {
			full_name: prev.profile.full_name,
			professional_summary: prev.profile.professional_summary,
			domain: prev.profile.domain,
			experience_years: prev.profile.experience_years ?? undefined
		};
		if (skills !== undefined) {
			body.skills = skills;
		}
		await get(mutation).mutateAsync(body);
		saveOnboardingDraft({
			step: 2,
			profile: {
				...prev.profile,
				skillsText: skills === undefined ? prev.profile.skillsText : skills.join(', ')
			}
		});
		await goto('/onboarding/cv');
	}

	async function skipOrNext(e: Event): Promise<void> {
		e.preventDefault();
		fieldErrors = {};
		if (skillsFilled) {
			const parsed = onboardingSkillsSchema.safeParse({ skills: skillsText });
			if (!parsed.success) {
				for (const iss of parsed.error.issues) {
					const k = String(iss.path[0] ?? 'form');
					fieldErrors = { ...fieldErrors, [k]: iss.message };
				}
				return;
			}
			const list = skillsListFromText(parsed.data.skills ?? '');
			await goCv(list);
			return;
		}
		await goCv([]);
	}
</script>

<svelte:head>
	<title>Onboarding — Skills</title>
</svelte:head>

<h1 class="mb-2 text-xl font-semibold">Skills</h1>
<p class="mb-6 text-sm text-base-content/70">
	Optional — list strengths as comma-separated keywords (for example, TypeScript, Postgres, team
	leadership). Skip if you want to add these later in Settings.
</p>
<form class="space-y-4" onsubmit={skipOrNext}>
	<label class="form-control">
		<span class="label-text font-medium">Skills (comma-separated)</span>
		<input
			class="input input-bordered rounded-xl border-base-300 bg-base-200 {fieldErrors.skills
				? 'input-error'
				: ''}"
			autocomplete="off"
			bind:value={skillsText}
		/>
		{#if fieldErrors.skills}<span class="label-text-alt text-error">{fieldErrors.skills}</span>{/if}
	</label>
	<Button type="submit" disabled={$mutation.isPending}>
		{$mutation.isPending ? 'Saving…' : primaryLabel}
	</Button>
</form>
