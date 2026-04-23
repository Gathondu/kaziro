import { test, expect } from '@playwright/test';

test('home shows auth links', async ({ page }) => {
	await page.goto('/');
	await expect(page.getByRole('heading', { name: 'Kaziro' })).toBeVisible();
	await expect(page.getByRole('link', { name: 'Log in' })).toBeVisible();
});

test('login page renders', async ({ page }) => {
	await page.goto('/login');
	await expect(page.getByRole('heading', { name: 'Log in' })).toBeVisible();
});
