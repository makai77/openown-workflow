// One Zod schema per boundary, reused for form validation and as the source of
// the form's TypeScript types — so runtime validation and TS types can't drift
// (FRONTEND_SETUP §5). Zod v4: string formats like email() are top-level.
import { z } from "zod";

import type { Category } from "@/api/applications";

export const CATEGORIES = [
  "GENERAL",
  "COMPLIANCE",
  "FINANCE",
  "OPERATIONS",
] as const satisfies readonly Category[];

export const CATEGORY_LABELS: Record<Category, string> = {
  GENERAL: "General",
  COMPLIANCE: "Compliance",
  FINANCE: "Finance",
  OPERATIONS: "Operations",
};

// Login. The backend authenticates by email (USERNAME_FIELD).
export const loginSchema = z.object({
  email: z.email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

export type LoginValues = z.infer<typeof loginSchema>;

// Create / edit a draft application. `description` and `amount` are always
// strings here (empty = "not provided"); the API layer maps "" to omitted/null.
// Keeping them non-optional keeps the inferred input and output types identical,
// which is what react-hook-form's resolver wants.
export const applicationFormSchema = z.object({
  title: z.string().trim().min(1, "Title is required"),
  category: z.enum(CATEGORIES),
  description: z.string(),
  amount: z
    .string()
    .refine(
      (value) => value === "" || /^\d+(\.\d{1,2})?$/.test(value),
      "Enter a valid amount, e.g. 1000.00",
    ),
});

export type ApplicationFormValues = z.infer<typeof applicationFormSchema>;

// Reject / return decision. The backend requires a non-blank comment for both
// (CommentRequired); this mirrors that as input validation only — it is never
// the reason the transition is legal or not. The backend remains the authority.
export const reviewDecisionSchema = z.object({
  comment: z.string().trim().min(1, "A comment is required"),
});

export type ReviewDecisionValues = z.infer<typeof reviewDecisionSchema>;
