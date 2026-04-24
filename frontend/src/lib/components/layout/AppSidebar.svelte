<script lang="ts">
	import { page } from '$app/stores';
	import { isNotificationsConnected, subscribeConnection } from '$lib/stores/notifications';

	let wsOk = $state(false);
	$effect(() =>
		subscribeConnection(() => {
			wsOk = isNotificationsConnected();
		})
	);

	const path = $derived($page.url.pathname);

	const linkCls = (href: string) =>
		`block w-full rounded-xl px-3 py-2.5 text-left text-sm font-medium tracking-nav transition-colors ${
			path === href || path.startsWith(href + '/')
				? 'bg-primary text-primary-content'
				: 'text-base-content hover:bg-base-200'
		}`;
</script>

<aside
	class="flex w-52 shrink-0 flex-col border-r border-base-300 bg-base-100"
	aria-label="Main navigation"
>
	<nav class="flex flex-1 flex-col gap-1 p-3" aria-label="Main">
		<a class={linkCls('/dashboard')} href="/dashboard">Dashboard</a>
		<a class={linkCls('/jobs')} href="/jobs">Jobs</a>
		<a class={linkCls('/applications')} href="/applications">Applications</a>
		<a class={linkCls('/settings')} href="/settings">Settings</a>
		<a class={linkCls('/onboarding')} href="/onboarding/profile">Onboarding</a>
	</nav>
	<div class="border-t border-base-300 p-3">
		<span
			class="badge rounded-lg font-medium {wsOk ? 'badge-success' : 'badge-ghost'}"
			title="Realtime connection"
		>
			{wsOk ? 'Live' : 'Offline'}
		</span>
	</div>
</aside>
