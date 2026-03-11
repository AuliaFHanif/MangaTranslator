import { useQuery } from "@tanstack/react-query";

// Simple health badge shown in the corner during development
function BackendStatus() {
  const { data, isLoading } = useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const res = await fetch("http://127.0.0.1:8000/health/");
      return res.json();
    },
    refetchInterval: 10_000,
  });

  if (isLoading) return <span className="status-dot bg-yellow-500" />;

  return (
    <div className="flex items-center gap-2 text-xs text-zinc-400">
      <span
        className={`status-dot ${
          data?.status === "ok" ? "bg-green-500" : "bg-red-500"
        }`}
      />
      <span>Backend</span>
      <span
        className={`status-dot ml-2 ${
          data?.lmstudio_connected ? "bg-green-500" : "bg-zinc-600"
        }`}
      />
      <span>LM Studio</span>
    </div>
  );
}

export default function App() {
  return (
    <div className="flex h-screen flex-col bg-zinc-950 text-zinc-100">
      {/* Titlebar (frameless window drag region) */}
      <div
        className="flex h-9 items-center justify-between px-4"
        style={{ WebkitAppRegion: "drag" } as React.CSSProperties}
      >
        <span className="text-sm font-semibold tracking-wide text-zinc-300">
          Manga Translator
        </span>
        <div style={{ WebkitAppRegion: "no-drag" } as React.CSSProperties}>
          <BackendStatus />
        </div>
      </div>

      {/* Main content area — router goes here in Phase 1 */}
      <main className="flex flex-1 items-center justify-center">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-zinc-200">
            Phase 0 — Scaffold Complete
          </h1>
          <p className="mt-2 text-zinc-500">
            Drop a manga folder here to get started. (Phase 1)
          </p>
        </div>
      </main>
    </div>
  );
}