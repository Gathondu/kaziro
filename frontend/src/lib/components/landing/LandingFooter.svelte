<script lang="ts">
	const year = new Date().getFullYear();
</script>

<footer class="border-t border-base-300/80 bg-base-200/40 px-4 py-10">
	<div class="mx-auto flex max-w-6xl flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
		<p class="text-sm text-base-content/70">© {year} Kaziro. All rights reserved.</p>
		<nav class="flex flex-wrap gap-x-6 gap-y-2 text-sm" aria-label="Footer">
			<a href="/privacy" class="link-hover link text-base-content/80">Privacy</a>
			<a href="/terms" class="link-hover link text-base-content/80">Terms</a>
			<a href="/login" class="link-hover link text-base-content/80">Log in</a>
			<a href="/signup" class="link-hover link text-base-content/80">Create account</a>
		</nav>
	</div>
</footer>
