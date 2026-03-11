import { app, BrowserWindow, ipcMain } from "electron";
import path from "path";
import { spawn, ChildProcess } from "child_process";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const isDev = process.env.NODE_ENV === "development";

let mainWindow: BrowserWindow | null = null;
let backendProcess: ChildProcess | null = null;

// ─── Backend process ──────────────────────────────────────────────────────────

function startBackend(): void {
  const backendPath = isDev
    ? path.join(__dirname, "../../backend")
    : path.join(process.resourcesPath, "backend");

  const executable = isDev
    ? "uvicorn"
    : path.join(backendPath, "manga_backend.exe");

  const args = isDev
    ? ["app.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"]
    : [];

  backendProcess = spawn(executable, args, {
    cwd: isDev ? backendPath : undefined,
    stdio: "pipe",
    shell: isDev, // needed on Windows for uvicorn in dev
  });

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
    backgroundColor: "#0f0f0f",
  });

  if (isDev) {
    mainWindow.loadURL("http://localhost:5173");
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, "../dist/index.html"));
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

// ─── IPC handlers (stubs — expanded per phase) ───────────────────────────────

ipcMain.handle("get-backend-url", () => "http://127.0.0.1:8000");

// ─── App lifecycle ────────────────────────────────────────────────────────────

app.whenReady().then(() => {
  startBackend();
  createWindow();
});

app.on("window-all-closed", () => {
  if (backendProcess) {
    backendProcess.kill();
  }
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", () => {
  if (mainWindow === null) createWindow();
});