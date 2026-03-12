"use strict";

// electron/electron.preload.ts
var import_electron = require("electron");
import_electron.contextBridge.exposeInMainWorld("electronAPI", {
  getBackendUrl: () => import_electron.ipcRenderer.invoke("get-backend-url"),
  openFolderDialog: () => import_electron.ipcRenderer.invoke("open-folder-dialog")
});
