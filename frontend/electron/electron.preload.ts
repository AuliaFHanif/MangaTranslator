import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("electronAPI", {
  getBackendUrl: (): Promise<string> =>
    ipcRenderer.invoke("get-backend-url"),

  openFolderDialog: (): Promise<string | null> =>
    ipcRenderer.invoke("open-folder-dialog"),
});