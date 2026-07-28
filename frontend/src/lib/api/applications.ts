import { apiClient } from "@/lib/api/client";
import type { ApplicationItem } from "@/lib/api/types";

export const listApplications = (token: string, status?: string) =>
  apiClient.get<ApplicationItem[]>(
    `/api/v1/applications${status ? `?status=${encodeURIComponent(status)}` : ""}`,
    token,
  );

export const getApplication = (token: string, id: string) =>
  apiClient.get<ApplicationItem>(`/api/v1/applications/${id}`, token);

export const createApplication = (token: string, jobPostingId: string) =>
  apiClient.post<ApplicationItem>(
    "/api/v1/applications",
    { job_posting_id: jobPostingId },
    token,
  );

export const updateApplicationNotes = (
  token: string,
  id: string,
  notes: string,
) =>
  apiClient.patch<ApplicationItem>(
    `/api/v1/applications/${id}`,
    { notes },
    token,
  );

export const updateApplicationDocs = (
  token: string,
  id: string,
  tailoredCvText: string,
  coverLetterText: string,
) =>
  apiClient.put<ApplicationItem>(
    `/api/v1/applications/${id}/docs`,
    {
      tailored_cv_text: tailoredCvText,
      cover_letter_text: coverLetterText,
    },
    token,
  );

export const updateApplicationStatus = (
  token: string,
  id: string,
  status: string,
) =>
  apiClient.put<ApplicationItem>(
    `/api/v1/applications/${id}/status`,
    { status },
    token,
  );

export const deleteApplication = (token: string, id: string) =>
  apiClient.deleteEmpty(`/api/v1/applications/${id}`, token);
