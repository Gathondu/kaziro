<script lang="ts">
	import { Moon, Sun, SunMoon } from 'lucide-svelte';
	import { appearance, setAppearance, type Appearance } from '$lib/stores/appearance.svelte';

	function pick(next: Appearance): void {
		setAppearance(next);
	}

	const btnBase =
		'btn btn-ghost btn-sm min-h-10 flex-1 rounded-none border-y-0 border-transparent transition-colors';
	const active = 'border-base-300 bg-base-200';
</script>

<div
	class="border-base-300 bg-base-100 divide-base-300 inline-flex w-full divide-x overflow-hidden rounded-xl border"
	role="group"
	aria-label="Color scheme"
>
	<button
		type="button"
		class="{btnBase} {appearance.value === 'light' ? active : ''}"
		aria-pressed={appearance.value === 'light'}
		aria-label="Light theme"
		onclick={() => pick('light')}
	>
		<Sun class="size-4" aria-hidden="true" />
	</button>
	<button
		type="button"
		class="{btnBase} {appearance.value === 'dark' ? active : ''}"
		aria-pressed={appearance.value === 'dark'}
		aria-label="Dark theme"
		onclick={() => pick('dark')}
	>
		<Moon class="size-4" aria-hidden="true" />
	</button>
	<button
		type="button"
		class="{btnBase} {appearance.value === 'system' ? active : ''}"
		aria-pressed={appearance.value === 'system'}
		aria-label="Use system theme"
		onclick={() => pick('system')}
	>
		<SunMoon class="size-4" aria-hidden="true" />
	</button>
</div>
