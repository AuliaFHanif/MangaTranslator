/**
 * usePipelineSocket — connects to /pipeline/ws and pushes live page status
 * updates into the Zustand project store.
 *
 * Mount this once at the App level. It reconnects automatically if the
 * connection drops.
 */

import { useEffect, useRef } from "react";
import { getBackendUrlSync } from "@/ipc/backend";
import { useProjectStore } from "@/stores/projectStore";
import type { PageStatus } from "@/stores/projectStore";

interface PageStatusMessage {
  type: "page_status";
  folder_path: string;
  page_index: number;
  status: PageStatus;
  error?: string;
}

interface ConnectedMessage {
  type: "connected";
  is_running: boolean;
  queue_depth: number;
}

type WsMessage = PageStatusMessage | ConnectedMessage;

const RECONNECT_DELAY_MS = 3000;

export function usePipelineSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmounted = useRef(false);

  const { project, updatePageStatus, setPipelineRunning } = useProjectStore();

  useEffect(() => {
    unmounted.current = false;

    function connect() {
      if (unmounted.current) return;

      // Convert http://127.0.0.1:8001 → ws://127.0.0.1:8001
      const backendUrl = getBackendUrlSync().replace(/^http/, "ws");
      const url = `${backendUrl}/pipeline/ws`;

      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("[pipeline ws] connected");
      };

      ws.onmessage = (event) => {
        try {
          const msg: WsMessage = JSON.parse(event.data);

          if (msg.type === "connected") {
            setPipelineRunning(msg.is_running);
          }

          if (msg.type === "page_status") {
            // Only update if the message is for the currently open project
            if (project && msg.folder_path === project.folder_path) {
              updatePageStatus(msg.page_index, msg.status, msg.error);
            }
          }
        } catch (e) {
          console.warn("[pipeline ws] bad message", event.data, e);
        }
      };

      ws.onclose = () => {
        console.log("[pipeline ws] disconnected — reconnecting in 3s");
        if (!unmounted.current) {
          reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY_MS);
        }
      };

      ws.onerror = (e) => {
        console.warn("[pipeline ws] error", e);
        // Only close if the socket is open or connecting — avoids double-close noise
        if (
          ws.readyState === WebSocket.OPEN ||
          ws.readyState === WebSocket.CONNECTING
        ) {
          ws.close();
        }
      };
    }

    connect();

    return () => {
      unmounted.current = true;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      const ws = wsRef.current;
      if (
        ws &&
        ws.readyState !== WebSocket.CLOSED &&
        ws.readyState !== WebSocket.CLOSING
      ) {
        ws.close();
      }
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
}
