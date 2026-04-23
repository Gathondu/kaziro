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

export interface JobEvaluation {
	id: string;
	job_posting_id: string;
	final_classification: Classification;
	overall_score: number;
	final_feedback: string;
	dimension_scores: Record<string, unknown>;
	evaluated_at: string;
	created_at: string;
	updated_at: string;
}

export interface TriggerEvaluationBody {
	task_id: string;
	duplicate: boolean;
}
