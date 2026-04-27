import { browser } from '$app/environment';
import type { LayoutLoad } from './$types';
import type { Appearance } from '$lib/stores/appearance.svelte';

function parseAppearanceCookie(value: string | undefined): Appearance {
	if (value === 'light' || value === 'dark' || value === 'system') {
		return value;
	}
	return 'system';
}

function readAppearanceFromDocumentCookie(): Appearance {
	if (!browser) {
		return 'system';
	}
	const pair = document.cookie
		.split(';')
		.map((chunk) => chunk.trim())
		.find((chunk) => chunk.startsWith('appearance='));

	return parseAppearanceCookie(pair?.split('=').slice(1).join('='));
}

export const load: LayoutLoad = async () => {
	return {
		appearance: readAppearanceFromDocumentCookie()
	};
};
