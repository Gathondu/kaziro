import { Suspense } from "react";
import { ConfirmEmailPanel } from "@/components/auth/ConfirmEmailPanel";

export default function ConfirmEmailPage() {
  return (
    <Suspense fallback={<span className="loading loading-spinner text-primary" />}>
      <ConfirmEmailPanel />
    </Suspense>
  );
}
