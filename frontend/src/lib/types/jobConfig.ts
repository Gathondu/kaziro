export interface JobConfig {
	id: string;
	user_id: string;
	name: string | null;
	keywords: string[];
	location: string | null;
	remote_only: boolean;
	salary_min: number | null;
	salary_max: number | null;
	employment_types: string[];
	fetch_schedule_cron: string;
	is_active: boolean;
	created_at: string;
	updated_at: string;
}
