<script lang="ts">
	import type { Snippet } from 'svelte';

	const {
		type = 'button',
		variant = 'primary',
		disabled = false,
		class: className = '',
		onclick,
		children
	}: {
		type?: 'button' | 'submit';
		variant?: 'primary' | 'secondary' | 'ghost' | 'outline';
		disabled?: boolean;
		class?: string;
		onclick?: (e: MouseEvent) => void;
		children: Snippet;
	} = $props();

	const variantClass = $derived(
		(
			{
				primary: 'btn btn-primary font-medium',
				secondary: 'btn btn-secondary font-medium',
				ghost: 'btn btn-ghost font-medium',
				outline: 'btn btn-outline font-medium'
			} as const
		)[variant]
	);
</script>

<button {type} class="{variantClass} rounded-xl {className}" {disabled} {onclick}
	>{@render children()}</button
>
