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
		href={href}
		class="group relative block overflow-hidden rounded-2xl bg-base-300 transition-transform duration-200 hover:-translate-y-0.5 hover:scale-105"
	>
		{#if animated}
			<span
				class="pointer-events-none absolute inset-0 overflow-hidden rounded-2xl opacity-0 transition-opacity duration-300 group-hover:opacity-100"
			>
				<span
					class="absolute -inset-24 animate-spin"
					style="background: conic-gradient(from 0deg, transparent 0deg, transparent 235deg, oklch(var(--p) / 0.45) 270deg, oklch(var(--p) / 0.85) 300deg, oklch(var(--s) / 0.95) 326deg, oklch(var(--a) / 0.85) 348deg, oklch(var(--a) / 0.45) 360deg); animation-duration: 3.4s;"
				></span>
			</span>
		{/if}
		<span
			class="relative z-10 block m-px rounded-2xl border border-base-300 bg-base-100 p-5 shadow-sm transition-shadow duration-200 group-hover:shadow-md"
		>
			<p class="text-sm font-medium text-base-content/70">{label}</p>
			<p class="mt-2 text-3xl font-semibold tabular-nums">{value}</p>
			{#if hint}
				<p class="mt-1 text-xs text-base-content/60">{hint}</p>
			{/if}
		</span>
	</a>
{:else}
	<div class="rounded-2xl border border-base-300 bg-base-100 p-5 shadow-sm">
		<p class="text-sm font-medium text-base-content/70">{label}</p>
		<p class="mt-2 text-3xl font-semibold tabular-nums">{value}</p>
		{#if hint}
			<p class="mt-1 text-xs text-base-content/60">{hint}</p>
		{/if}
	</div>
{/if}
