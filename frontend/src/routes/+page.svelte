<script lang="ts">
	import LandingFeatures from '$lib/components/landing/LandingFeatures.svelte';
	import LandingFooter from '$lib/components/landing/LandingFooter.svelte';
	import LandingHeader from '$lib/components/landing/LandingHeader.svelte';
	import LandingHero from '$lib/components/landing/LandingHero.svelte';
	import LandingHowItWorks from '$lib/components/landing/LandingHowItWorks.svelte';
	import JsonLdInline from '$lib/components/seo/JsonLdInline.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
</script>

<svelte:head>
	<title>{data.seo.title}</title>
	<meta name="description" content={data.seo.description} />
	<link rel="canonical" href={data.canonicalUrl} />
	<meta property="og:title" content={data.seo.title} />
	<meta property="og:description" content={data.seo.description} />
	<meta property="og:url" content={data.canonicalUrl} />
	<meta property="og:type" content="website" />
	<meta property="og:site_name" content={data.seo.siteName} />
	<meta name="twitter:card" content="summary" />
	<meta name="twitter:title" content={data.seo.title} />
	<meta name="twitter:description" content={data.seo.description} />
</svelte:head>

<JsonLdInline jsonLd={data.jsonLd} />

<div class="flex min-h-screen flex-col">
	<LandingHeader />
	<main class="flex-1">
		<LandingHero />
		<LandingFeatures />
		<LandingHowItWorks />
	</main>
	<LandingFooter />
</div>
