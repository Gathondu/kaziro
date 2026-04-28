<script lang="ts">
	import { dismiss, getToasts, subscribeToasts, type ToastItem } from '$lib/stores/toast';

	let list = $state<ToastItem[]>([]);

	$effect(() =>
		subscribeToasts(() => {
			list = getToasts();
		})
	);
</script>

<div class="toast toast-end toast-bottom z-50 w-full max-w-sm gap-2">
	{#each list as t (t.id)}
		<div
			class="alert border-base-300 rounded-xl border shadow-sm {t.level === 'success'
				? 'alert-success'
				: t.level === 'warning'
					? 'alert-warning'
					: t.level === 'error'
						? 'alert-error'
						: 'alert-info'}"
			role="status"
		>
			<span class="text-sm font-medium">{t.message}</span>
			<button type="button" class="btn btn-ghost btn-xs rounded-lg" onclick={() => dismiss(t.id)}>
				Dismiss
			</button>
		</div>
	{/each}
</div>
