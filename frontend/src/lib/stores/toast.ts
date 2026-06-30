import { create } from "zustand";

export type ToastTone = "success" | "error" | "info";

export type ToastMessage = {
  id: string;
  tone: ToastTone;
  message: string;
};

type ToastState = {
  toasts: ToastMessage[];
  push: (tone: ToastTone, message: string) => void;
  dismiss: (id: string) => void;
};

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  push: (tone, message) =>
    set((state) => ({
      toasts: [...state.toasts, { id: crypto.randomUUID(), tone, message }],
    })),
  dismiss: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((toast) => toast.id !== id),
    })),
}));
