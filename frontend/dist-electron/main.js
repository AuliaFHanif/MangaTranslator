"use strict";
var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));

// electron/electron.main.ts
var import_electron = require("electron");
var import_path = __toESM(require("path"));
var import_child_process = require("child_process");
var isDev = process.env.NODE_ENV === "development";
var backendPort = isDev ? 8001 : 8e3;
var mainWindow = null;
var backendProcess = null;
function startBackend() {
  const backendPath = isDev ? import_path.default.join(__dirname, "../../backend") : import_path.default.join(process.resourcesPath, "backend");
  if (isDev) {
    const devCommand = [
      `py -3.12 -m uvicorn app.main:app --host 127.0.0.1 --port ${backendPort} --reload`,
      `C:/Users/fhani/AppData/Local/Microsoft/WindowsApps/python3.12.exe -m uvicorn app.main:app --host 127.0.0.1 --port ${backendPort} --reload`,
      `py -m uvicorn app.main:app --host 127.0.0.1 --port ${backendPort} --reload`,
      `python -m uvicorn app.main:app --host 127.0.0.1 --port ${backendPort} --reload`,
      `uvicorn app.main:app --host 127.0.0.1 --port ${backendPort} --reload`
    ].join(" || ");
    backendProcess = (0, import_child_process.spawn)(devCommand, {
      cwd: backendPath,
      stdio: "pipe",
      shell: true
    });
  } else {
    backendProcess = (0, import_child_process.spawn)(import_path.default.join(backendPath, "manga_backend.exe"), [], {
      stdio: "pipe"
    });
  }
  backendProcess.stdout?.on("data", (data) => {
    console.log("[backend]", data.toString().trim());
  });
  backendProcess.stderr?.on("data", (data) => {
    console.error("[backend:err]", data.toString().trim());
  });
  backendProcess.on("close", (code) => {
    console.log(`[backend] exited with code ${code}`);
    backendProcess = null;
  });
}
function createWindow() {
  mainWindow = new import_electron.BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    webPreferences: {
      preload: import_path.default.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    },
    titleBarStyle: "hidden",
    backgroundColor: "#0a0a0a",
    show: false
  });
  if (isDev) {
    mainWindow.loadURL("http://localhost:5173");
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(import_path.default.join(__dirname, "../dist/index.html"));
  }
  mainWindow.once("ready-to-show", () => mainWindow?.show());
  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}
import_electron.ipcMain.handle("get-backend-url", () => `http://127.0.0.1:${backendPort}`);
import_electron.ipcMain.handle("open-folder-dialog", async () => {
  if (!mainWindow) return null;
  const result = await import_electron.dialog.showOpenDialog(mainWindow, {
    title: "Select Manga Folder",
    properties: ["openDirectory"],
    buttonLabel: "Open Folder"
  });
  if (result.canceled || result.filePaths.length === 0) return null;
  return result.filePaths[0];
});
import_electron.app.whenReady().then(() => {
  startBackend();
  createWindow();
});
import_electron.app.on("window-all-closed", () => {
  if (backendProcess) backendProcess.kill();
  if (process.platform !== "darwin") import_electron.app.quit();
});
import_electron.app.on("activate", () => {
  if (mainWindow === null) createWindow();
});
