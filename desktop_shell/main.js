const { app, BrowserWindow, Menu, shell, session } = require('electron');
const { spawn } = require('child_process');
const fs = require('fs');
const http = require('http');
const path = require('path');

const ROOT = '/Users/lan/PycharmProjects/TermFinale';
const PORT = 8903;
const PY = path.join(ROOT, '.venv/bin/python');
let server = null;

function waitForServer(tries = 80) {
  return new Promise((resolve, reject) => {
    const tick = (n) => {
      const req = http.get({ host: '127.0.0.1', port: PORT, path: '/api/health', timeout: 800 }, (res) => {
        res.resume();
        if (res.statusCode) resolve(); else retry(n);
      });
      req.on('error', () => retry(n));
      req.on('timeout', () => { req.destroy(); retry(n); });
    };
    const retry = (n) => {
      if (n <= 0) return reject(new Error('backend timeout'));
      setTimeout(() => tick(n - 1), 250);
    };
    tick(tries);
  });
}

function startServer() {
  server = spawn(PY, ['server/app.py'], {
    cwd: ROOT,
    env: { ...process.env, TERMFINALE_WEB_PORT: String(PORT) },
    detached: true,
    stdio: ['ignore', fs.openSync('/tmp/tf_server.log', 'a'), fs.openSync('/tmp/tf_server.log', 'a')],
  });
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1080,
    minHeight: 720,
    title: 'TermFinale',
    backgroundColor: '#F7F4EE',
    titleBarStyle: 'hiddenInset',
    trafficLightPosition: { x: 16, y: 16 },
    webPreferences: { contextIsolation: true, nodeIntegration: false },
  });
  win.loadURL(`http://127.0.0.1:${PORT}/dashboard.html?v=3`);
  win.webContents.on('did-finish-load', () => { try { win.webContents.executeJavaScript('window.scrollTo(0,0)'); } catch (e) {} });
  win.webContents.on('before-input-event', (e, input) => {
    if ((input.meta || input.control) && String(input.key).toLowerCase() === 'r') {
      win.webContents.reloadIgnoringCache();
      e.preventDefault();
    }
  });
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http://127.0.0.1:')) return { action: 'allow' };
    shell.openExternal(url);
    return { action: 'deny' };
  });
}

app.whenReady().then(async () => {
  Menu.setApplicationMenu(null);
  try { await session.defaultSession.clearCache(); } catch (e) {}
  startServer();
  try { await waitForServer(); } catch (e) { console.error(e); }
  createWindow();
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});

function stopServer() {
  if (!server) return;
  try { process.kill(-server.pid, 'SIGTERM'); } catch (e) {}
  server = null;
}
app.on('window-all-closed', () => { stopServer(); app.quit(); });
app.on('before-quit', stopServer);
