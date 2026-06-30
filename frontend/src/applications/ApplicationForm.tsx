import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate, useParams } from "react-router-dom";

import { ApiError } from "@/api/client";
import type { CreateApplicationPayload } from "@/api/applications";
import { ErrorState } from "@/components/ErrorState";
import { Field } from "@/components/Field";
import { LoadingState } from "@/components/LoadingState";
import { SelectField } from "@/components/SelectField";
import { TextareaField } from "@/components/TextareaField";
import { applicationFormSchema, CATEGORIES, CATEGORY_LABELS } from "@/lib/schemas";
import type { ApplicationFormValues } from "@/lib/schemas";
import { useDocumentTitle } from "@/lib/useDocumentTitle";

import {
  useApplication,
  useCreateApplication,
  useUpdateApplication,
} from "./hooks";

// The form maps blank text to the API's "absent" shape: amount "" -> null.
function toPayload(values: ApplicationFormValues): CreateApplicationPayload {
  return {
    title: values.title.trim(),
    category: values.category,
    description: values.description,
    amount: values.amount === "" ? null : values.amount,
  };
}

function serverErrorMessage(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : "Something went wrong. Please try again.";
}

interface ApplicationFormProps {
  heading: string;
  defaultValues: ApplicationFormValues;
  submitLabel: string;
  submitting: boolean;
  serverError: string | null;
  onSubmit: (values: ApplicationFormValues) => void;
}

function ApplicationForm({
  heading,
  defaultValues,
  submitLabel,
  submitting,
  serverError,
  onSubmit,
}: ApplicationFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ApplicationFormValues>({
    resolver: zodResolver(applicationFormSchema),
    defaultValues,
  });
  useDocumentTitle(heading);

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="max-w-lg space-y-4"
      noValidate
    >
      <h1 className="text-xl font-semibold">{heading}</h1>
      <Field label="Title" error={errors.title?.message} {...register("title")} />
      <SelectField
        label="Category"
        error={errors.category?.message}
        {...register("category")}
      >
        {CATEGORIES.map((category) => (
          <option key={category} value={category}>
            {CATEGORY_LABELS[category]}
          </option>
        ))}
      </SelectField>
      <TextareaField
        label="Description"
        rows={4}
        error={errors.description?.message}
        {...register("description")}
      />
      <Field
        label="Amount"
        inputMode="decimal"
        placeholder="1000.00"
        error={errors.amount?.message}
        {...register("amount")}
      />
      {serverError ? <ErrorState message={serverError} /> : null}
      <button
        type="submit"
        disabled={submitting}
        className="rounded bg-brand px-3 py-2 text-sm font-medium text-white hover:bg-brand-hover disabled:opacity-50"
      >
        {submitting ? "Saving…" : submitLabel}
      </button>
    </form>
  );
}

export function NewApplicationPage() {
  const navigate = useNavigate();
  const create = useCreateApplication();

  return (
    <ApplicationForm
      heading="New application"
      defaultValues={{
        title: "",
        category: "GENERAL",
        description: "",
        amount: "",
      }}
      submitLabel="Create draft"
      submitting={create.isPending}
      serverError={create.isError ? serverErrorMessage(create.error) : null}
      onSubmit={(values) =>
        create.mutate(toPayload(values), {
          onSuccess: (application) =>
            navigate(`/applications/${application.id}`),
        })
      }
    />
  );
}

export function EditApplicationPage() {
  const params = useParams();
  const id = Number(params.id);
  const navigate = useNavigate();
  const { data, isPending, isError, error, refetch } = useApplication(id);
  const update = useUpdateApplication(id);

  if (isPending) return <LoadingState />;
  if (isError) {
    return (
      <ErrorState
        message={serverErrorMessage(error)}
        onRetry={() => void refetch()}
      />
    );
  }
  // The backend rejects edits to non-editable applications; we mirror that here
  // only to avoid showing a form that can't be saved — it is not the guard.
  if (data.status !== "DRAFT" && data.status !== "RETURNED") {
    return <ErrorState message="This application can no longer be edited." />;
  }

  return (
    <ApplicationForm
      heading="Edit application"
      defaultValues={{
        title: data.title,
        category: data.category,
        description: data.description,
        amount: data.amount ?? "",
      }}
      submitLabel="Save changes"
      submitting={update.isPending}
      serverError={update.isError ? serverErrorMessage(update.error) : null}
      onSubmit={(values) =>
        update.mutate(toPayload(values), {
          onSuccess: () => navigate(`/applications/${id}`),
        })
      }
    />
  );
}
