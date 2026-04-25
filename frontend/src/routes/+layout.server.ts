import type { LayoutServerLoad } from './$types';
import type { Appearance } from '$lib/stores/appearance.svelte';

function parseAppearanceCookie(value: string | undefined): Appearance {
	if (value === 'light' || value === 'dark' || value === 'system') {
		return value;
	}
	return 'system';
}

export const load: LayoutServerLoad = async ({ cookies }) => {
	return {
		appearance: parseAppearanceCookie(cookies.get('appearance'))
	};
};
