import { getBackendUrlSync, resolveBackendUrl } from "@/ipc/backend";

export async function openProject(folderPath: string) {
  const backend = await resolveBackendUrl();
  const url = `${backend}/projects/open`;

  console.log("[api.openProject] request:start", { url, folderPath });
  console.time("[api.openProject] request");

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ folder_path: folderPath }),
  });

  console.log("[api.openProject] response:headers", {
    ok: res.ok,
    status: res.status,
    statusText: res.statusText,
  });

  if (!res.ok) {
    const err = await res.json();
    console.error("[api.openProject] request:failed", err);
    console.timeEnd("[api.openProject] request");
    throw new Error(err.detail ?? "Failed to open project");
  }

  const data = await res.json();
  console.log("[api.openProject] request:success", {
    wasCreated: data.was_created,
    pageCount: data.project?.pages?.length,
    projectId: data.project?.id,
  });
  console.timeEnd("[api.openProject] request");
  return data;
}

export function getThumbnailUrl(
  projectId: string,
  folderPath: string,
  pageIndex: number,
) {
  const backend = getBackendUrlSync();
  const encoded = encodeURIComponent(folderPath);
  return `${backend}/projects/${projectId}/pages/${pageIndex}/thumbnail?folder_path=${encoded}`;
}

export async function startPipeline(folderPath: string) {
  const backend = getBackendUrlSync();
  const res = await fetch(`${backend}/pipeline/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ folder_path: folderPath }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail ?? "Failed to start pipeline");
  }
  return res.json();
}

export async function stopPipeline() {
  const backend = getBackendUrlSync();
  const res = await fetch(`${backend}/pipeline/stop`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to stop pipeline");
  return res.json();
}
