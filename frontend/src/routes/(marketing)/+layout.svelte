<script lang="ts">
	import type { Snippet } from 'svelte';

	/**
	 * Public marketing + legal: inherits `data-theme` from `<html>` (appearance cookie,
	 * or `system` → `prefers-color-scheme`, same as `app.html` + `initAppearance`).
	 */
	const { children }: { children: Snippet } = $props();
</script>

<div
	data-marketing-surface
	class="min-h-screen bg-gradient-to-b from-base-100 via-base-100 to-base-200 text-base-content antialiased"
>
	{@render children()}
</div>
