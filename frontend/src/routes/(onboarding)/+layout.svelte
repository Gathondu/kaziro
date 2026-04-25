<script lang="ts">
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { fade } from 'svelte/transition';
	import { getUser, isAuthReady } from '$lib/stores/auth';
	import { onboardingStepMeta } from '$lib/utils/onboarding';

	const { children } = $props();

	const pathname = $derived($page.url.pathname);
	const stepMeta = $derived(onboardingStepMeta(pathname));
	const progressPct = $derived(
		stepMeta ? Math.round((stepMeta.current / stepMeta.total) * 100) : 0
	);

	$effect(() => {
		if (!browser || !isAuthReady()) return;
		if (!getUser()) {
			const next = encodeURIComponent($page.url.pathname + $page.url.search);
			void goto(`/login?next=${next}`);
		}
	});
</script>

<div class="flex min-h-screen flex-col bg-base-200">
	<header
		class="shrink-0 border-b border-base-300 bg-base-100/90 backdrop-blur-sm"
		aria-label="Onboarding"
	>
		<div class="mx-auto flex w-full max-w-xl items-center justify-center px-4 py-3">
			{#if stepMeta}
				<span class="text-xs font-medium tabular-nums text-base-content/70">
					Step {stepMeta.current} of {stepMeta.total}
				</span>
			{/if}
		</div>
		{#if stepMeta}
			<div class="h-1 w-full bg-base-300" aria-hidden="true">
				<div
					class="h-full bg-primary transition-[width] duration-300 ease-out"
					style={`width: ${progressPct}%`}
				></div>
			</div>
		{/if}
	</header>

	<main class="flex flex-1 flex-col items-stretch px-4 py-10 sm:items-center sm:py-16">
		<div class="w-full max-w-xl sm:mx-auto">
			{#key pathname}
				<div class="w-full" transition:fade={{ duration: 200 }}>
					{@render children()}
				</div>
			{/key}
		</div>
	</main>
</div>
