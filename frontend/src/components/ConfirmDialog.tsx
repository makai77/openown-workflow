import * as AlertDialog from "@radix-ui/react-alert-dialog";

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel: string;
  cancelLabel?: string;
  onConfirm: () => void;
  // Tint for the confirm button — defaults to the destructive red used by the
  // Reject action elsewhere. Plain class strings, matching the rest of the app's
  // primitives (no cn/clsx helper).
  confirmClassName?: string;
}

// A small, accessible confirmation dialog built directly on Radix's AlertDialog
// primitives. Radix gives us the alertdialog role, focus trap, Escape-to-close,
// and aria-labelledby/aria-describedby wiring from Title/Description for free;
// the styling here is plain Tailwind to match Field/TextareaField/StatusBadge.
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  cancelLabel = "Cancel",
  onConfirm,
  confirmClassName = "rounded bg-red-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-800",
}: ConfirmDialogProps) {
  return (
    <AlertDialog.Root open={open} onOpenChange={onOpenChange}>
      <AlertDialog.Portal>
        <AlertDialog.Overlay className="fixed inset-0 bg-black/40" />
        <AlertDialog.Content className="fixed left-1/2 top-1/2 w-[90vw] max-w-sm -translate-x-1/2 -translate-y-1/2 space-y-4 rounded border bg-white p-5 shadow-lg">
          <AlertDialog.Title className="text-sm font-semibold">
            {title}
          </AlertDialog.Title>
          <AlertDialog.Description className="text-sm text-gray-600">
            {description}
          </AlertDialog.Description>
          <div className="flex justify-end gap-2">
            <AlertDialog.Cancel className="rounded border px-3 py-1.5 text-sm">
              {cancelLabel}
            </AlertDialog.Cancel>
            <AlertDialog.Action onClick={onConfirm} className={confirmClassName}>
              {confirmLabel}
            </AlertDialog.Action>
          </div>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  );
}
