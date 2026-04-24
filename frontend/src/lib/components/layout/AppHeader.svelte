<script lang="ts">
	import { goto } from '$app/navigation';
	import { UserRound } from 'lucide-svelte';
	import { signOutEverywhere } from '$lib/stores/auth';
	import { isNotificationsConnected, subscribeConnection } from '$lib/stores/notifications';

	let wsOk = $state(false);
	$effect(() =>
		subscribeConnection(() => {
			wsOk = isNotificationsConnected();
		})
	);

	async function logout(): Promise<void> {
		await signOutEverywhere();
		await goto('/login');
	}
</script>

<header
	class="sticky top-0 z-40 flex items-center justify-between gap-3 border-b border-base-300 bg-base-100 px-4 py-3"
>
	<a href="/dashboard" class="text-lg font-semibold text-primary">Kaziro</a>
	<div class="flex items-center gap-2">
		<span
			class="badge rounded-lg font-medium {wsOk ? 'badge-success' : 'badge-ghost'}"
			title="Realtime connection"
		>
			{wsOk ? 'Live' : 'Offline'}
		</span>
		<div class="dropdown dropdown-end">
			<button
				type="button"
				tabindex="0"
				class="btn btn-circle btn-ghost btn-sm"
				aria-label="Account menu"
			>
				<UserRound class="size-6" aria-hidden="true" />
			</button>
			<ul
				class="menu dropdown-content z-50 mt-2 w-52 rounded-box border border-base-300 bg-base-100 p-2 shadow-sm"
			>
				<li>
					<a href="/settings" class="rounded-lg">Settings</a>
				</li>
				<li>
					<button type="button" class="rounded-lg" onclick={() => logout()}>Log out</button>
				</li>
			</ul>
		</div>
	</div>
</header>
