<script lang="ts">
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import LandingFeatures from '$lib/components/landing/LandingFeatures.svelte';
	import LandingFooter from '$lib/components/landing/LandingFooter.svelte';
	import LandingHeader from '$lib/components/landing/LandingHeader.svelte';
	import LandingHero from '$lib/components/landing/LandingHero.svelte';
	import LandingHowItWorks from '$lib/components/landing/LandingHowItWorks.svelte';
	import LandingWhy from '$lib/components/landing/LandingWhy.svelte';
	import JsonLdInline from '$lib/components/seo/JsonLdInline.svelte';
	import { getPublicSiteUrl } from '$lib/env/public';
	import { getUser, waitForAuthReady } from '$lib/stores/auth';

	const seo = {
		title: 'Kaziro - AI-assisted job search and tailored applications',
		description:
			'Kaziro discovers roles, scores fit to your profile, researches companies, and drafts tailored CVs and cover letters so you can move faster with confidence.',
		siteName: 'Kaziro'
	};
	const siteOrigin = getPublicSiteUrl();
	const canonicalUrl = siteOrigin ? `${siteOrigin}/` : undefined;
	const jsonLd = JSON.stringify({
		'@context': 'https://schema.org',
		'@type': 'WebSite',
		name: 'Kaziro',
		...(canonicalUrl ? { url: canonicalUrl } : {})
	});

	$effect(() => {
		if (!browser) return;
		let cancelled = false;
		void (async () => {
			await waitForAuthReady();
			if (cancelled || !getUser()) return;
			await goto('/dashboard');
		})();
		return () => {
			cancelled = true;
		};
	});
</script>

<svelte:head>
	<meta name="robots" content="index,follow" />
	<title>{seo.title}</title>
	<meta name="description" content={seo.description} />
	{#if canonicalUrl}
		<link rel="canonical" href={canonicalUrl} />
	{/if}
	<meta property="og:title" content={seo.title} />
	<meta property="og:description" content={seo.description} />
	{#if canonicalUrl}
		<meta property="og:url" content={canonicalUrl} />
	{/if}
	<meta property="og:type" content="website" />
	<meta property="og:site_name" content={seo.siteName} />
	<meta name="twitter:card" content="summary" />
	<meta name="twitter:title" content={seo.title} />
	<meta name="twitter:description" content={seo.description} />
</svelte:head>

<JsonLdInline {jsonLd} />

<div class="flex min-h-screen flex-col">
	<LandingHeader />
	<main class="flex-1">
		<LandingHero />
		<LandingFeatures />
		<LandingWhy />
		<LandingHowItWorks />
	</main>
	<LandingFooter />
</div>
