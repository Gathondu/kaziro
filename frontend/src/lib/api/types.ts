export type ApiErrorBody = {
  code: string;
  message: string;
};

export type ApiEnvelope<TData, TMeta = Record<string, unknown> | null> = {
  data: TData | null;
  meta: TMeta;
  error: ApiErrorBody | null;
};

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export type TokenData = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
  user_id: string;
};

export type UserAccount = {
  id: string;
  email: string;
  username: string;
  subscription_tier: string;
  email_confirmed_at: string | null;
};

export type SignupResponse = {
  user_id: string;
  email: string;
  confirmation_required: boolean;
  confirmation_sent: boolean;
};

export type ConfirmationResponse = {
  user_id: string;
  email: string;
  confirmed_at: string;
  token: TokenData;
};

export type ResendConfirmationResponse = {
  confirmation_sent: boolean;
};

export type ProfilePayload = {
  full_name: string;
  professional_summary?: string | null;
  skills: string[];
  experience_years?: number | null;
  domain?: string | null;
  values_statement?: string | null;
  linkedin_url?: string | null;
};

export type ProfileResponse = ProfilePayload & {
  id: string;
  user_id: string;
  has_master_cv: boolean;
  cv_original_filename?: string | null;
  created_at: string;
  updated_at: string;
};

export type CvUploadResponse = {
  storage_path: string;
  original_filename: string;
  text_chars: number;
  embedding_dims?: number;
  signed_url?: string | null;
  has_master_cv: boolean;
};

export type CvDownloadResponse = {
  signed_url: string;
};

export type JobConfigPayload = {
  name?: string | null;
  keywords: string[];
  location?: string | null;
  remote_only: boolean;
  salary_min?: number | null;
  salary_max?: number | null;
  employment_types?: string[];
  fetch_schedule_cron: string;
  is_active?: boolean;
};

export type JobConfigResponse = JobConfigPayload & {
  id: string;
  user_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type SchedulePreset = {
  id: string;
  label: string;
  fetch_schedule_cron: string;
};

export type RunConfigResponse = {
  task_id: string;
};

export type NotificationItem = {
  id: string;
  event_type: string;
  title: string;
  body: string;
  payload: Record<string, unknown>;
  read_at: string | null;
  created_at: string;
};

export type NotificationListResponse = {
  items: NotificationItem[];
  unread_count: number;
};

export type NotificationStreamPayload =
  | {
      action: "SYNC";
      items: NotificationItem[];
      unread_count: number;
    }
  | {
      action: "NEW_ALERT";
      notification: NotificationItem;
      message?: string;
    }
  | {
      action: "MARK_ALL_READ";
      message?: string;
    }
  | {
      action: "MARK_SINGLE_READ";
      notification_id: string;
      message?: string;
    };

export type CompanySummary = {
  company_name: string;
  selected_website: string | null;
  mission: string;
  values: string;
  culture: string;
  tech_stack: string;
  team_size_approx: string;
  recent_news: string;
  ai_summary: string;
  field_citations: Record<string, string[]>;
  source_urls: string[];
  retrieved_at: string;
};

export type ApplicationDocText = {
  tailored_cv_text: string;
  cover_letter_text: string;
  cv_pdf_available: boolean;
  cover_letter_pdf_available: boolean;
};

export type JobEvaluation = {
  id: string;
  job_posting_id: string;
  application_id: string | null;
  final_classification: string;
  overall_score: number;
  final_feedback: string;
  dimension_scores: Record<string, unknown>;
  rejection_source: string | null;
  evaluated_at: string;
  application_doc: ApplicationDocText | null;
};

export type JobPosting = {
  id: string;
  external_job_id: string;
  title: string;
  company_name: string;
  company_website: string | null;
  location: string;
  remote_flag: boolean;
  salary_min: number | null;
  salary_max: number | null;
  employment_type: string;
  description: string;
  requirements: string[];
  application_url: string | null;
  posted_date: string | null;
  parsed_at: string;
  evaluation: JobEvaluation | null;
  company_summary: CompanySummary | null;
};

export type JobListFilters = {
  cursor?: string;
  classification?: string[];
  minScore?: number;
  remoteOnly?: boolean;
  postedAfter?: string;
  keyword?: string;
};

export type TriggerJobResponse = {
  task_id: string;
  duplicate: boolean;
};

export type ApplicationDocument = {
  id: string;
  tailored_cv_text: string;
  cover_letter_text: string;
  cv_pdf_available: boolean;
  cover_letter_pdf_available: boolean;
  quality_passed: boolean;
  quality_notes: string;
};

export type ApplicationEvent = {
  id: string;
  event_type: string;
  event_date: string;
  from_status: string;
  to_status: string;
  notes: string;
};

export type ApplicationItem = {
  id: string;
  job_posting_id: string;
  application_doc_id: string;
  status: string;
  applied_at: string | null;
  notes: string;
  created_at: string;
  updated_at: string;
  job_posting: JobPosting;
  application_doc: ApplicationDocument;
  evaluation: JobEvaluation;
  events?: ApplicationEvent[];
};
