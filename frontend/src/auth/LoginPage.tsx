import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate } from "react-router-dom";

import { ApiError } from "@/api/client";
import { ErrorState } from "@/components/ErrorState";
import { Field } from "@/components/Field";
import { loginSchema } from "@/lib/schemas";
import type { LoginValues } from "@/lib/schemas";
import { useDocumentTitle } from "@/lib/useDocumentTitle";

import { useAuth } from "./context";

// Sign-in screen. Client-side validation is a convenience (empty/invalid email);
// the backend is the authority on credentials. On success we route by role.
export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);
  useDocumentTitle("Sign in");
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  async function onSubmit(values: LoginValues) {
    setFormError(null);
    try {
      const user = await login(values.email, values.password);
      navigate(
        user.role === "REVIEWER" ? "/reviewer/applications" : "/applications",
        { replace: true },
      );
    } catch (error) {
      setFormError(
        error instanceof ApiError && error.status === 400
          ? "Incorrect email or password."
          : "Could not sign in. Please try again.",
      );
    }
  }

  return (
    <main className="mx-auto grid min-h-svh max-w-sm place-items-center p-6">
      <form
        onSubmit={handleSubmit(onSubmit)}
        className="w-full space-y-4"
        noValidate
      >
        <div>
          <h1 className="text-xl font-semibold">Sign in</h1>
          <p className="text-sm text-gray-500">Open Ownership Workflow</p>
        </div>
        <Field
          label="Email"
          type="email"
          autoComplete="username"
          error={errors.email?.message}
          {...register("email")}
        />
        <Field
          label="Password"
          type="password"
          autoComplete="current-password"
          error={errors.password?.message}
          {...register("password")}
        />
        {formError ? <ErrorState message={formError} /> : null}
        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full rounded bg-brand px-3 py-2 text-sm font-medium text-white hover:bg-brand-hover disabled:opacity-50"
        >
          {isSubmitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </main>
  );
}
