<script lang="ts">
	const year = new Date().getFullYear();
</script>

<footer
	class="relative border-t border-base-content/20 bg-gradient-to-b from-base-200 to-base-300/40 px-4 py-12"
>
	<div
		class="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/45 to-transparent"
		aria-hidden="true"
	></div>
	<div
		class="relative mx-auto flex max-w-6xl flex-col gap-8 sm:flex-row sm:items-center sm:justify-between"
	>
		<div>
			<p class="text-sm font-semibold text-base-content">Kaziro</p>
			<p class="mt-1 text-sm text-base-content/85">© {year} Kaziro. All rights reserved.</p>
		</div>
		<nav class="flex flex-wrap gap-x-8 gap-y-2 text-sm font-medium" aria-label="Footer">
			<a href="/privacy" class="link-hover link font-medium text-base-content">Privacy</a>
			<a href="/terms" class="link-hover link font-medium text-base-content">Terms</a>
			<a href="/login" class="link-hover link font-medium text-base-content">Log in</a>
			<a href="/signup" class="link-hover link text-primary">Create account</a>
		</nav>
	</div>
</footer>
