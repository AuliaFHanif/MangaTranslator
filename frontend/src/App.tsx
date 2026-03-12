import { useProjectStore } from "@/stores/projectStore";
import { Titlebar } from "@/components/Titlebar";
import { PageSidebar } from "@/components/PageSidebar";
import { PagePreview } from "@/components/PagePreview";
import { WelcomeScreen } from "@/components/WelcomeScreen";

export default function App() {
  const project = useProjectStore((s) => s.project);

  return (
    <div className="flex h-screen flex-col bg-zinc-950 text-zinc-100 overflow-hidden">
      <Titlebar />

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