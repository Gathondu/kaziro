import { render, screen } from '@testing-library/svelte';
import { describe, it, expect } from 'vitest';
import EvaluationPanel from './EvaluationPanel.svelte';
import type { JobEvaluation } from '$lib/types/jobs';

const mockEv: JobEvaluation = {
	id: '00000000-0000-4000-8000-000000000001',
	job_posting_id: '00000000-0000-4000-8000-000000000002',
	final_classification: 'GOOD_FIT',
	overall_score: 8.4,
	final_feedback: 'Strong alignment with backend role.',
	dimension_scores: { relevance: 9, impact: 8 },
	evaluated_at: new Date().toISOString(),
	created_at: new Date().toISOString(),
	updated_at: new Date().toISOString()
};

describe('EvaluationPanel', () => {
	it('shows classification and rationale', () => {
		render(EvaluationPanel, { props: { evaluation: mockEv } });
		expect(screen.getByText('GOOD_FIT')).toBeTruthy();
		expect(screen.getByText(/Strong alignment/)).toBeTruthy();
	});

	it('labels user-initiated rejections', () => {
		const userReject: JobEvaluation = {
			...mockEv,
			final_classification: 'REJECT',
			rejection_source: 'user'
		};
		render(EvaluationPanel, { props: { evaluation: userReject } });
		expect(screen.getByText('Rejected (by you)')).toBeTruthy();
	});
});
