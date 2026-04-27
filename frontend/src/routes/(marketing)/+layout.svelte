<script lang="ts">
	import type { Snippet } from 'svelte';

	/**
	 * Public marketing + legal pages always use light `terracotta`, independent of the
	 * user’s saved appearance (cookie / system) on `<html>`.
	 */
	const { children }: { children: Snippet } = $props();
</script>

<div data-theme="terracotta" class="min-h-screen bg-base-100 text-base-content">
	{@render children()}
</div>
