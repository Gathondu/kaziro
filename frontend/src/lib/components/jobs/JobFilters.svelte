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

<div class="flex flex-col gap-3 rounded-2xl border border-base-300 bg-base-200 p-4">
	<label class="form-control w-full max-w-md">
		<span class="label-text text-sm font-medium">Keyword</span>
		<input
			class="input input-bordered rounded-xl border-base-300 bg-base-100"
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
	<label class="form-control w-full max-w-xs">
		<span class="label-text text-sm font-medium">Posted after</span>
		<input
			class="input input-bordered rounded-xl border-base-300 bg-base-100"
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
