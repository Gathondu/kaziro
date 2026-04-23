<script lang="ts">
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { getUser, isAuthReady } from '$lib/stores/auth';

	const { children } = $props();

	$effect(() => {
		if (!browser || !isAuthReady()) return;
		if (!getUser()) {
			const next = encodeURIComponent($page.url.pathname + $page.url.search);
			void goto(`/login?next=${next}`);
		}
	});
</script>

<div class="min-h-screen bg-base-200 px-4 py-8">
	<div class="mx-auto max-w-2xl rounded-2xl border border-base-300 bg-base-100 p-6 shadow-sm">
		<p class="mb-4 text-sm text-base-content/70">
			<a class="link link-primary font-medium" href="/dashboard">Back to dashboard</a>
		</p>
		{@render children()}
	</div>
</div>
