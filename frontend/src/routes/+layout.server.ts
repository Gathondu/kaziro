import type { LayoutServerLoad } from './$types';
import type { Appearance } from '$lib/stores/appearance.svelte';

function parseAppearanceCookie(value: string | undefined): Appearance {
	if (value === 'light' || value === 'dark' || value === 'system') {
		return value;
	}
	return 'system';
}

/** Cookie `appearance` → `initAppearance` in root `+layout.svelte` (mirrors `app.html` pre-paint script). */
export const load: LayoutServerLoad = async ({ cookies }) => {
	return {
		appearance: parseAppearanceCookie(cookies.get('appearance'))
	};
};
