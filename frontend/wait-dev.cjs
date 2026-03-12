// wait-dev.cjs — polls localhost:5173 then launches Electron
const http = require("http");
const { spawn } = require("child_process");
const electronBinary = require("electron");

const URL = "http://localhost:5173";
const INTERVAL = 500;
const TIMEOUT = 30000;

function poll(elapsed) {
  if (elapsed >= TIMEOUT) {
    console.error("Timed out waiting for Vite");
    process.exit(1);
  }
  http
    .get(URL, () => {
      console.log("Vite ready — launching Electron");
      const el = spawn(electronBinary, ["."], {
        stdio: "inherit",
        env: { ...process.env, NODE_ENV: "development" },
      });
      el.on("close", (code) => process.exit(code));
    })
    .on("error", () => {
      setTimeout(() => poll(elapsed + INTERVAL), INTERVAL);
    });
}

poll(0);
