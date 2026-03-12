// Extends the Window interface with our Electron IPC bridge
export {};

declare global {
  interface Window {
    electronAPI: {
      getBackendUrl: () => Promise<string>;
      openFolderDialog: () => Promise<string | null>;
    };
  }
}