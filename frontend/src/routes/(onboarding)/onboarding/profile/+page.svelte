<script lang="ts">
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { loadOnboardingDraft, resumeOnboardingPath } from '$lib/utils/onboarding';

	$effect(() => {
		if (!browser) return;
		void goto(resumeOnboardingPath(loadOnboardingDraft()));
	});
</script>

<p class="text-base-content/60 text-sm">Redirecting…</p>
