'use strict';

const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn, execSync } = require('child_process');
const http = require('http');
const net = require('net');

const DEV_SERVER_URL = 'http://localhost:5173';
const IS_DEV = process.env.NODE_ENV !== 'production';
const BACKEND_PORT = 8000;
const BACKEND_HOST = '127.0.0.1';
const BACKEND_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}`;
const HEALTH_INTERVAL_MS = 500;
const HEALTH_TIMEOUT_MS = 30000;

let mainWindow = null;
let backendProcess = null;
let backendReady = false;

// ─── Python executable detection ─────────────────────────────────────────────

function findPython() {
  const venvPython = path.join(__dirname, '..', '.venv', 'bin', 'python');
  if (fs.existsSync(venvPython)) return venvPython;
  try {
    execSync('which python3', { stdio: 'pipe' });
    return 'python3';
  } catch {}
  return 'python';
}

// ─── Port availability check ──────────────────────────────────────────────────

function isPortInUse(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once('error', () => resolve(true));
    server.once('listening', () => {
      server.close();
      resolve(false);
    });
    server.listen(port, BACKEND_HOST);
  });
}

// ─── Health polling ───────────────────────────────────────────────────────────

function httpGet(url) {
  return new Promise((resolve, reject) => {
    const req = http.get(url, (res) => {
      if (res.statusCode >= 200 && res.statusCode < 400) resolve(true);
      else reject(new Error(`HTTP ${res.statusCode}`));
      res.resume();
    });
    req.on('error', reject);
    req.setTimeout(2000, () => {
      req.destroy();
      reject(new Error('timeout'));
    });
  });
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function pollBackendHealth() {
  const maxAttempts = Math.ceil(HEALTH_TIMEOUT_MS / HEALTH_INTERVAL_MS);
  for (let i = 0; i < maxAttempts; i++) {
    try {
      await httpGet(`${BACKEND_URL}/health`);
      return true;
    } catch {}
    await sleep(HEALTH_INTERVAL_MS);
  }
  return false;
}

// ─── FastAPI spawn ────────────────────────────────────────────────────────────

async function spawnBackend() {
  const portBusy = await isPortInUse(BACKEND_PORT);

  if (portBusy) {
    if (IS_DEV) {
      // Assume backend is already running externally in dev mode
      console.log('[VIA] Port 8000 in use — assuming external backend (dev mode)');
      backendReady = true;
      return;
    }
    dialog.showErrorBox(
      'VIA — Port Conflict',
      `Port ${BACKEND_PORT} is already in use. Please free the port and restart VIA.`,
    );
    app.quit();
    return;
  }

  const python = findPython();
  const projectRoot = path.join(__dirname, '..');

  console.log(`[VIA] Starting backend: ${python} -m uvicorn ...`);

  backendProcess = spawn(
    python,
    ['-m', 'uvicorn', 'backend.main:app', '--host', BACKEND_HOST, '--port', String(BACKEND_PORT)],
    {
      cwd: projectRoot,
      stdio: ['ignore', 'pipe', 'pipe'],
      env: { ...process.env },
    },
  );

  backendProcess.stdout.on('data', (d) => process.stdout.write(`[backend] ${d}`));
  backendProcess.stderr.on('data', (d) => process.stderr.write(`[backend] ${d}`));

  backendProcess.on('exit', (code, signal) => {
    console.log(`[VIA] Backend exited: code=${code} signal=${signal}`);
    if (backendReady) {
      // Unexpected exit after startup — show message
      if (mainWindow && !mainWindow.isDestroyed()) {
        dialog.showErrorBox('VIA — Backend Stopped', 'The backend server stopped unexpectedly.');
      }
    }
    backendProcess = null;
  });

  const ready = await pollBackendHealth();
  if (!ready) {
    dialog.showErrorBox(
      'VIA — Backend Startup Failed',
      'The backend server did not respond within 30 seconds. Check the logs and try again.',
    );
    if (backendProcess) {
      backendProcess.kill('SIGKILL');
      backendProcess = null;
    }
    app.quit();
    return;
  }

  backendReady = true;
  console.log('[VIA] Backend ready at', BACKEND_URL);
}

// ─── Graceful shutdown ────────────────────────────────────────────────────────

function killBackend() {
  if (!backendProcess) return Promise.resolve();
  return new Promise((resolve) => {
    backendProcess.kill('SIGTERM');
    const timer = setTimeout(() => {
      if (backendProcess) {
        backendProcess.kill('SIGKILL');
      }
      resolve();
    }, 5000);
    backendProcess.once('exit', () => {
      clearTimeout(timer);
      resolve();
    });
  });
}

// ─── Window ───────────────────────────────────────────────────────────────────

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 900,
    minHeight: 600,
    backgroundColor: '#0a0a0a',
    title: 'VIA — Vision Intelligence Agent',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
      sandbox: false,
    },
    show: false,
  });

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  if (IS_DEV) {
    mainWindow.loadURL(DEV_SERVER_URL).catch(() => {
      mainWindow.loadFile(path.join(__dirname, 'dist', 'index.html')).catch(() => {
        mainWindow.webContents.loadURL(
          'data:text/html,<h1 style="color:white;font-family:sans-serif;padding:2rem">VIA: Dev server not running. Start with: npm run dev:web</h1>',
        );
      });
    });
  } else {
    mainWindow.loadFile(path.join(__dirname, 'dist', 'index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// ─── App lifecycle ────────────────────────────────────────────────────────────

app.on('ready', async () => {
  await spawnBackend();
  createWindow();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});

app.on('before-quit', async (event) => {
  if (backendProcess) {
    event.preventDefault();
    await killBackend();
    app.exit(0);
  }
});

// ─── IPC handlers ─────────────────────────────────────────────────────────────

ipcMain.handle('via:ping', () => 'pong');

ipcMain.handle('via:getBackendStatus', () => ({
  running: backendReady,
  url: BACKEND_URL,
}));

ipcMain.handle('via:getEngineStatus', async () => {
  try {
    const data = await new Promise((resolve, reject) => {
      const req = http.get(`${BACKEND_URL}/api/engine/status`, (res) => {
        let body = '';
        res.on('data', (chunk) => { body += chunk; });
        res.on('end', () => {
          try { resolve(JSON.parse(body)); } catch { reject(new Error('Invalid JSON')); }
        });
      });
      req.on('error', reject);
      req.setTimeout(5000, () => { req.destroy(); reject(new Error('timeout')); });
    });
    return data;
  } catch (err) {
    return { error: err.message, connected: false };
  }
});
