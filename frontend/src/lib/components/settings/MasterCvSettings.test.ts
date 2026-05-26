import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import MasterCvSettings from './MasterCvSettings.svelte';

type StoreValue<T> = {
	subscribe: (run: (value: T) => void) => () => void;
};

const mocks = vi.hoisted(() => ({
	profileValue: {
		data: { has_master_cv: false },
		isPending: false,
		isError: false
	},
	cvUrlValue: {
		data: null as string | null,
		isPending: false,
		isError: false
	},
	uploadValue: {
		isPending: false,
		mutateAsync: vi.fn()
	},
	toastSuccess: vi.fn(),
	toastError: vi.fn()
}));

function storeFrom<T>(getValue: () => T): StoreValue<T> {
	return {
		subscribe(run: (value: T) => void): () => void {
			run(getValue());
			return () => undefined;
		}
	};
}

vi.mock('$lib/hooks/useProfile', () => ({
	useProfile: () => storeFrom(() => mocks.profileValue),
	useProfileCvPdfUrl: () => storeFrom(() => mocks.cvUrlValue),
	useCvUpload: () => storeFrom(() => mocks.uploadValue)
}));

vi.mock('$lib/stores/toast', () => ({
	toast: {
		success: mocks.toastSuccess,
		error: mocks.toastError
	}
}));

describe('MasterCvSettings', () => {
	beforeEach(() => {
		mocks.profileValue = {
			data: { has_master_cv: false },
			isPending: false,
			isError: false
		};
		mocks.cvUrlValue = {
			data: null,
			isPending: false,
			isError: false
		};
		mocks.uploadValue = {
			isPending: false,
			mutateAsync: vi.fn()
		};
		mocks.toastSuccess.mockReset();
		mocks.toastError.mockReset();
	});

	it('renders an empty state when no CV exists', () => {
		render(MasterCvSettings);

		expect(screen.getByText('No CV is uploaded yet.')).toBeTruthy();
		expect(screen.getByRole('button', { name: /upload cv/i })).toBeTruthy();
	});

	it('renders current CV preview and open link when a signed URL is available', () => {
		mocks.profileValue = {
			data: { has_master_cv: true },
			isPending: false,
			isError: false
		};
		mocks.cvUrlValue = {
			data: 'https://signed.example/master-cv.pdf',
			isPending: false,
			isError: false
		};

		render(MasterCvSettings);

		expect(screen.getByTitle('Current uploaded CV')).toBeTruthy();
		expect(screen.getByRole('link', { name: /open cv/i }).getAttribute('href')).toBe(
			'https://signed.example/master-cv.pdf'
		);
	});

	it('rejects non-PDF files before upload', async () => {
		render(MasterCvSettings);

		const input = screen.getByLabelText('Replacement CV PDF');
		const file = new File(['hello'], 'notes.txt', { type: 'text/plain' });
		await fireEvent.change(input, { target: { files: [file] } });

		expect(screen.getByText('Choose a PDF file.')).toBeTruthy();
		expect(screen.getByRole('button', { name: /upload cv/i }).hasAttribute('disabled')).toBe(true);
	});

	it('uploads a valid replacement PDF', async () => {
		mocks.uploadValue.mutateAsync.mockResolvedValueOnce({
			signed_url: 'https://signed.example/master-cv.pdf',
			storage_path: 'users/u/cv/master.pdf',
			text_chars: 100,
			embedding_dims: 1536,
			has_master_cv: true
		});
		render(MasterCvSettings);

		const input = screen.getByLabelText('Replacement CV PDF');
		const file = new File(['%PDF-1.4'], 'cv.pdf', { type: 'application/pdf' });
		await fireEvent.change(input, { target: { files: [file] } });
		await fireEvent.submit(screen.getByRole('form', { name: 'Replace current CV' }));

		expect(mocks.uploadValue.mutateAsync).toHaveBeenCalledWith(file);
		expect(mocks.toastSuccess).toHaveBeenCalledWith('CV updated.');
	});
});
