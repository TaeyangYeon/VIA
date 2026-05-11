'use strict';

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('via', {
  platform: process.platform,
  versions: {
    electron: process.versions.electron,
    node: process.versions.node,
    chrome: process.versions.chrome,
  },
  ping: () => ipcRenderer.invoke('via:ping'),
  getBackendStatus: () => ipcRenderer.invoke('via:getBackendStatus'),
  getEngineStatus: () => ipcRenderer.invoke('via:getEngineStatus'),
});
