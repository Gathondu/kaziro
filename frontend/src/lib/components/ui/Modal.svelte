<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		open = $bindable(false),
		title,
		children,
		footer,
		boxClass = ''
	}: {
		open?: boolean;
		title: string;
		children: Snippet;
		footer?: Snippet;
		/** Extra classes on the dialog panel (e.g. responsive max-width). */
		boxClass?: string;
	} = $props();

	function close(): void {
		open = false;
	}
</script>

{#if open}
	<dialog class="modal modal-open">
		<div
			class="modal-box rounded-2xl border border-base-300 bg-base-100 {boxClass}"
		>
			<h3 class="mb-3 text-lg font-semibold">{title}</h3>
			<div class="py-2">
				{@render children()}
			</div>
			<div class="modal-action">
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
