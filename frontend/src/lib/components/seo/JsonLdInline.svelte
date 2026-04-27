<script lang="ts">
	/** Server-built `JSON.stringify` object graph — not user-controlled HTML. */
	const { jsonLd }: { jsonLd: string } = $props();

	const markup = $derived('<script type="application/ld+json">' + jsonLd + '</' + 'script>');
</script>

<svelte:head>
	{@html markup}
</svelte:head>
