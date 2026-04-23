<script lang="ts">
	const { children } = $props();
</script>

<div class="flex min-h-screen items-center justify-center bg-base-200 px-4 py-10">
	<div class="w-full max-w-md rounded-2xl border border-base-300 bg-base-100 p-6 shadow-sm">
		{@render children()}
	</div>
</div>
