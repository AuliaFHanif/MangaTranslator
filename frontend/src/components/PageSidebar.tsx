import { useProjectStore } from "@/stores/projectStore";
import { StatusBadge } from "./StatusBadge";
import { getThumbnailUrl } from "@/ipc/api";

export function PageSidebar() {
  const { project, selectedPageIndex, setSelectedPage } = useProjectStore();

  if (!project) return null;

  return (
    <aside className="w-56 flex-shrink-0 border-r border-zinc-800 flex flex-col bg-zinc-950">
      {/* Header */}
      <div className="px-3 py-3 border-b border-zinc-800">
        <p className="font-mono text-[10px] text-zinc-500 uppercase tracking-widest">
          Pages
        </p>
        <p className="font-mono text-xs text-zinc-400 mt-0.5">
          {project.pages.length} total
        </p>
      </div>

      {/* Page list */}
      <div className="flex-1 overflow-y-auto">
        {project.pages.map((page) => {
          const isSelected = page.index === selectedPageIndex;
          return (
            <button
              key={page.id}
              onClick={() => setSelectedPage(page.index)}
              className={`w-full flex items-center gap-2.5 px-3 py-2.5 border-b border-zinc-800/50 transition-colors text-left
                ${
                  isSelected
                    ? "bg-amber-500/10 border-l-2 border-l-amber-500"
                    : "hover:bg-zinc-900 border-l-2 border-l-transparent"
                }`}
            >
              {/* Thumbnail */}
              <div className="w-9 h-12 flex-shrink-0 bg-zinc-800 rounded overflow-hidden">
                <img
                  src={getThumbnailUrl(
                    project.id,
                    project.folder_path,
                    page.index,
                  )}
                  alt={page.filename}
                  className="w-full h-full object-cover"
                  loading="lazy"
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = "none";
                  }}
                />
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <p
                  className={`font-mono text-xs truncate ${isSelected ? "text-amber-400" : "text-zinc-300"}`}
                >
                  {String(page.index + 1).padStart(3, "0")}
                </p>
                <div className="mt-1">
                  <StatusBadge status={page.status} />
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </aside>
  );
}
