<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		open = $bindable(false),
		title,
		children,
		footer,
		boxClass = '',
		/** When false, the main body does not scroll; use for nested scroll (e.g. textarea). */
		scrollBody = true,
		/** When false, panel does not clip overflow (e.g. DaisyUI tooltips that use ::before). */
		clipOverflow = true
	}: {
		open?: boolean;
		title: string;
		children: Snippet;
		footer?: Snippet;
		/** Extra classes on the dialog panel (e.g. responsive max-width). */
		boxClass?: string;
		scrollBody?: boolean;
		clipOverflow?: boolean;
	} = $props();

	function close(): void {
		open = false;
	}
</script>

{#if open}
	<dialog class="modal modal-open">
		<div
			class="modal-box flex min-h-0 !max-h-[min(90vh,calc(100vh-2rem))] flex-col rounded-2xl border border-base-300 bg-base-100 {clipOverflow
				? '!overflow-hidden'
				: 'overflow-visible'} {boxClass}"
		>
			<h3 class="mb-3 shrink-0 text-lg font-semibold">{title}</h3>
			<div
				class="min-h-0 flex-1 py-2 {scrollBody
					? 'overflow-y-auto'
					: clipOverflow
						? 'flex flex-col overflow-hidden'
						: 'flex flex-col overflow-visible'}"
			>
				{@render children()}
			</div>
			<div class="modal-action shrink-0">
				{#if footer}
					{@render footer()}
				{:else}
					<button type="button" class="btn btn-ghost rounded-xl" onclick={close}>Close</button>
				{/if}
			</div>
		</div>
		<button type="button" class="modal-backdrop bg-neutral/40" aria-label="Close" onclick={close}
		></button>
	</dialog>
{/if}
