<script lang="ts">
	import { goto } from '$app/navigation';
	import { loadOnboardingDraft } from '$lib/utils/onboarding';

	$effect(() => {
		const d = loadOnboardingDraft();
		if (d?.step === 2) void goto('/onboarding/cv');
		else if (d?.step === 3) void goto('/onboarding/config');
		else void goto('/onboarding/profile');
	});
</script>

<p class="text-sm text-base-content/60">Redirecting…</p>
