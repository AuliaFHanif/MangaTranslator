import { getBackendUrlSync, resolveBackendUrl } from "@/ipc/backend";

export async function openProject(folderPath: string) {
  const backend = await resolveBackendUrl();
  const res = await fetch(`${backend}/projects/open`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ folder_path: folderPath }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail ?? "Failed to open project");
  }
  return res.json();
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

export function getFinalImageUrl(
  projectId: string,
  folderPath: string,
  pageIndex: number,
) {
  const backend = getBackendUrlSync();
  const encoded = encodeURIComponent(folderPath);
  return `${backend}/projects/${projectId}/pages/${pageIndex}/final?folder_path=${encoded}`;
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