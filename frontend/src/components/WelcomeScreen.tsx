import { useProjectStore } from "@/stores/projectStore";
import { openProject } from "@/ipc/api";

export function WelcomeScreen() {
  const { setProject, setLoading, setError, isLoading } = useProjectStore();

  async function handleOpenFolder() {
    // Use Electron's native folder picker
    const folderPath = await window.electronAPI?.openFolderDialog();
    if (!folderPath) return;

    setLoading(true);
    setError(null);
    try {
      const { project } = await openProject(folderPath);
      setProject(project);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to open project");
    } finally {
      setLoading(false);
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
        </div>

        {/* Error display */}
        {useProjectStore.getState().error && (
          <p className="mt-4 font-mono text-xs text-red-400 border border-red-900/50 px-3 py-2">
            {useProjectStore.getState().error}
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