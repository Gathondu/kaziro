<script lang="ts">
	const year = new Date().getFullYear();
</script>

<footer
	class="border-base-content/20 from-base-200 to-base-300/40 relative border-t bg-gradient-to-b px-4 py-12"
>
	<div
		class="via-primary/45 pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent to-transparent"
		aria-hidden="true"
	></div>
	<div
		class="relative mx-auto flex max-w-6xl flex-col gap-8 sm:flex-row sm:items-center sm:justify-between"
	>
		<div>
			<p class="text-base-content text-sm font-semibold">Kaziro</p>
			<p class="text-base-content/85 mt-1 text-sm">© {year} Kaziro. All rights reserved.</p>
		</div>
		<nav class="flex flex-wrap gap-x-8 gap-y-2 text-sm font-medium" aria-label="Footer">
			<a href="/privacy" class="link-hover link text-base-content font-medium">Privacy</a>
			<a href="/terms" class="link-hover link text-base-content font-medium">Terms</a>
			<a href="/login" class="link-hover link text-base-content font-medium">Log in</a>
			<a href="/signup" class="link-hover link text-primary">Create account</a>
		</nav>
	</div>
</footer>
