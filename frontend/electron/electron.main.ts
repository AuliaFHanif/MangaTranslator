import { app, BrowserWindow, ipcMain, dialog } from "electron";
import http from "http";
import path from "path";
import { spawn, spawnSync, ChildProcess } from "child_process";

const isDev = process.env.NODE_ENV === "development";
const backendPort = isDev ? 8011 : 8000;

let mainWindow: BrowserWindow | null = null;
let backendProcess: ChildProcess | null = null;

const BACKEND_HEALTH_PATH = "/health/";
const BACKEND_STARTUP_TIMEOUT_MS = 20_000;
const BACKEND_POLL_INTERVAL_MS = 500;
const WINDOW_SHOW_FALLBACK_MS = 1_500;

function getDevPythonCommand(): { command: string; args: string[] } {
  const backendArgs = [
    "-m",
    "uvicorn",
    "app.main:app",
    "--host",
    "127.0.0.1",
    "--port",
    String(backendPort),
  ];

  const configuredPython = process.env.MANGA_TRANSLATOR_PYTHON;
  if (configuredPython) {
    return { command: configuredPython, args: backendArgs };
  }

  if (process.platform === "win32") {
    return { command: "py", args: ["-3.12", ...backendArgs] };
  }

  return { command: "python3.12", args: backendArgs };
}

function waitForBackendReady(): Promise<void> {
  const startedAt = Date.now();

  return new Promise((resolve, reject) => {
    const tryConnect = () => {
      if (!backendProcess) {
        reject(new Error("Backend process exited before becoming ready."));
        return;
      }

      const req = http.get(
        `http://127.0.0.1:${backendPort}${BACKEND_HEALTH_PATH}`,
        (res) => {
          res.resume();
          if (res.statusCode && res.statusCode >= 200 && res.statusCode < 300) {
            resolve();
            return;
          }

          if (Date.now() - startedAt >= BACKEND_STARTUP_TIMEOUT_MS) {
            reject(
              new Error(
                `Backend health check failed with status ${res.statusCode}.`,
              ),
            );
            return;
          }

          setTimeout(tryConnect, BACKEND_POLL_INTERVAL_MS);
        },
      );

      req.on("error", () => {
        if (Date.now() - startedAt >= BACKEND_STARTUP_TIMEOUT_MS) {
          reject(new Error("Timed out waiting for backend readiness."));
          return;
        }

        setTimeout(tryConnect, BACKEND_POLL_INTERVAL_MS);
      });
    };

    tryConnect();
  });
}

function stopBackend(): void {
  if (!backendProcess?.pid) {
    backendProcess = null;
    return;
  }

  if (process.platform === "win32") {
    spawn("taskkill", ["/pid", String(backendProcess.pid), "/t", "/f"], {
      stdio: "ignore",
      shell: false,
    });
  } else {
    backendProcess.kill("SIGTERM");
  }

  backendProcess = null;
}

function killStaleDevBackendOnPort(port: number): void {
  if (process.platform !== "win32") return;

  const netstat = spawnSync("netstat", ["-ano", "-p", "tcp"], {
    encoding: "utf8",
  });
  if (netstat.status !== 0 || !netstat.stdout) return;

  const pidSet = new Set<string>();
  const portNeedle = `127.0.0.1:${port}`;

  for (const line of netstat.stdout.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (
      !trimmed ||
      !trimmed.includes("LISTENING") ||
      !trimmed.includes(portNeedle)
    ) {
      continue;
    }

    const parts = trimmed.split(/\s+/);
    const pid = parts[parts.length - 1];
    if (!pid || Number(pid) === process.pid) continue;
    pidSet.add(pid);
  }

  for (const pid of pidSet) {
    spawnSync("taskkill", ["/pid", pid, "/t", "/f"], {
      stdio: "ignore",
      shell: false,
    });
    console.warn(
      `[backend] terminated stale listener on port ${port} (pid=${pid})`,
    );
  }
}

// ─── Backend process ──────────────────────────────────────────────────────────

function startBackend(): void {
  const backendPath = isDev
    ? path.join(__dirname, "../../backend")
    : path.join(process.resourcesPath, "backend");

  if (isDev) {
    // Prevent stale uvicorn instances from shadowing updated backend code.
    killStaleDevBackendOnPort(backendPort);

    const { command, args } = getDevPythonCommand();

    backendProcess = spawn(command, args, {
      cwd: backendPath,
      stdio: "pipe",
      shell: false,
      env: {
        ...process.env,
        PYTHONUNBUFFERED: "1",
      },
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

  let didShowWindow = false;
  const showWindow = () => {
    if (!mainWindow || didShowWindow) return;
    didShowWindow = true;
    mainWindow.show();
    mainWindow.focus();

    if (isDev) {
      mainWindow.webContents.openDevTools({ mode: "detach" });
    }
  };

  if (isDev) {
    mainWindow.loadURL("http://localhost:5173");
  } else {
    mainWindow.loadFile(path.join(__dirname, "../dist/index.html"));
  }

  mainWindow.once("ready-to-show", showWindow);
  mainWindow.webContents.once("did-finish-load", showWindow);
  mainWindow.webContents.on(
    "did-fail-load",
    (_event, errorCode, errorDescription) => {
      console.error(
        `[renderer:err] Failed to load window (${errorCode}): ${errorDescription}`,
      );
      showWindow();
    },
  );

  setTimeout(showWindow, WINDOW_SHOW_FALLBACK_MS);

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

app.whenReady().then(async () => {
  startBackend();

  createWindow();

  try {
    await waitForBackendReady();
  } catch (error) {
    console.error("[backend:err]", error);
  }
});

app.on("window-all-closed", () => {
  stopBackend();
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (mainWindow === null) createWindow();
});
