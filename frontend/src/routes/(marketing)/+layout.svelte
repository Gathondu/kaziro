<script lang="ts">
	import type { Snippet } from 'svelte';

	/**
	 * Public marketing + legal pages always use light `terracotta`, independent of the
	 * user’s saved appearance (cookie / system) on `<html>`.
	 */
	const { children }: { children: Snippet } = $props();
</script>

<div
	data-theme="terracotta"
	data-marketing-surface
	class="min-h-screen bg-gradient-to-b from-base-100 via-base-100 to-base-200 text-base-content antialiased"
>
	{@render children()}
</div>
