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
  created_at: string;
  updated_at: string;
};

export type CvUploadResponse = {
  storage_path: string;
  text_chars: number;
  has_master_cv: boolean;
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
