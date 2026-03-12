import { app, BrowserWindow, ipcMain, dialog } from "electron";
import path from "path";
import { spawn, ChildProcess } from "child_process";

const isDev = process.env.NODE_ENV === "development";
const backendPort = isDev ? 8001 : 8000;

let mainWindow: BrowserWindow | null = null;
let backendProcess: ChildProcess | null = null;

// ─── Backend process ──────────────────────────────────────────────────────────

function startBackend(): void {
  const backendPath = isDev
    ? path.join(__dirname, "../../backend")
    : path.join(process.resourcesPath, "backend");

  if (isDev) {
    const devCommand = [
      `py -3.12 -m uvicorn app.main:app --host 127.0.0.1 --port ${backendPort} --reload`,
      `C:/Users/fhani/AppData/Local/Microsoft/WindowsApps/python3.12.exe -m uvicorn app.main:app --host 127.0.0.1 --port ${backendPort} --reload`,
      `py -m uvicorn app.main:app --host 127.0.0.1 --port ${backendPort} --reload`,
      `python -m uvicorn app.main:app --host 127.0.0.1 --port ${backendPort} --reload`,
      `uvicorn app.main:app --host 127.0.0.1 --port ${backendPort} --reload`,
    ].join(" || ");

    backendProcess = spawn(devCommand, {
      cwd: backendPath,
      stdio: "pipe",
      shell: true,
    });
  } else {
    backendProcess = spawn(path.join(backendPath, "manga_backend.exe"), [], {
      stdio: "pipe",
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

// ─── Main window ─────────────────────────────────────────────────────────────

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
    titleBarStyle: "hidden",
    backgroundColor: "#0a0a0a",
    show: false,
  });

  if (isDev) {
    mainWindow.loadURL("http://localhost:5173");
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, "../dist/index.html"));
  }

  // Avoid white flash on load
  mainWindow.once("ready-to-show", () => mainWindow?.show());

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

// ─── IPC handlers ─────────────────────────────────────────────────────────────

ipcMain.handle("get-backend-url", () => `http://127.0.0.1:${backendPort}`);

ipcMain.handle("open-folder-dialog", async () => {
  if (!mainWindow) return null;
  const result = await dialog.showOpenDialog(mainWindow, {
    title: "Select Manga Folder",
    properties: ["openDirectory"],
    buttonLabel: "Open Folder",
  });
  if (result.canceled || result.filePaths.length === 0) return null;
  return result.filePaths[0];
});

// ─── App lifecycle ────────────────────────────────────────────────────────────

app.whenReady().then(() => {
  startBackend();
  createWindow();
});

app.on("window-all-closed", () => {
  if (backendProcess) backendProcess.kill();
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (mainWindow === null) createWindow();
});
