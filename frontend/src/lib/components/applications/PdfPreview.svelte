<script lang="ts">
	const {
		title,
		url
	}: {
		title: string;
		url: string | null;
	} = $props();
</script>

<div class="flex min-h-80 flex-col rounded-2xl border border-base-300 bg-base-200 p-3 shadow-inner">
	<h3 class="mb-2 text-sm font-semibold">{title}</h3>
	{#if url}
		<iframe
			{title}
			src={url}
			width="100%"
			height="420"
			class="min-h-72 w-full flex-1 rounded-xl bg-base-100"
		></iframe>
	{:else}
		<p class="text-sm text-base-content/60">No PDF URL yet.</p>
	{/if}
</div>
