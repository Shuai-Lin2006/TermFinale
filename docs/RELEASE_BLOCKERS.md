# Release blockers and decisions

## Must decide before a public commercial release

1. **PyMuPDF / MuPDF is AGPL-3.0 or commercial.**
   - Current app uses it for PDF parsing/rendering.
   - A closed-source commercial release needs an Artifex commercial license.
   - An AGPL release needs the complete corresponding source and AGPL notices.
   - See `licenses/PyMuPDF-NOTICE.txt`.

2. **macOS Developer ID signing/notarization** is not configured.
   - Current bundle is ad-hoc signed (`flags=adhoc`) and only works with
     Gatekeeper overrides on machines that trust it.
   - Public distribution needs a Developer ID certificate, hardened runtime,
     notarization, and a clean-machine test.

3. **Windows clean-VM matrix** is not run here.
   - Follow `docs/WINDOWS_RELEASE.md` on a Windows 10/11 machine.
   - WebView2 runtime, Edge availability for PDF, and LibreOffice presence
     must be tested on a clean VM.

## Technical checks completed

- `python-multipart` upgraded from 0.0.20 to 0.0.31; `pip-audit -r` clean.
- Same-origin + DNS-rebinding guard and a loopback session cookie for the
  packaged product app.
- `.env`, session token and bridge token are written with mode 0600 where the
  OS supports it.
- Export filenames are sanitized and checked to remain in the Desktop folder.
- PDF return links use the active request origin instead of a hard-coded 8907.
- Packaged app starts only the v3 product server; legacy 8900/8905 servers are
  not started.
- `desktop.py` uses platform-specific user-data paths and allocates a free
  loopback port when the default is occupied.
