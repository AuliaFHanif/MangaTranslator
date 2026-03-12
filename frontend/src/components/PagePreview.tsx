import { useProjectStore } from "@/stores/projectStore";
import { StatusBadge } from "./StatusBadge";
import { getThumbnailUrl } from "@/ipc/api";

export function PagePreview() {
  const { project, selectedPageIndex } = useProjectStore();

  if (!project || project.pages.length === 0) return null;

  const page = project.pages[selectedPageIndex];
  if (!page) return null;

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
        <span className="font-mono text-xs text-zinc-600 ml-auto truncate max-w-xs">
          {page.filename}
        </span>
      </div>

      {/* Image area */}
      <div className="flex-1 overflow-auto flex items-start justify-center p-6 bg-zinc-950">
        <div className="relative shadow-2xl shadow-black/60">
          <img
            key={page.index}
            src={getThumbnailUrl(project.id, project.folder_path, page.index)}
            alt={page.filename}
            className="max-h-full max-w-full object-contain block"
            style={{ maxHeight: "calc(100vh - 140px)" }}
          />
          {/* Page number overlay */}
          <div className="absolute bottom-2 right-2 bg-black/70 px-2 py-0.5 font-mono text-[10px] text-amber-400">
            {String(page.index + 1).padStart(3, "0")}
          </div>
        </div>
      </div>
    </div>
  );
}
