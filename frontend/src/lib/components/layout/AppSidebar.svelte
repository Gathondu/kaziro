<script lang="ts">
	import AppearanceIconSwitch from '$lib/components/layout/AppearanceIconSwitch.svelte';
	import { page } from '$app/stores';

	const path = $derived($page.url.pathname);

	const linkCls = (href: string) =>
		`block w-full rounded-xl px-3 py-2.5 text-left text-sm font-medium tracking-nav transition-colors ${
			path === href || path.startsWith(href + '/')
				? 'bg-primary text-primary-content'
				: 'text-base-content hover:bg-base-200'
		}`;
</script>

<aside
	class="border-base-300 bg-base-100 flex w-52 shrink-0 flex-col border-r"
	aria-label="Main navigation"
>
	<nav class="flex flex-1 flex-col gap-1 p-3" aria-label="Main">
		<a class={linkCls('/dashboard')} href="/dashboard">Dashboard</a>
		<a class={linkCls('/jobs')} href="/jobs">Jobs</a>
		<a class={linkCls('/applications')} href="/applications">Applications</a>
		<a class={linkCls('/settings')} href="/settings">Settings</a>
	</nav>
	<div class="border-base-300 flex flex-col gap-2 border-t p-3">
		<span class="text-base-content/60 text-xs font-medium tracking-wide uppercase">Appearance</span>
		<AppearanceIconSwitch />
	</div>
</aside>
