<script lang="ts">
	import type { ApplicationEvent } from '$lib/types/applications';

	const { events }: { events: ApplicationEvent[] } = $props();

	const sorted = $derived([...events].sort((a, b) => a.event_date.localeCompare(b.event_date)));
</script>

<ol class="space-y-3 border-l border-base-300 pl-4">
	{#each sorted as ev (ev.id)}
		<li class="relative">
			<span class="absolute -left-2 top-1 h-3 w-3 rounded-full bg-primary"></span>
			<p class="text-sm font-medium">{ev.event_type.replaceAll('_', ' ')}</p>
			<p class="text-xs text-base-content/60">
				<time datetime={ev.event_date}>{new Date(ev.event_date).toLocaleString()}</time>
			</p>
			{#if ev.from_status || ev.to_status}
				<p class="text-xs text-base-content/70">
					{ev.from_status ?? '—'} → {ev.to_status ?? '—'}
				</p>
			{/if}
			{#if ev.notes}
				<p class="mt-1 text-sm text-base-content/80">{ev.notes}</p>
			{/if}
		</li>
	{/each}
</ol>
