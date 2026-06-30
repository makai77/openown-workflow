import { useEffect } from "react";

const SUFFIX = "Submission & Approval Workflow";

// Sets the browser tab title to "<page> · <app>", or just the app name when no
// page title is given (e.g. while a detail page is still loading).
export function useDocumentTitle(title?: string): void {
  useEffect(() => {
    document.title = title ? `${title} · ${SUFFIX}` : SUFFIX;
  }, [title]);
}
