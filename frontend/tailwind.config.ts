import type { Config } from 'tailwindcss';
import daisyui from 'daisyui';

const config: Config = {
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			fontFamily: {
				sans: [
					'"Plus Jakarta Sans"',
					'ui-sans-serif',
					'system-ui',
					'-apple-system',
					'Segoe UI',
					'Roboto',
					'Helvetica Neue',
					'Arial',
					'sans-serif'
				]
			},
			letterSpacing: {
				nav: '0.2px'
			}
		}
	},
	plugins: [daisyui],
	daisyui: {
		themes: [
			{
				terracotta: {
					primary: '#C96A4A',
					'primary-focus': '#A5543B',
					'primary-content': '#FFFFFF',
					'base-100': '#F5EDE6',
					'base-200': '#EADFD6',
					'base-300': '#D8C8BC',
					'base-content': '#3A2E2A',
					secondary: '#E3A18B',
					accent: '#D9A441',
					neutral: '#3A2E2A',
					info: '#6C8FA3',
					success: '#7A9E7E',
					warning: '#D9A441',
					error: '#C65A5A'
				}
			},
			{
				terracotta_dark: {
					primary: '#C96A4A',
					'primary-focus': '#A5543B',
					'primary-content': '#FFFFFF',
					'base-100': '#1F1A18',
					'base-200': '#2A2320',
					'base-300': '#3A2E2A',
					'base-content': '#F5EDE6',
					secondary: '#A5543B',
					accent: '#D9A441',
					neutral: '#F5EDE6',
					info: '#6C8FA3',
					success: '#7A9E7E',
					warning: '#D9A441',
					error: '#C65A5A'
				}
			}
		],
		logs: false,
		darkTheme: 'terracotta_dark'
	}
};

export default config;
