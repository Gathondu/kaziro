import js from '@eslint/js';
import ts from 'typescript-eslint';
import svelte from 'eslint-plugin-svelte';
import prettier from 'eslint-config-prettier';
import globals from 'globals';

/** @type {import('eslint').Linter.Config[]} */
export default [
	js.configs.recommended,
	...ts.configs.recommended,
	...svelte.configs['flat/recommended'],
	prettier,
	...svelte.configs['flat/prettier'],
	{
		languageOptions: {
			globals: {
				...globals.browser,
				...globals.node
			}
		}
	},
	{
		files: ['**/*.svelte'],
		languageOptions: {
			parserOptions: {
				parser: ts.parser
			}
		}
	},
	{
		files: ['src/**/*.{js,ts}'],
		ignores: ['src/**/*.svelte.js', 'src/**/*.svelte.ts'],
		rules: {
			'no-restricted-globals': [
				'error',
				{
					name: '$state',
					message: 'Use $state only in .svelte, .svelte.js, or .svelte.ts files.'
				},
				{
					name: '$derived',
					message: 'Use $derived only in .svelte, .svelte.js, or .svelte.ts files.'
				},
				{
					name: '$effect',
					message: 'Use $effect only in .svelte, .svelte.js, or .svelte.ts files.'
				},
				{
					name: '$props',
					message: 'Use $props only in .svelte files.'
				},
				{
					name: '$bindable',
					message: 'Use $bindable only in .svelte files.'
				},
				{
					name: '$inspect',
					message: 'Use $inspect only in .svelte, .svelte.js, or .svelte.ts files.'
				},
				{
					name: '$host',
					message: 'Use $host only in .svelte files.'
				}
			]
		}
	},
	{
		ignores: [
			'build/**',
			'.svelte-kit/**',
			'.vercel/**',
			'dist/**',
			'node_modules/**',
			'coverage/**',
			'playwright-report/**',
			'test-results/**'
		]
	}
];
