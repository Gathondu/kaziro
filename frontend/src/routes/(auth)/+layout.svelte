<script lang="ts">
	const { children } = $props();
</script>

<svelte:head>
	<meta name="robots" content="noindex,nofollow" />
</svelte:head>

<div class="bg-base-200 flex min-h-screen items-center justify-center px-4 py-10">
	<div class="border-base-300 bg-base-100 w-full max-w-md rounded-2xl border p-6 shadow-sm">
		{@render children()}
	</div>
</div>
