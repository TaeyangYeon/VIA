'use strict';

const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');

const DEV_SERVER_URL = 'http://localhost:5173';
const IS_DEV = process.env.NODE_ENV !== 'production';

let mainWindow = null;

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
        mainWindow.webContents.loadURL('data:text/html,<h1 style="color:white;font-family:sans-serif;padding:2rem">VIA: Dev server not running. Start with: npm run dev:web</h1>');
      });
    });
  } else {
    mainWindow.loadFile(path.join(__dirname, 'dist', 'index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.on('ready', createWindow);

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

// IPC placeholder for future agent communication
ipcMain.handle('via:ping', () => 'pong');
