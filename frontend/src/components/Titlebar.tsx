import { useQuery } from "@tanstack/react-query";
import { useProjectStore } from "@/stores/projectStore";
import { resolveBackendUrl } from "@/ipc/backend";

function Dot({ active, pulse }: { active: boolean; pulse?: boolean }) {
  return (
    <span
      className={`inline-block w-1.5 h-1.5 rounded-full
      ${active ? "bg-green-500" : "bg-zinc-700"}
      ${pulse && active ? "animate-pulse" : ""}
    `}
    />
  );
}

export function Titlebar() {
  const project = useProjectStore((s) => s.project);

  const { data } = useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const backend = await resolveBackendUrl();
      const res = await fetch(`${backend}/health/`);
      return res.json();
    },
    refetchInterval: 8_000,
  });

  return (
    <div
      className="h-9 flex items-center justify-between px-4 border-b border-zinc-800 bg-zinc-950 flex-shrink-0"
      style={{ WebkitAppRegion: "drag" } as React.CSSProperties}
    >
      {/* Left: app name + project */}
      <div className="flex items-center gap-3">
        <span className="font-mono text-xs font-bold text-amber-500 tracking-widest">
          MANGATL
        </span>
        {project && (
          <>
            <span className="text-zinc-700 font-mono text-xs">›</span>
            <span className="font-mono text-xs text-zinc-400 truncate max-w-xs">
              {project.name}
            </span>
            <span className="font-mono text-[10px] text-zinc-600">
              [{project.pages.length} pages]
            </span>
          </>
        )}
      </div>

      {/* Right: status indicators */}
      <div
        className="flex items-center gap-4"
        style={{ WebkitAppRegion: "no-drag" } as React.CSSProperties}
      >
        <div className="flex items-center gap-1.5">
          <Dot active={data?.status === "ok"} />
          <span className="font-mono text-[10px] text-zinc-600 uppercase tracking-wider">
            Backend
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <Dot active={data?.lmstudio_connected} pulse />
          <span className="font-mono text-[10px] text-zinc-600 uppercase tracking-wider">
            LM Studio
          </span>
        </div>
      </div>
    </div>
  );
}
