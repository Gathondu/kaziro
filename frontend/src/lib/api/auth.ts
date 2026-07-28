import { apiClient } from "@/lib/api/client";
import type {
  ConfirmationResponse,
  ResendConfirmationResponse,
  SignupResponse,
  TokenData,
  UserAccount,
} from "@/lib/api/types";

export type SignupPayload = {
  email: string;
  password: string;
  username: string;
};

export type LoginPayload = {
  identifier: string;
  password: string;
};

export function signup(payload: SignupPayload): Promise<SignupResponse> {
  return apiClient.post<SignupResponse>("/api/v1/auth/signup", payload);
}

export function login(payload: LoginPayload): Promise<TokenData> {
  return apiClient.post<TokenData>("/api/v1/auth/login", payload);
}

export function confirmEmail(token: string): Promise<ConfirmationResponse> {
  return apiClient.post<ConfirmationResponse>("/api/v1/auth/confirm-email", {
    token,
  });
}

export function resendConfirmation(
  email: string,
): Promise<ResendConfirmationResponse> {
  return apiClient.post<ResendConfirmationResponse>(
    "/api/v1/auth/resend-confirmation",
    {
      email,
    },
  );
}

export function refresh(refreshToken: string): Promise<TokenData> {
  return apiClient.post<TokenData>("/api/v1/auth/refresh", {
    refresh_token: refreshToken,
  });
}

export function getMe(token: string): Promise<UserAccount> {
  return apiClient.get<UserAccount>("/api/v1/auth/me", token);
}

export const forgotPassword = (email: string) =>
  apiClient.post<{ message: string }>("/api/v1/auth/forgot-password", {
    email,
  });

export const resetPassword = (token: string, newPassword: string) =>
  apiClient.post<{ message: string }>("/api/v1/auth/reset-password", {
    token,
    new_password: newPassword,
  });
