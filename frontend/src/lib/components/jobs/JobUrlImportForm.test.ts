import { fireEvent, render, screen } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import JobUrlImportForm from './JobUrlImportForm.svelte';

const mutateAsync = vi.fn();

vi.mock('$lib/hooks/useJobs', () => ({
	useImportJobUrl: () =>
		readable({
			isPending: false,
			mutateAsync
		})
}));

vi.mock('$lib/stores/toast', () => ({
	toast: {
		info: vi.fn(),
		error: vi.fn()
	}
}));

describe('JobUrlImportForm', () => {
	it('shows a field error for empty submits', async () => {
		render(JobUrlImportForm);

		await fireEvent.submit(screen.getByRole('form', { name: 'Import a job from URL' }));

		expect(screen.getByText('Paste a job post URL first.')).toBeTruthy();
	});

	it('queues a valid URL', async () => {
		mutateAsync.mockResolvedValueOnce({ task_id: 'task-1', duplicate: false });
		render(JobUrlImportForm);

		await fireEvent.input(screen.getByLabelText('Job post URL'), {
			target: { value: 'https://jobs.example.com/role' }
		});
		await fireEvent.submit(screen.getByRole('form', { name: 'Import a job from URL' }));

		expect(mutateAsync).toHaveBeenCalledWith(['https://jobs.example.com/role', null]);
		const { toast } = await import('$lib/stores/toast');
		expect(toast.info).toHaveBeenCalledWith('Job processing started.');
	});
});
