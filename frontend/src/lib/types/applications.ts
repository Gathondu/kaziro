import type { ApplicationEventType, ApplicationStatus } from './enums';
import type { JobEvaluation, JobPosting } from './jobs';

export interface ApplicationDocSnippet {
	id: string;
	tailored_cv_text: string;
	cover_letter_text: string;
	cv_pdf_path: string | null;
	cover_letter_pdf_path: string | null;
	quality_passed: boolean;
	last_edited_at: string;
}

export interface ApplicationEvent {
	id: string;
	event_type: ApplicationEventType;
	event_date: string;
	from_status: string | null;
	to_status: string | null;
	notes: string | null;
	actor_user_id: string | null;
}

export interface Application {
	id: string;
	user_id: string;
	job_posting_id: string;
	application_doc_id: string;
	status: ApplicationStatus;
	applied_at: string | null;
	notes: string | null;
	created_at: string;
	updated_at: string;
	job_posting: JobPosting | null;
	application_doc: ApplicationDocSnippet | null;
	evaluation: JobEvaluation | null;
}

export interface ApplicationDetail extends Application {
	events: ApplicationEvent[];
}
