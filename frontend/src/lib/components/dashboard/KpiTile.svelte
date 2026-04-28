<script lang="ts">
	const {
		label,
		value,
		hint,
		href,
		animated = true
	}: {
		label: string;
		value: string | number;
		hint?: string;
		href?: string;
		animated?: boolean;
	} = $props();
</script>

{#if href}
	<a
		{href}
		class="group bg-base-300 relative block overflow-hidden rounded-2xl transition-transform duration-200 hover:-translate-y-0.5 hover:scale-105"
	>
		{#if animated}
			<span
				class="pointer-events-none absolute inset-0 overflow-hidden rounded-2xl opacity-0 transition-opacity duration-300 group-hover:opacity-100"
			>
				<span class="kaziro-card-sheen-blur absolute -inset-28 animate-spin blur-lg"></span>
				<span class="kaziro-card-sheen-sharp absolute -inset-24 animate-spin"></span>
			</span>
		{/if}
		<span
			class="border-base-300 bg-base-100 relative z-10 m-0.5 block rounded-2xl border p-5 shadow-sm transition-shadow duration-200 group-hover:shadow-md"
		>
			<p class="text-base-content/70 text-sm font-medium">{label}</p>
			<p class="mt-2 text-3xl font-semibold tabular-nums">{value}</p>
			{#if hint}
				<p class="text-base-content/60 mt-1 text-xs">{hint}</p>
			{/if}
		</span>
	</a>
{:else}
	<div class="border-base-300 bg-base-100 rounded-2xl border p-5 shadow-sm">
		<p class="text-base-content/70 text-sm font-medium">{label}</p>
		<p class="mt-2 text-3xl font-semibold tabular-nums">{value}</p>
		{#if hint}
			<p class="text-base-content/60 mt-1 text-xs">{hint}</p>
		{/if}
	</div>
{/if}
