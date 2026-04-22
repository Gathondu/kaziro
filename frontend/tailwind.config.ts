import type { Config } from 'tailwindcss';
import daisyui from 'daisyui';

const config: Config = {
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {}
	},
	plugins: [daisyui],
	daisyui: {
		themes: ['light', 'dark'],
		logs: false
	}
};

export default config;
