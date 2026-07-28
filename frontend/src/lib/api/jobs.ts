import { apiClient } from "@/lib/api/client";
import type {
  ApplicationDocText,
  JobEvaluation,
  JobListFilters,
  JobPosting,
  TriggerJobResponse,
} from "@/lib/api/types";

export async function listJobs(
  token: string,
  filters: JobListFilters = {},
): Promise<JobPosting[]> {
  const query = new URLSearchParams();
  if (filters.cursor) query.set("cursor", filters.cursor);
  if (filters.keyword) query.set("keyword", filters.keyword);
  if (filters.minScore !== undefined)
    query.set("min_score", String(filters.minScore));
  if (filters.remoteOnly !== undefined)
    query.set("remote_only", String(filters.remoteOnly));
  if (filters.postedAfter) query.set("posted_after", filters.postedAfter);
  filters.classification?.forEach((value) =>
    query.append("classification", value),
  );
  const suffix = query.size ? `?${query.toString()}` : "";
  return apiClient.get<JobPosting[]>(`/api/v1/jobs${suffix}`, token);
}

export const getJob = (token: string, id: string) =>
  apiClient.get<JobPosting>(`/api/v1/jobs/${id}`, token);

export const getJobEvaluation = (token: string, id: string) =>
  apiClient.get<JobEvaluation>(`/api/v1/jobs/${id}/evaluation`, token);

export const importJobUrl = (token: string, url: string, companyUrl?: string) =>
  apiClient.post<TriggerJobResponse>(
    "/api/v1/jobs/import-url",
    { url, company_url: companyUrl || null },
    token,
  );

export const triggerJobEvaluation = (token: string, id: string) =>
  apiClient.post<TriggerJobResponse>(
    `/api/v1/jobs/${id}/trigger-evaluation`,
    {},
    token,
  );

export const regenerateDocuments = (
  token: string,
  id: string,
  part: "all" | "cv" | "cover_letter" = "all",
) =>
  apiClient.post<TriggerJobResponse>(
    `/api/v1/jobs/${id}/regenerate-documents`,
    { part },
    token,
  );

export const updateJobDocuments = (
  token: string,
  id: string,
  tailoredCvText: string,
  coverLetterText: string,
) =>
  apiClient.put<ApplicationDocText>(
    `/api/v1/jobs/${id}/documents`,
    {
      tailored_cv_text: tailoredCvText,
      cover_letter_text: coverLetterText,
    },
    token,
  );

export const markJobNotInterested = (token: string, id: string) =>
  apiClient.post<JobEvaluation>(
    `/api/v1/jobs/${id}/mark-not-interested`,
    {},
    token,
  );
