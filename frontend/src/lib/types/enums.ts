/** Mirrors ``backend/db/models/enums.py`` string enums. */

export type Classification = 'GOOD_FIT' | 'MAYBE' | 'REJECT';

export type ApplicationStatus =
	| 'DRAFT'
	| 'SENT'
	| 'INTERVIEWING'
	| 'OFFERED'
	| 'REJECTED'
	| 'WITHDRAWN';

export type ApplicationEventType = 'CREATED' | 'STATUS_CHANGED' | 'NOTE_ADDED' | 'DOC_REGENERATED';
