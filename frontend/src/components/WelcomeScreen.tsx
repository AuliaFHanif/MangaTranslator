import { useEffect, useRef, useState } from "react";
import { useProjectStore } from "@/stores/projectStore";
import { openProject } from "@/ipc/api";

export function WelcomeScreen() {
  const { setProject, setLoading, setError, isLoading, error } =
    useProjectStore();
  const [elapsed, setElapsed] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (isLoading) {
      setElapsed(0);
      intervalRef.current = setInterval(() => setElapsed((s) => s + 1), 1000);
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      setElapsed(0);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isLoading]);

  async function handleOpenFolder() {
    console.log("[open-folder] opening native folder picker");

    // Use Electron's native folder picker
    const folderPath = await window.electronAPI?.openFolderDialog();
    console.log("[open-folder] folder picker result", { folderPath });
    if (!folderPath) return;

    console.time("[open-folder] total");
    setLoading(true);
    setError(null);
    console.log("[open-folder] loading state enabled", { folderPath });

    try {
      const { project } = await openProject(folderPath);
      console.log("[open-folder] project loaded", {
        id: project.id,
        name: project.name,
        pageCount: project.pages.length,
      });
      setProject(project);
    } catch (err) {
      console.error("[open-folder] failed", err);
      setError(err instanceof Error ? err.message : "Failed to open project");
    } finally {
      setLoading(false);
      console.log("[open-folder] loading state disabled");
      console.timeEnd("[open-folder] total");
    }
  }

  return (
    <div className="flex-1 flex items-center justify-center bg-zinc-950">
      <div className="text-center max-w-sm">
        {/* Logo mark */}
        <div className="mx-auto mb-8 w-16 h-16 border-2 border-amber-500/60 flex items-center justify-center">
          <div className="w-8 h-8 border-2 border-amber-500 rotate-45" />
        </div>

        <h1 className="font-mono text-2xl font-bold text-zinc-100 tracking-tight">
          MANGA<span className="text-amber-500">TL</span>
        </h1>
        <p className="font-mono text-xs text-zinc-500 mt-1 tracking-widest uppercase">
          Batch Translation Engine
        </p>

        <div className="mt-10 space-y-3">
          <button
            onClick={handleOpenFolder}
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-3 px-6 py-3
              bg-amber-500 hover:bg-amber-400 disabled:bg-zinc-700
              text-zinc-950 disabled:text-zinc-500
              font-mono text-sm font-bold tracking-wider
              transition-colors duration-150"
          >
            {isLoading ? (
              <>
                <span className="animate-spin">⟳</span>
                LOADING...
              </>
            ) : (
              <>
                <span>▶</span>
                OPEN FOLDER
              </>
            )}
          </button>

          {/* Progress bar — shown while scanning/loading */}
          {isLoading && (
            <div className="space-y-1.5">
              {/* Indeterminate bar */}
              <div className="w-full h-0.5 bg-zinc-800 overflow-hidden">
                <div
                  className="h-full bg-amber-500 animate-[progress_1.4s_ease-in-out_infinite]"
                  style={{
                    width: "40%",
                    animation: "progress 1.4s ease-in-out infinite",
                  }}
                />
              </div>
              <p className="font-mono text-[10px] text-zinc-500 tracking-widest uppercase text-left">
                Scanning images
                <span className="animate-[ellipsis_1.2s_steps(4,end)_infinite]">
                  ...
                </span>
                <span className="float-right text-zinc-600">{elapsed}s</span>
              </p>
            </div>
          )}
        </div>

        {/* Error display */}
        {error && (
          <p className="mt-4 font-mono text-xs text-red-400 border border-red-900/50 px-3 py-2">
            {error}
          </p>
        )}

        {/* Hint */}
        <p className="mt-8 font-mono text-[10px] text-zinc-700 uppercase tracking-widest">
          Select a folder containing manga images
        </p>
      </div>
    </div>
  );
}
