import type { ComponentType, SVGProps } from "react";
import { CheckCircle2, Eye, FileText, Send, Undo2, XCircle } from "lucide-react";
import type { ApplicationStatus } from "@/api/applications";

type IconComponent = ComponentType<SVGProps<SVGSVGElement>>;

interface StatusMeta {
  label: string;
  Icon: IconComponent;
  className: string;
}

// One badge for all six statuses: icon + label + tint, never colour alone.
const STATUS_META: Record<ApplicationStatus, StatusMeta> = {
  DRAFT: {
    label: "Draft",
    Icon: FileText,
    className: "bg-gray-100 text-gray-700",
  },
  SUBMITTED: {
    label: "Submitted",
    Icon: Send,
    className: "bg-blue-100 text-blue-700",
  },
  UNDER_REVIEW: {
    label: "Under review",
    Icon: Eye,
    className: "bg-amber-100 text-amber-800",
  },
  APPROVED: {
    label: "Approved",
    Icon: CheckCircle2,
    className: "bg-green-100 text-green-700",
  },
  REJECTED: {
    label: "Rejected",
    Icon: XCircle,
    className: "bg-red-100 text-red-700",
  },
  RETURNED: {
    label: "Returned for changes",
    Icon: Undo2,
    className: "bg-purple-100 text-purple-700",
  },
};

export function StatusBadge({ status }: { status: ApplicationStatus }) {
  const { label, Icon, className } = STATUS_META[status];
  return (
    <span
      data-testid="status-badge"
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${className}`}
    >
      <Icon className="size-3.5" aria-hidden="true" />
      {label}
    </span>
  );
}
