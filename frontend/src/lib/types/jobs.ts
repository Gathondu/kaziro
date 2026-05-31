import type { Classification } from './enums';
import type { PageMeta } from './api';

export type { PageMeta };

export interface JobPosting {
	id: string;
	title: string;
	company_name: string;
	company_website: string | null;
	location: string | null;
	remote_flag: boolean;
	description: string;
	application_url: string;
	posted_date: string | null;
	parsed_at: string;
	created_at: string;
	updated_at: string;
}

/** Populated when the document agent has produced tailored text for this evaluation. */
export interface JobEvaluationApplicationDoc {
	tailored_cv_text: string;
	cover_letter_text: string;
	cv_pdf_available?: boolean;
	cover_letter_pdf_available?: boolean;
}

export interface JobEvaluation {
	id: string;
	job_posting_id: string;
	/** Present when the user has an application row for this posting (used to PATCH docs). */
	application_id?: string | null;
	final_classification: Classification;
	overall_score: number;
	final_feedback: string;
	dimension_scores: Record<string, unknown>;
	evaluated_at: string;
	created_at: string;
	updated_at: string;
	/** Present when the user marked the job not interested (still ``REJECT`` classification). */
	rejection_source?: 'user' | null;
	application_doc?: JobEvaluationApplicationDoc | null;
}

export interface TriggerEvaluationBody {
	task_id: string;
	duplicate: boolean;
}

export interface ImportJobUrlRequest {
	url: string;
	company_url?: string | null;
}
