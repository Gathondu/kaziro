import { Suspense } from "react";
import { LoginForm } from "@/components/auth/LoginForm";

export default function LoginPage() {
  return (
    <Suspense
      fallback={<span className="loading loading-spinner text-primary" />}
    >
      <LoginForm />
    </Suspense>
  );
}
