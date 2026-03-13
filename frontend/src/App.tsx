import { useProjectStore } from "@/stores/projectStore";
import { usePipelineSocket } from "@/hooks/usePipelineSocket";
import { Titlebar } from "@/components/Titlebar";
import { PageSidebar } from "@/components/PageSidebar";
import { PagePreview } from "@/components/PagePreview";
import { WelcomeScreen } from "@/components/WelcomeScreen";
import { getBackendUrlSync } from "@/ipc/backend";

function RunButton() {
  const { project, isPipelineRunning, setPipelineRunning } = useProjectStore();

  if (!project) return null;

  const pendingCount = project.pages.filter(
    (p) => p.status === "pending",
  ).length;

  async function handleRun() {
    if (!project) return;
    setPipelineRunning(true);
    try {
      await fetch(`${getBackendUrlSync()}/pipeline/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ folder_path: project.folder_path }),
      });
    } catch (e) {
      console.error("Failed to start pipeline", e);
      setPipelineRunning(false);
    }
  }

  async function handleStop() {
    setPipelineRunning(false);
    try {
      await fetch(`${getBackendUrlSync()}/pipeline/stop`, { method: "POST" });
    } catch (e) {
      console.error("Failed to stop pipeline", e);
    }
  }

  if (isPipelineRunning) {
    return (
      <button
        onClick={handleStop}
        className="flex items-center gap-2 px-3 py-1
          bg-red-500/20 hover:bg-red-500/30 border border-red-500/50
          font-mono text-xs text-red-400 transition-colors"
      >
        <span className="animate-pulse">■</span>
        STOP
      </button>
    );
  }

  return (
    <button
      onClick={handleRun}
      disabled={pendingCount === 0}
      className="flex items-center gap-2 px-3 py-1
        bg-amber-500 hover:bg-amber-400 disabled:bg-zinc-700
        text-zinc-950 disabled:text-zinc-500
        font-mono text-xs font-bold transition-colors"
    >
      ▶ RUN
      {pendingCount > 0 && (
        <span className="bg-zinc-950/30 px-1">{pendingCount}</span>
      )}
    </button>
  );
}

export default function App() {
  const { project } = useProjectStore();

  // Mount WebSocket listener for the lifetime of the app
  usePipelineSocket();

  return (
    <div className="flex flex-col h-screen bg-zinc-950 text-zinc-100 select-none overflow-hidden">
      {/* Titlebar with Run button */}
      <div className="flex items-center justify-between pr-2 flex-shrink-0">
        <Titlebar />
        <RunButton />
      </div>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {project ? (
          <>
            <PageSidebar />
            <PagePreview />
          </>
        ) : (
          <WelcomeScreen />
        )}
      </div>
    </div>
  );
}
