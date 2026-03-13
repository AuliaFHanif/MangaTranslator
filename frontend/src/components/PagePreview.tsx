import { useState } from "react";
import { useProjectStore } from "@/stores/projectStore";
import { StatusBadge } from "./StatusBadge";
import { getThumbnailUrl, getFinalImageUrl } from "@/ipc/api";

export function PagePreview() {
  const { project, selectedPageIndex } = useProjectStore();
  const [showFinal, setShowFinal] = useState(false);

  if (!project || project.pages.length === 0) return null;

  const page = project.pages[selectedPageIndex];
  if (!page) return null;

  const isDone = page.status === "done";
  const hasFinal = isDone && !!page.final_path;

  // Auto-switch to original if the page isn't done yet
  const displayFinal = showFinal && hasFinal;

  const imageSrc = displayFinal
    ? getFinalImageUrl(project.id, project.folder_path, page.index)
    : getThumbnailUrl(project.id, project.folder_path, page.index);

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Toolbar */}
      <div className="h-10 border-b border-zinc-800 flex items-center px-4 gap-4 flex-shrink-0">
        <span className="font-mono text-xs text-zinc-500">
          PAGE{" "}
          <span className="text-amber-400">
            {String(page.index + 1).padStart(3, "0")}
          </span>
          <span className="text-zinc-700 mx-2">/</span>
          {project.pages.length}
        </span>

        <StatusBadge status={page.status} />

        {/* Toggle — only shown when final image exists */}
        {hasFinal && (
          <div
            className="flex items-center border border-zinc-700 overflow-hidden font-mono text-[10px]"
            style={{ WebkitAppRegion: "no-drag" } as React.CSSProperties}
          >
            <button
              onClick={() => setShowFinal(false)}
              className={`px-2 py-1 transition-colors ${
                !displayFinal
                  ? "bg-amber-500 text-zinc-950 font-bold"
                  : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              ORIGINAL
            </button>
            <button
              onClick={() => setShowFinal(true)}
              className={`px-2 py-1 transition-colors ${
                displayFinal
                  ? "bg-amber-500 text-zinc-950 font-bold"
                  : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              TRANSLATED
            </button>
          </div>
        )}

        <span className="font-mono text-xs text-zinc-600 ml-auto truncate max-w-xs">
          {page.filename}
        </span>
      </div>

      {/* Image area */}
      <div className="flex-1 overflow-auto flex items-start justify-center p-6 bg-zinc-950">
        <div className="relative shadow-2xl shadow-black/60">
          <img
            key={`${page.index}-${displayFinal}`}
            src={imageSrc}
            alt={page.filename}
            className="max-h-full max-w-full object-contain block"
            style={{ maxHeight: "calc(100vh - 140px)" }}
          />

          {/* Page number overlay */}
          <div className="absolute bottom-2 right-2 bg-black/70 px-2 py-0.5 font-mono text-[10px] text-amber-400">
            {String(page.index + 1).padStart(3, "0")}
          </div>

          {/* Processing overlay — shown while page is being processed */}
          {!["pending", "done", "error", "review"].includes(page.status) && (
            <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
              <div className="font-mono text-xs text-amber-400 animate-pulse uppercase tracking-widest">
                {page.status}...
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}