import type { PageStatus } from "@/stores/projectStore";

const STATUS_CONFIG: Record<PageStatus, { label: string; color: string }> = {
  pending:     { label: "PENDING",     color: "text-zinc-500 bg-zinc-800" },
  detecting:   { label: "DETECTING",   color: "text-blue-400 bg-blue-900/40" },
  ocr:         { label: "OCR",         color: "text-cyan-400 bg-cyan-900/40" },
  translating: { label: "TRANSLATING", color: "text-amber-400 bg-amber-900/40" },
  inpainting:  { label: "INPAINTING",  color: "text-purple-400 bg-purple-900/40" },
  typesetting: { label: "TYPESETTING", color: "text-pink-400 bg-pink-900/40" },
  review:      { label: "REVIEW",      color: "text-yellow-300 bg-yellow-900/40" },
  done:        { label: "DONE",        color: "text-green-400 bg-green-900/40" },
  error:       { label: "ERROR",       color: "text-red-400 bg-red-900/40" },
};

export function StatusBadge({ status }: { status: PageStatus }) {
  const { label, color } = STATUS_CONFIG[status];
  return (
    <span className={`font-mono text-[10px] px-1.5 py-0.5 rounded ${color}`}>
      {label}
    </span>
  );
}