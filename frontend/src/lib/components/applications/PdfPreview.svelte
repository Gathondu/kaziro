<script lang="ts">
	const {
		title,
		url
	}: {
		title: string;
		url: string | null;
	} = $props();
</script>

<div class="border-base-300 bg-base-200 flex min-h-80 flex-col rounded-2xl border p-3 shadow-inner">
	<h3 class="mb-2 text-sm font-semibold">{title}</h3>
	{#if url}
		<iframe
			{title}
			src={url}
			width="100%"
			height="420"
			class="bg-base-100 min-h-72 w-full flex-1 rounded-xl"
		></iframe>
	{:else}
		<p class="text-base-content/60 text-sm">No PDF URL yet.</p>
	{/if}
</div>
