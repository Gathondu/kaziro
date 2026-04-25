<script lang="ts">
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import Button from '$lib/components/ui/Button.svelte';
	import { onboardingDomainSchema } from '$lib/schemas/profile';
	import { omitFieldErrors } from '$lib/utils/form-errors.utils';
	import { loadOnboardingDraft, resumeOnboardingPath, saveOnboardingDraft } from '$lib/utils/onboarding';
	import { get } from 'svelte/store';

	const DOMAIN_MAX = 100;

	let domain = $state('');
	let fieldErrors = $state<Record<string, string>>({});

	const domainLen = $derived(domain.length);
	const domainFilled = $derived(domain.trim().length > 0);
	const primaryLabel = $derived(domainFilled ? 'Next' : 'Skip');

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

	function goExperience(nextDomain: string | undefined): void {
		const prev = loadOnboardingDraft();
		if (!prev?.profile?.full_name) {
			void goto('/onboarding/about-you');
			return;
		}
		saveOnboardingDraft({
			step: 1,
			profileSubStep: 'experience',
			profile: {
				...prev.profile,
				domain: nextDomain
			}
		});
		void goto('/onboarding/experience');
	}

	function submit(e: Event): void {
		e.preventDefault();
		fieldErrors = {};
		if (!domainFilled) {
			goExperience(undefined);
			return;
		}
		const parsed = onboardingDomainSchema.safeParse({ domain });
		if (!parsed.success) {
			for (const iss of parsed.error.issues) {
				const k = String(iss.path[0] ?? 'form');
				fieldErrors = { ...fieldErrors, [k]: iss.message };
			}
			return;
		}
		const domainVal = parsed.data.domain?.trim() ?? '';
		goExperience(domainVal === '' ? undefined : domainVal);
	}

	function onDomainInput(): void {
		fieldErrors = omitFieldErrors(fieldErrors, 'domain');
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
				oninput={onDomainInput}
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
	<Button type="submit">{primaryLabel}</Button>
</form>
