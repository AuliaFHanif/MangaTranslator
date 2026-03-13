import { useProjectStore } from "@/stores/projectStore";
import { usePipelineSocket } from "@/hooks/usePipelineSocket";
import { Titlebar } from "@/components/Titlebar";
import { PageSidebar } from "@/components/PageSidebar";
import { PagePreview } from "@/components/PagePreview";
import { WelcomeScreen } from "@/components/WelcomeScreen";
import { startPipeline, stopPipeline } from "@/ipc/api";

function ErrorBanner() {
  const { error, setError } = useProjectStore();

  if (!error) return null;

  return (
    <div className="px-3 py-2 border-b border-red-900/60 bg-red-950/40 flex items-start justify-between gap-3 flex-shrink-0">
      <p className="font-mono text-xs text-red-300 leading-relaxed">{error}</p>
      <button
        onClick={() => setError(null)}
        className="px-2 py-1 border border-red-800/80 text-red-300 hover:bg-red-900/40 font-mono text-[10px] transition-colors"
      >
        DISMISS
      </button>
    </div>
  );
}

function RunButton() {
  const { project, isPipelineRunning, setPipelineRunning, setError } =
    useProjectStore();

  if (!project) return null;

  const runnableCount = project.pages.filter(
    (p) => p.status === "pending" || p.status === "error",
  ).length;

  async function handleRun() {
    if (!project) return;
    setError(null);
    try {
      const res = await startPipeline(project.folder_path);
      setPipelineRunning(Boolean(res?.is_running));
      if (!res?.enqueued) {
        const statusSummary = res?.status_counts
          ? Object.entries(res.status_counts)
              .map(([status, count]) => `${status}: ${count}`)
              .join(", ")
          : null;
        const message = statusSummary
          ? `Pipeline did not enqueue any pages. Current statuses: ${statusSummary}.`
          : "Pipeline did not enqueue any pages.";
        setError(message);
        console.warn("Pipeline started but no runnable pages were enqueued.", {
          statusCounts: res?.status_counts,
        });
      }
    } catch (e) {
      console.error("Failed to start pipeline", e);
      setPipelineRunning(false);
      setError(e instanceof Error ? e.message : "Failed to start pipeline");
    }
  }

  async function handleStop() {
    try {
      await stopPipeline();
      setPipelineRunning(false);
    } catch (e) {
      console.error("Failed to stop pipeline", e);
      setError(e instanceof Error ? e.message : "Failed to stop pipeline");
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
      disabled={runnableCount === 0}
      className="flex items-center gap-2 px-3 py-1
        bg-amber-500 hover:bg-amber-400 disabled:bg-zinc-700
        text-zinc-950 disabled:text-zinc-500
        font-mono text-xs font-bold transition-colors"
    >
      ▶ RUN
      {runnableCount > 0 && (
        <span className="bg-zinc-950/30 px-1">{runnableCount}</span>
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

      <ErrorBanner />

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
