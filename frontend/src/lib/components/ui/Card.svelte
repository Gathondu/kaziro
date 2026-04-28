<script lang="ts">
	import type { Snippet } from 'svelte';

	const {
		class: className = '',
		children
	}: {
		class?: string;
		children: Snippet;
	} = $props();
</script>

<div class="border-base-300 bg-base-100 rounded-2xl border p-5 shadow-sm {className}">
	{@render children()}
</div>
