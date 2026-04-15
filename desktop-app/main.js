const { app, BrowserWindow, ipcMain, Tray, Menu, globalShortcut, desktopCapturer, nativeImage } = require('electron');
const path = require('path');
const fs = require('fs');
const axios = require('axios');

let mainWindow = null;
let overlayWindow = null;
let tray = null;
let deviceToken = 'NOT_BOUND';
let apiBaseUrl = 'http://localhost:5000/api'; // Change to live URL later

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    show: false, // Start hidden in background
    frame: false, // Frameless UI requires us to have custom titlebar
    transparent: false, // Turned off transparency for main window to prevent weird artifacts
    backgroundColor: '#1e1e24', // Dark fallback
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  // If in dev mode, load from Vite dev server. Otherwise load built file.
  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:5173');
  } else {
    mainWindow.loadFile(path.join(__dirname, 'dist', 'index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function createOverlayWindow() {
  // Transparent, click-through overlay for exam mode answers
  overlayWindow = new BrowserWindow({
    width: 600,
    height: 100,
    x: 100,
    y: 10,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    focusable: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js')
    }
  });

  if (process.env.NODE_ENV === 'development') {
    overlayWindow.loadURL('http://localhost:5173/#/overlay');
  } else {
    overlayWindow.loadFile(path.join(__dirname, 'dist', 'index.html'), { hash: 'overlay' });
  }
  
  overlayWindow.setIgnoreMouseEvents(true);
}

app.whenReady().then(() => {
  createMainWindow();
  createOverlayWindow();

  // Create a 16x16 transparent tray icon dynamically to avoid file not found crashes
  const emptyIcon = nativeImage.createEmpty();
  tray = new Tray(emptyIcon);
  const contextMenu = Menu.buildFromTemplate([
    { label: 'Show AI-Access', click: () => mainWindow.show() },
    { label: 'Toggle Exam Mode', type: 'checkbox', checked: false, click: (item) => toggleExamMode(item.checked) },
    { type: 'separator' },
    { label: 'Quit', click: () => {
        app.isQuitting = true;
        app.quit();
      }
    }
  ]);
  tray.setToolTip('AI-Access Background Service');
  tray.setContextMenu(contextMenu);

  tray.on('click', () => {
    mainWindow.isVisible() ? mainWindow.hide() : mainWindow.show();
  });

  // Global hotkey for quick summon
  globalShortcut.register('CommandOrControl+Shift+Space', () => {
    mainWindow.isVisible() ? mainWindow.hide() : mainWindow.show();
  });
});

let examModeEnabled = false;

function toggleExamMode(enabled) {
  examModeEnabled = enabled;
  if (enabled) {
    // Register hotkey to capture screen and get answer
    globalShortcut.register('Shift', async () => {
      await performScreenAnalysis();
    });
  } else {
    globalShortcut.unregister('Shift');
  }
}

async function performScreenAnalysis() {
  try {
    // Capture the primary screen
    const sources = await desktopCapturer.getSources({ types: ['screen'], thumbnailSize: { width: 1920, height: 1080 } });
    if (sources.length === 0) return;
    
    const imageBase64 = sources[0].thumbnail.toDataURL();
    
    // Send to backend
    const res = await axios.post(`${apiBaseUrl}/screen`, {
      imageBase64,
      token: deviceToken,
      prompt: "Solve the question shown. Reply ONLY with the brief, correct answer."
    });

    if (res.data.success && overlayWindow) {
      // Send answer to overlay window
      overlayWindow.webContents.send('exam-answer', res.data.text);
    }
  } catch (error) {
    console.error('Screen analysis failed:', error.message);
  }
}

// Keep app running in background
app.on('window-all-closed', (e) => {
  e.preventDefault();
});

// IPC handlers (for React to call Electron)
ipcMain.on('hide-window', () => {
  if (mainWindow) mainWindow.hide();
});

ipcMain.on('minimize-window', () => {
  if (mainWindow) mainWindow.minimize();
});

ipcMain.on('maximize-window', () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  }
});

ipcMain.on('set-token', (event, token) => {
  deviceToken = token;
});

// File System AI Integrations
ipcMain.handle('read-dir', async (event, dirPath) => {
  try {
    const target = dirPath || app.getPath('documents');
    const files = fs.readdirSync(target);
    return { success: true, path: target, files };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

ipcMain.handle('extract-zip', async (event, zipPath, outPath) => {
  try {
    // Basic structural setup for future extraction logic
    // Usually uses 'extract-zip' or 'adm-zip' package
    return { success: true, message: `Pretended to extract ${zipPath} to ${outPath}` };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

// Avoid duplicate hotkeys warning
app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});
