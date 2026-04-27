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
		await goto('/login');
	}
</script>

<header
	class="sticky top-0 z-40 flex items-center justify-between gap-3 border-b border-base-300 bg-base-100 px-4 py-3"
>
	<a href="/dashboard" class="text-lg font-semibold text-primary">Kaziro</a>
	<div class="flex items-center gap-2">
		<div class="dropdown dropdown-end">
			<button
				type="button"
				tabindex="0"
				class="btn btn-circle btn-ghost btn-sm relative"
				aria-label={wsAriaLabel(wsState)}
			>
				<UserRound class="size-6" aria-hidden="true" />
				<span
					class="absolute bottom-1 right-1 size-2 rounded-full ring-2 ring-base-100 {wsState === 'live'
						? 'bg-success'
						: wsState === 'pending'
							? 'bg-warning'
							: 'bg-error'}"
					aria-hidden="true"
					title={wsTitle(wsState)}
				></span>
			</button>
			<ul
				class="menu dropdown-content z-50 mt-2 w-52 rounded-box border border-base-300 bg-base-100 p-2 shadow-sm"
			>
				{#if $profile.isSuccess && $profile.data.full_name?.trim()}
					<li class="pointer-events-none border-b border-base-200 pb-2">
						<span
							class="block whitespace-normal break-words px-1 py-0.5 text-center text-xs font-semibold uppercase leading-snug text-base-content/70"
							aria-label="Signed in as {$profile.data.full_name}"
						>
							{$profile.data.full_name.trim()}
						</span>
					</li>
				{/if}
				<li>
					<a href="/settings?tab=profile" class="rounded-lg">Profile</a>
				</li>
				<li>
					<button type="button" class="rounded-lg" onclick={() => logout()}>Log out</button>
				</li>
			</ul>
		</div>
	</div>
</header>
