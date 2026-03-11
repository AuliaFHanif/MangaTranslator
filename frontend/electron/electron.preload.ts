import { contextBridge, ipcRenderer } from "electron";

// Expose a safe, typed API to the React renderer.
// Never expose ipcRenderer directly — contextIsolation keeps us safe.
contextBridge.exposeInMainWorld("electronAPI", {
  getBackendUrl: (): Promise<string> =>
    ipcRenderer.invoke("get-backend-url"),
});