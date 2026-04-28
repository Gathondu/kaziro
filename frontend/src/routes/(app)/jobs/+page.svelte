<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { get } from 'svelte/store';
	import JobCard from '$lib/components/jobs/JobCard.svelte';
	import JobFilters from '$lib/components/jobs/JobFilters.svelte';
	import { useJobsInfiniteFromUrl } from '$lib/hooks/useJobs';
	import type { Classification } from '$lib/types/enums';

	let classification = $state<Classification | ''>('');
	let keyword = $state('');
	let postedAfter = $state('');

	$effect(() => {
		const s = $page.url.searchParams;
		keyword = s.get('q') ?? '';
		postedAfter = s.get('posted') ?? '';
		const fit = s.get('fit') as Classification | '';
		classification = fit === 'GOOD_FIT' || fit === 'MAYBE' || fit === 'REJECT' ? fit : '';
	});

	const q = useJobsInfiniteFromUrl();

	const flat = $derived(($q.data?.pages ?? []).flatMap((p) => p.items));
	const backTo = $derived.by(() => {
		const qs = $page.url.searchParams.toString();
		return qs ? `/jobs?${qs}` : '/jobs';
	});

	function pushUrl(next: {
		classification: Classification | '';
		keyword: string;
		postedAfter: string;
	}): void {
		classification = next.classification;
		keyword = next.keyword;
		postedAfter = next.postedAfter;
		const p = new URLSearchParams();
		if (keyword) p.set('q', keyword);
		if (postedAfter) p.set('posted', postedAfter);
		if (classification) p.set('fit', classification);
		const qs = p.toString();
		void goto(qs ? `?${qs}` : '?', { replaceState: true, keepFocus: true, noScroll: true });
	}

	let sentinel = $state<HTMLDivElement | null>(null);

	$effect(() => {
		if (!sentinel) return;
		const ob = new IntersectionObserver(([e]) => {
			const st = get(q);
			if (e.isIntersecting && st.hasNextPage && !st.isFetchingNextPage) {
				void st.fetchNextPage();
			}
		});
		ob.observe(sentinel);
		return () => ob.disconnect();
	});
</script>

<svelte:head>
	<title>Jobs — Kaziro</title>
</svelte:head>

<div class="flex h-full min-h-0 flex-col overflow-hidden">
	<div class="mb-4">
		<JobFilters {classification} {keyword} {postedAfter} onChange={pushUrl} />
	</div>

	{#if $q.isPending}
		<p class="text-base-content/60 pt-6 text-sm">Loading jobs…</p>
	{:else if $q.isError}
		<p class="text-error pt-6 text-sm">Could not load jobs.</p>
	{:else}
		<div class="scroll-region min-h-0 flex-1 overflow-y-auto px-2">
			{#if flat.length > 100}
				<p class="text-base-content/60 mb-2 text-xs" role="status">
					Showing {flat.length} loaded jobs — refine filters to narrow results.
				</p>
			{/if}
			{#each flat as job (job.id)}
				<div class="mb-3 first:mt-1">
					<JobCard {job} detailHref={`/jobs/${job.id}?backTo=${encodeURIComponent(backTo)}`} />
				</div>
			{/each}
			<div bind:this={sentinel} class="h-4"></div>
			{#if $q.isFetchingNextPage}
				<p class="text-base-content/60 py-3 text-center text-sm">Loading more…</p>
			{/if}
		</div>
	{/if}
</div>
