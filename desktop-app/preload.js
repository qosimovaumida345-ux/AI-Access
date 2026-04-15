const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  hideWindow: () => ipcRenderer.send('hide-window'),
  minimizeWindow: () => ipcRenderer.send('minimize-window'),
  maximizeWindow: () => ipcRenderer.send('maximize-window'),
  setToken: (token) => ipcRenderer.send('set-token', token),
  onExamAnswer: (callback) => ipcRenderer.on('exam-answer', (_event, value) => callback(value)),
  readDir: (path) => ipcRenderer.invoke('read-dir', path),
  extractZip: (zip, out) => ipcRenderer.invoke('extract-zip', zip, out)
});
