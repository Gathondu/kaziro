"use client";

import { X } from "lucide-react";
import { useEffect } from "react";
import { useToastStore, type ToastMessage } from "@/lib/stores/toast";

const toneClass: Record<ToastMessage["tone"], string> = {
  success: "alert-success",
  error: "alert-error",
  info: "alert-info",
};

export function ToastHost() {
  const toasts = useToastStore((state) => state.toasts);
  const dismiss = useToastStore((state) => state.dismiss);

  useEffect(() => {
    if (toasts.length === 0) {
      return;
    }
    const timer = window.setTimeout(() => {
      dismiss(toasts[0].id);
    }, 4500);
    return () => window.clearTimeout(timer);
  }, [dismiss, toasts]);

  if (toasts.length === 0) {
    return null;
  }

  return (
    <div className="toast toast-end z-50">
      {toasts.map((toast) => (
        <div
          className={`alert ${toneClass[toast.tone]} max-w-sm shadow-lg`}
          key={toast.id}
        >
          <span>{toast.message}</span>
          <button
            aria-label="Dismiss notification"
            className="btn btn-ghost btn-xs btn-circle"
            onClick={() => dismiss(toast.id)}
            type="button"
          >
            <X className="size-3.5" aria-hidden="true" />
          </button>
        </div>
      ))}
    </div>
  );
}
