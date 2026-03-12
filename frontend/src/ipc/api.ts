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
