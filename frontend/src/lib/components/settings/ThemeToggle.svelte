<script lang="ts">
	import { browser } from '$app/environment';

	let theme = $state<'terracotta' | 'terracotta_dark'>('terracotta');

	function readTheme(): void {
		if (!browser) return;
		const t = document.documentElement.getAttribute('data-theme');
		theme = t === 'terracotta_dark' ? 'terracotta_dark' : 'terracotta';
	}

	function setTheme(next: 'terracotta' | 'terracotta_dark'): void {
		if (!browser) return;
		document.documentElement.setAttribute('data-theme', next);
		try {
			localStorage.setItem('kaziro-theme', next);
		} catch {
			// ignore
		}
		theme = next;
	}

	$effect(() => {
		if (!browser) return;
		try {
			const saved = localStorage.getItem('kaziro-theme');
			if (saved === 'terracotta_dark' || saved === 'terracotta') {
				document.documentElement.setAttribute('data-theme', saved);
				theme = saved;
			}
		} catch {
			readTheme();
		}
	});
</script>

<div class="form-control max-w-xs">
	<span class="label-text text-sm font-medium">Theme</span>
	<div class="join rounded-xl border border-base-300">
		<button
			type="button"
			class="btn join-item btn-sm font-medium {theme === 'terracotta'
				? 'btn-primary'
				: 'btn-ghost'}"
			onclick={() => setTheme('terracotta')}>Light</button
		>
		<button
			type="button"
			class="btn join-item btn-sm font-medium {theme === 'terracotta_dark'
				? 'btn-primary'
				: 'btn-ghost'}"
			onclick={() => setTheme('terracotta_dark')}>Dark</button
		>
	</div>
</div>
