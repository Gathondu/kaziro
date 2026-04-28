<script lang="ts">
	import { Moon, Sun, SunMoon } from 'lucide-svelte';
	import { appearance, setAppearance, type Appearance } from '$lib/stores/appearance.svelte';

	function pick(next: Appearance): void {
		setAppearance(next);
	}

	const btnBase =
		'btn btn-ghost btn-sm min-h-10 flex-1 rounded-lg border border-transparent transition-colors';
	const active = 'border-base-300 bg-base-200';
</script>

<div
	class="join join-horizontal border-base-300 bg-base-100 w-full border"
	role="group"
	aria-label="Color scheme"
>
	<button
		type="button"
		class="{btnBase} join-item {appearance.value === 'light' ? active : ''}"
		aria-pressed={appearance.value === 'light'}
		aria-label="Light theme"
		onclick={() => pick('light')}
	>
		<Sun class="size-4" aria-hidden="true" />
	</button>
	<button
		type="button"
		class="{btnBase} join-item {appearance.value === 'dark' ? active : ''}"
		aria-pressed={appearance.value === 'dark'}
		aria-label="Dark theme"
		onclick={() => pick('dark')}
	>
		<Moon class="size-4" aria-hidden="true" />
	</button>
	<button
		type="button"
		class="{btnBase} join-item {appearance.value === 'system' ? active : ''}"
		aria-pressed={appearance.value === 'system'}
		aria-label="Use system theme"
		onclick={() => pick('system')}
	>
		<SunMoon class="size-4" aria-hidden="true" />
	</button>
</div>
