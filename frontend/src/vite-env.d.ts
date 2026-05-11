/// <reference types="vite/client" />

interface ViaEngineStatus {
  engine_mode?: string;
  connected?: boolean;
  base_url?: string;
  error?: string;
}

interface ViaBackendStatus {
  running: boolean;
  url: string;
}

interface Window {
  via?: {
    platform: string;
    versions: { electron: string; node: string; chrome: string };
    ping: () => Promise<string>;
    getBackendStatus: () => Promise<ViaBackendStatus>;
    getEngineStatus: () => Promise<ViaEngineStatus>;
  };
}
