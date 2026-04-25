<script lang="ts">
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import Button from '$lib/components/ui/Button.svelte';
	import { useUpsertProfile } from '$lib/hooks/useProfile';
	import { onboardingDomainSchema } from '$lib/schemas/profile';
	import { loadOnboardingDraft, resumeOnboardingPath, saveOnboardingDraft } from '$lib/utils/onboarding';
	import { get } from 'svelte/store';

	const DOMAIN_MAX = 100;

	let domain = $state('');
	let fieldErrors = $state<Record<string, string>>({});

	const mutation = useUpsertProfile();
	const domainLen = $derived(domain.length);

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
		if (d?.profile?.domain !== undefined) {
			domain = d.profile.domain ?? '';
		}
	});

	async function submit(e: Event): Promise<void> {
		e.preventDefault();
		fieldErrors = {};
		const parsed = onboardingDomainSchema.safeParse({ domain });
		if (!parsed.success) {
			for (const iss of parsed.error.issues) {
				const k = String(iss.path[0] ?? 'form');
				fieldErrors = { ...fieldErrors, [k]: iss.message };
			}
			return;
		}
		const prev = loadOnboardingDraft();
		if (!prev?.profile?.full_name) {
			void goto('/onboarding/about-you');
			return;
		}
		const domainVal = parsed.data.domain?.trim() ?? '';
		await get(mutation).mutateAsync({
			full_name: prev.profile.full_name,
			professional_summary: prev.profile.professional_summary,
			domain: domainVal === '' ? undefined : domainVal
		});
		saveOnboardingDraft({
			step: 1,
			profileSubStep: 'experience',
			profile: {
				...prev.profile,
				domain: domainVal === '' ? undefined : domainVal
			}
		});
		await goto('/onboarding/experience');
	}
</script>

<svelte:head>
	<title>Onboarding — Domain</title>
</svelte:head>

<h1 class="mb-2 text-xl font-semibold">Your domain</h1>
<p class="mb-6 text-sm text-base-content/70">
	Your domain is the industry or problem space you work in (for example, healthcare IT, fintech
	payments, or climate hardware). It helps us match roles and language to your context.
</p>
<form class="space-y-4" onsubmit={submit}>
	<label class="form-control">
		<span class="label-text font-medium">Domain</span>
		<div class="relative">
			<textarea
				class="textarea textarea-bordered min-h-24 w-full rounded-xl border-base-300 bg-base-200 pb-10 pr-14 {fieldErrors.domain
					? 'textarea-error'
					: ''}"
				maxlength={DOMAIN_MAX}
				rows={4}
				bind:value={domain}
			></textarea>
			<span
				class="pointer-events-none absolute bottom-3 right-3 text-xs tabular-nums text-base-content/60"
				aria-live="polite"
			>
				{domainLen}/{DOMAIN_MAX}
			</span>
		</div>
		{#if fieldErrors.domain}<span class="label-text-alt text-error">{fieldErrors.domain}</span>{/if}
	</label>
	<Button type="submit" disabled={$mutation.isPending}>
		{$mutation.isPending ? 'Saving…' : 'Continue'}
	</Button>
</form>
