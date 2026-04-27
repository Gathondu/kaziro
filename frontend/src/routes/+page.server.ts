import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { getPublicSiteUrl } from '$lib/env/public';

const META_TITLE = 'Kaziro — AI-assisted job search and tailored applications';
const META_DESCRIPTION =
	'Kaziro discovers roles, scores fit to your profile, researches companies, and drafts tailored CVs and cover letters so you can move faster with confidence.';

export const load: PageServerLoad = async ({ locals, url }) => {
	const {
		data: { user }
	} = await locals.supabase.auth.getUser();
	if (user) {
		throw redirect(303, '/dashboard');
	}

	const siteOrigin = getPublicSiteUrl() ?? url.origin;
	const canonicalUrl = `${siteOrigin}/`;

	const jsonLd = JSON.stringify({
		'@context': 'https://schema.org',
		'@type': 'WebSite',
		name: 'Kaziro',
		url: canonicalUrl
	});

	return {
		canonicalUrl,
		jsonLd,
		seo: {
			title: META_TITLE,
			description: META_DESCRIPTION,
			siteName: 'Kaziro'
		}
	};
};
