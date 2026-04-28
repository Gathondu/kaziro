<script lang="ts">
	import type { Classification } from '$lib/types/enums';

	const {
		classification,
		keyword,
		postedAfter,
		onChange
	}: {
		classification: Classification | '';
		keyword: string;
		postedAfter: string;
		onChange: (next: {
			classification: Classification | '';
			keyword: string;
			postedAfter: string;
		}) => void;
	} = $props();

	function setClass(c: Classification | ''): void {
		onChange({ classification: c, keyword, postedAfter });
	}
</script>

<div class="border-base-300 bg-base-200 flex flex-col gap-3 rounded-2xl border p-4">
	<div class="flex min-w-0 flex-wrap items-end gap-3">
		<label class="block w-full min-w-0 flex-1 space-y-1.5 sm:min-w-[16rem]">
			<span class="text-sm font-medium">Keyword</span>
			<input
				class="bg-base-100 text-base-content placeholder:text-base-content/45 border-base-300 focus:border-primary focus:ring-primary/25 block w-full min-w-0 rounded-xl border px-3 py-2.5 transition-colors focus:ring-2 focus:outline-none"
				type="search"
				placeholder="Title, company, description…"
				value={keyword}
				oninput={(e) =>
					onChange({
						classification,
						keyword: (e.currentTarget as HTMLInputElement).value,
						postedAfter
					})}
			/>
		</label>
		<label class="block w-full max-w-xs min-w-0 space-y-1.5 sm:w-auto">
			<span class="text-sm font-medium">Posted after</span>
			<input
				class="bg-base-100 text-base-content border-base-300 focus:border-primary focus:ring-primary/25 block w-full min-w-0 rounded-xl border px-3 py-2.5 transition-colors focus:ring-2 focus:outline-none"
				type="date"
				value={postedAfter}
				oninput={(e) =>
					onChange({
						classification,
						keyword,
						postedAfter: (e.currentTarget as HTMLInputElement).value
					})}
			/>
		</label>
	</div>
	<div class="flex flex-wrap gap-2">
		<span class="self-center text-sm font-medium">Fit:</span>
		<button
			type="button"
			class="btn btn-xs rounded-lg {classification === '' ? 'btn-primary' : 'btn-ghost'}"
			onclick={() => setClass('')}>All</button
		>
		<button
			type="button"
			class="btn btn-xs rounded-lg {classification === 'GOOD_FIT' ? 'btn-success' : 'btn-ghost'}"
			onclick={() => setClass('GOOD_FIT')}>Good fit</button
		>
		<button
			type="button"
			class="btn btn-xs rounded-lg {classification === 'MAYBE' ? 'btn-warning' : 'btn-ghost'}"
			onclick={() => setClass('MAYBE')}>Maybe</button
		>
		<button
			type="button"
			class="btn btn-xs rounded-lg {classification === 'REJECT' ? 'btn-error' : 'btn-ghost'}"
			onclick={() => setClass('REJECT')}>Reject</button
		>
	</div>
</div>
