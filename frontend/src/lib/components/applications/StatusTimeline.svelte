<script lang="ts">
	import type { ApplicationEvent } from '$lib/types/applications';

	const { events }: { events: ApplicationEvent[] } = $props();

	const sorted = $derived([...events].sort((a, b) => a.event_date.localeCompare(b.event_date)));
</script>

<ol class="border-base-300 space-y-3 border-l pl-4">
	{#each sorted as ev (ev.id)}
		<li class="relative">
			<span class="bg-primary absolute top-1 -left-2 h-3 w-3 rounded-full"></span>
			<p class="text-sm font-medium">{ev.event_type.replaceAll('_', ' ')}</p>
			<p class="text-base-content/60 text-xs">
				<time datetime={ev.event_date}>{new Date(ev.event_date).toLocaleString()}</time>
			</p>
			{#if ev.from_status || ev.to_status}
				<p class="text-base-content/70 text-xs">
					{ev.from_status ?? '—'} → {ev.to_status ?? '—'}
				</p>
			{/if}
			{#if ev.notes}
				<p class="text-base-content/80 mt-1 text-sm">{ev.notes}</p>
			{/if}
		</li>
	{/each}
</ol>
