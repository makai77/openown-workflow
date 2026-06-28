import type { AuditLogEntry } from "@/api/applications";
import { StatusBadge } from "./StatusBadge";

// Pure render of the audit_logs timeline — no fetching, no business logic.
export function AuditTrail({ entries }: { entries: AuditLogEntry[] }) {
  if (entries.length === 0) {
    return <p className="text-sm text-gray-500">No history yet.</p>;
  }

  return (
    <ol data-testid="audit-trail" className="flex flex-col gap-3">
      {entries.map((entry) => (
        <li key={entry.id} className="border-l-2 border-gray-200 pl-3">
          <div className="flex items-center gap-2 text-sm">
            <StatusBadge status={entry.from_status} />
            <span aria-hidden="true">→</span>
            <StatusBadge status={entry.to_status} />
          </div>
          <p className="mt-1 text-xs text-gray-500">
            {entry.actor_name || entry.actor_email} ·{" "}
            {new Date(entry.created_at).toLocaleString()}
          </p>
          {entry.comment ? (
            <p className="mt-1 text-sm">{entry.comment}</p>
          ) : null}
        </li>
      ))}
    </ol>
  );
}
