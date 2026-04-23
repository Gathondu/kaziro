<script lang="ts">
	import type { Snippet } from 'svelte';

	const {
		variant = 'neutral',
		class: className = '',
		children
	}: {
		variant?: 'neutral' | 'success' | 'warning' | 'error' | 'info';
		class?: string;
		children: Snippet;
	} = $props();

	const cls = $derived(
		(
			{
				neutral: 'badge badge-ghost',
				success: 'badge badge-success',
				warning: 'badge badge-warning',
				error: 'badge badge-error',
				info: 'badge badge-info'
			} as const
		)[variant]
	);
</script>

<span class="{cls} rounded-lg font-medium {className}">{@render children()}</span>
