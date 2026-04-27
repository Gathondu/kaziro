import { test, expect } from '@playwright/test';

test('home shows marketing and auth links', async ({ page }) => {
	await page.goto('/');
	await expect(page.getByRole('heading', { name: /Job search that works with you/ })).toBeVisible();
	await expect(page.getByRole('heading', { name: 'How it works' })).toBeVisible();
	await expect(page.getByRole('link', { name: 'Log in' }).first()).toBeVisible();
	await expect(page.getByRole('link', { name: 'Create account' }).first()).toBeVisible();
});

test('privacy placeholder renders', async ({ page }) => {
	await page.goto('/privacy');
	await expect(page.getByRole('heading', { name: 'Privacy policy' })).toBeVisible();
});

test('login page renders', async ({ page }) => {
	await page.goto('/login');
	await expect(page.getByRole('heading', { name: 'Log in' })).toBeVisible();
});
