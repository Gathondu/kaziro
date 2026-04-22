import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		port: 5173,
		strictPort: true
	},
	test: {
		environment: 'jsdom',
		globals: true,
		include: ['tests/unit/**/*.{test,spec}.{js,ts}', 'src/**/*.{test,spec}.{js,ts}'],
		setupFiles: ['./tests/unit/setup.ts']
	}
});
