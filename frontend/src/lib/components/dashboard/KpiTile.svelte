<script lang="ts">
	const {
		label,
		value,
		hint
	}: {
		label: string;
		value: string | number;
		hint?: string;
	} = $props();
</script>

<div class="rounded-2xl border border-base-300 bg-base-100 p-5 shadow-sm">
	<p class="text-sm font-medium text-base-content/70">{label}</p>
	<p class="mt-2 text-3xl font-semibold tabular-nums">{value}</p>
	{#if hint}
		<p class="mt-1 text-xs text-base-content/60">{hint}</p>
	{/if}
</div>
