<script lang="ts">
	import { goto } from '$app/navigation';
	import { UserRound } from 'lucide-svelte';
	import { useProfile } from '$lib/hooks/useProfile';
	import { signOutEverywhere } from '$lib/stores/auth';
	import {
		getNotificationsConnectionVisualState,
		subscribeConnection,
		type NotificationsConnectionVisualState
	} from '$lib/stores/notifications';

	const profile = useProfile();

	let wsState = $state<NotificationsConnectionVisualState>('offline');
	$effect(() =>
		subscribeConnection(() => {
			wsState = getNotificationsConnectionVisualState();
		})
	);

	function wsTitle(state: NotificationsConnectionVisualState): string {
		switch (state) {
			case 'live':
				return 'Realtime: connected';
			case 'pending':
				return 'Realtime: connecting…';
			case 'offline':
				return 'Realtime: disconnected';
		}
	}

	function wsAriaLabel(state: NotificationsConnectionVisualState): string {
		switch (state) {
			case 'live':
				return 'Account menu. Realtime connected.';
			case 'pending':
				return 'Account menu. Realtime connecting.';
			case 'offline':
				return 'Account menu. Realtime disconnected.';
		}
	}

	async function logout(): Promise<void> {
		await signOutEverywhere();
		await goto('/');
	}
</script>

<header
	class="border-base-300 bg-base-100 sticky top-0 z-40 flex items-center justify-between gap-3 border-b px-4 py-3"
>
	<a href="/dashboard" class="text-primary text-lg font-semibold">Kaziro</a>
	<div class="flex min-w-0 items-center gap-2">
		<details class="relative">
			<summary
				class="btn btn-circle btn-ghost btn-sm relative list-none [&::-webkit-details-marker]:hidden"
				aria-label={wsAriaLabel(wsState)}
			>
				<UserRound class="size-6" aria-hidden="true" />
				<span
					class="ring-base-100 absolute right-1 bottom-1 size-2 rounded-full ring-2 {wsState ===
					'live'
						? 'bg-success'
						: wsState === 'pending'
							? 'bg-warning'
							: 'bg-error'}"
					aria-hidden="true"
					title={wsTitle(wsState)}
				></span>
			</summary>
			<div
				class="border-base-300 bg-base-100 absolute top-full right-0 z-[60] mt-2 w-52 rounded-xl border p-2 shadow-lg"
				role="menu"
			>
				{#if $profile.isSuccess && $profile.data.full_name?.trim()}
					<div class="border-base-200 pointer-events-none border-b pb-2">
						<span
							class="text-base-content/70 block px-1 py-0.5 text-center text-xs leading-snug font-semibold break-words whitespace-normal uppercase"
							aria-label="Signed in as {$profile.data.full_name}"
						>
							{$profile.data.full_name.trim()}
						</span>
					</div>
				{/if}
				<nav class="flex flex-col gap-0.5">
					<a
						href="/settings?tab=profile"
						class="text-base-content hover:bg-base-200 block rounded-lg px-3 py-2 text-sm"
						role="menuitem">Profile</a
					>
					<button
						type="button"
						class="text-base-content hover:bg-base-200 block w-full rounded-lg px-3 py-2 text-left text-sm"
						role="menuitem"
						onclick={() => logout()}>Log out</button
					>
				</nav>
			</div>
		</details>
	</div>
</header>
