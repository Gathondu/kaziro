import type { Classification } from './enums';

/** Server → client payloads (Redis fan-out + WS). */
export type NotificationMessage =
	| { type: 'ping'; ts: number }
	| { type: 'pong'; ts: number }
	| { type: 'fetch_complete'; config_id: string; new_jobs: number }
	| {
			type: 'evaluation_complete';
			job_posting_id: string;
			classification: Classification;
			score: number;
	  }
	| { type: 'research_complete'; job_posting_id: string }
	| {
			type: 'documents_ready';
			/** Present when the evaluation row was resolved for fan-out. */
			job_posting_id?: string;
			job_evaluation_id: string;
			application_doc_id?: string | null;
			quality_passed: boolean;
	  }
	| {
			type: 'application_event';
			application_id: string;
			event_type: string;
			from_status: string | null;
			to_status: string | null;
	  };
