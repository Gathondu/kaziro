<script lang="ts">
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { getUser, isAuthReady } from '$lib/stores/auth';
	import Button from '$lib/components/ui/Button.svelte';

	$effect(() => {
		if (!browser || !isAuthReady()) return;
		if (getUser()) {
			void goto('/dashboard');
		}
	});
</script>

<svelte:head>
	<title>Kaziro</title>
</svelte:head>

<main class="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-16">
	<h1 class="text-3xl font-semibold text-primary">Kaziro</h1>
	<p class="text-base leading-relaxed text-base-content/80">
		AI-assisted job search, evaluation, and tailored applications — warm, focused, and fast.
	</p>
	<div class="flex flex-wrap gap-3">
		<a href="/login"><Button>Log in</Button></a>
		<a href="/signup"><Button variant="outline">Create account</Button></a>
	</div>
</main>
