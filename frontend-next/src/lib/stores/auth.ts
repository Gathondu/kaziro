"use client";

import {
  confirmEmail as confirmEmailRequest,
  getMe,
  login as loginRequest,
  refresh as refreshRequest,
  resendConfirmation as resendConfirmationRequest,
  signup as signupRequest,
  type LoginPayload,
  type SignupPayload,
} from "@/lib/api/auth";
import { ApiError, type SignupResponse, type TokenData, type UserAccount } from "@/lib/api/types";
import { create } from "zustand";

const SESSION_KEY = "kaziro.next.auth.v1";

type AuthState = {
  hydrated: boolean;
  token: TokenData | null;
  user: UserAccount | null;
  loadSession: () => Promise<void>;
  signup: (payload: SignupPayload) => Promise<SignupResponse>;
  login: (payload: LoginPayload) => Promise<void>;
  confirmEmail: (token: string) => Promise<void>;
  resendConfirmation: (email: string) => Promise<boolean>;
  logout: () => void;
};

export const useAuthStore = create<AuthState>((set, get) => ({
  hydrated: false,
  token: null,
  user: null,
  loadSession: async () => {
    if (typeof window === "undefined") {
      set({ hydrated: true });
      return;
    }
    const stored = readStoredToken();
    if (!stored) {
      set({ hydrated: true, token: null, user: null });
      return;
    }
    set({ token: stored });
    try {
      const user = await getMe(stored.access_token);
      set({ hydrated: true, user });
    } catch (error) {
      const refreshed = await tryRefresh(stored.refresh_token, error);
      if (!refreshed) {
        get().logout();
        set({ hydrated: true });
        return;
      }
      const user = await getMe(refreshed.access_token);
      persistToken(refreshed);
      set({ hydrated: true, token: refreshed, user });
    }
  },
  signup: (payload) => signupRequest(payload),
  login: async (payload) => {
    const token = await loginRequest(payload);
    const user = await getMe(token.access_token);
    persistToken(token);
    set({ hydrated: true, token, user });
  },
  confirmEmail: async (tokenValue) => {
    const confirmation = await confirmEmailRequest(tokenValue);
    const token = confirmation.token;
    const user = await getMe(token.access_token);
    persistToken(token);
    set({ hydrated: true, token, user });
  },
  resendConfirmation: async (email) => {
    const response = await resendConfirmationRequest(email);
    return response.confirmation_sent;
  },
  logout: () => {
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(SESSION_KEY);
    }
    set({ token: null, user: null });
  },
}));

async function tryRefresh(refreshToken: string, error: unknown): Promise<TokenData | null> {
  if (!(error instanceof ApiError) || error.status !== 401) {
    return null;
  }
  try {
    return await refreshRequest(refreshToken);
  } catch {
    return null;
  }
}

function persistToken(token: TokenData): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(SESSION_KEY, JSON.stringify(token));
}

function readStoredToken(): TokenData | null {
  if (typeof window === "undefined") {
    return null;
  }
  const raw = window.localStorage.getItem(SESSION_KEY);
  if (!raw) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as unknown;
    return isTokenData(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function isTokenData(value: unknown): value is TokenData {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return (
    typeof record.access_token === "string" &&
    typeof record.refresh_token === "string" &&
    record.token_type === "bearer" &&
    typeof record.expires_in === "number" &&
    typeof record.user_id === "string"
  );
}
