# Windows build and release checklist

## Build host

- Windows 10/11 x64
- Python **3.12 x64** (PyInstaller support is safer than 3.14)
- Visual C++ runtime available on the build machine
- WebView2 Evergreen Runtime installed on the target machine
- Optional for PDF export: LibreOffice (`soffice.exe` on PATH)
- Playwright is required by the PDF renderer. Do not download a separate Chromium: the renderer uses the installed Microsoft Edge (`channel=msedge`).

## Build

```powershell
py -3.12 -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install pyinstaller
powershell -ExecutionPolicy Bypass -File tools\build_windows.ps1
```

The spec now creates a one-folder `dist\TermFinale\TermFinale.exe` and does not
create the macOS `BUNDLE` on Windows. The Windows icon is `assets/icon.ico`.

## Runtime paths

- App data: `%APPDATA%\TermFinale\v3-data`
- API keys: `%APPDATA%\TermFinale\.env`
- Chat DB: `%APPDATA%\TermFinale\v3-data\chat.sqlite3`
- Ports: 8900/8905/8907 by default; if a port is occupied, the shell allocates a
  free loopback port and opens the matching URL.
- All API calls from the UI are relative; PDF return links use the active
  request host/port.

## Must test on a clean Windows VM

1. First launch and onboarding.
2. API Key save/test/reopen.
3. Upload PDF and save sources, then read, search, export.
4. Backup ZIP and reinstall on a second Windows user account.
5. WebView2 missing case and no-network/cross-origin behavior.
6. LibreOffice-present and LibreOffice-absent PDF export paths.
7. `%APPDATA%` write failure and non-ASCII Windows username/path.
8. Installer/authenticode signing, SmartScreen and uninstall.

This is not a completed Windows release until that VM matrix is run.
