const DEFAULT_BACKEND_URL = "http://127.0.0.1:8001";

let backendUrl = DEFAULT_BACKEND_URL;
let backendUrlPromise: Promise<string> | null = null;

export function getBackendUrlSync(): string {
  return backendUrl;
}

export async function resolveBackendUrl(): Promise<string> {
  if (backendUrlPromise) return backendUrlPromise;

  backendUrlPromise = (async () => {
    if (typeof window !== "undefined" && window.electronAPI?.getBackendUrl) {
      try {
        backendUrl = await window.electronAPI.getBackendUrl();
      } catch {
        // Fall back to default URL when Electron IPC is unavailable.
      }
    }
    return backendUrl;
  })();

  return backendUrlPromise;
}
