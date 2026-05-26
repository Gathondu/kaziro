export interface Profile {
	id: string;
	user_id: string;
	full_name: string;
	professional_summary: string | null;
	skills: string[];
	experience_years: number | null;
	domain: string | null;
	values_statement: string | null;
	linkedin_url: string | null;
	has_master_cv: boolean;
	created_at: string;
	updated_at: string;
}

export interface CvUploadResult {
	signed_url: string;
	storage_path: string;
	text_chars: number;
	embedding_dims: number;
	has_master_cv: boolean;
}

export interface CvDownloadResult {
	signed_url: string;
}
