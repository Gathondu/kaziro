<script lang="ts">
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { loadOnboardingDraft, resumeOnboardingPath } from '$lib/utils/onboarding';

	$effect(() => {
		if (!browser) return;
		const d = loadOnboardingDraft();
		void goto(resumeOnboardingPath(d));
	});
</script>

<p class="text-sm text-base-content/60">Redirecting…</p>
