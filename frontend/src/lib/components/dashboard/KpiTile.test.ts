import { render, screen } from '@testing-library/svelte';
import { describe, it, expect } from 'vitest';
import KpiTile from './KpiTile.svelte';

describe('KpiTile', () => {
	it('renders label and value', () => {
		render(KpiTile, { props: { label: 'Test KPI', value: 42, hint: 'hint' } });
		expect(screen.getByText('Test KPI')).toBeTruthy();
		expect(screen.getByText('42')).toBeTruthy();
		expect(screen.getByText('hint')).toBeTruthy();
	});
});
