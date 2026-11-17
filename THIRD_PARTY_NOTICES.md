# Third-party notices

**Project license:** GNU Affero General Public License v3.0 (AGPL-3.0).
The project itself is licensed under AGPL-3.0 because it bundles/imports
AGPL-3.0 components (PyMuPDF/MuPDF, MinerU). Corresponding source:
`<GitHub repository URL to be filled at release>`.

This file is a release-time inventory, not legal advice. It distinguishes
**bundled** assets from **system font references**. The app's own code is MIT
licensed; third-party components keep their own licenses.

## Commercial-use verdict

| Component | Where | License | Commercial use |
|---|---|---|---|
| KaTeX JS/CSS | bundled in `web/assets/katex`, `core/assets/katex` | MIT | **Yes**, keep notice |
| KaTeX fonts | bundled in the same folders | SIL Open Font License 1.1 | **Yes**, keep notice |
| Roboto (CustomTkinter assets) | bundled by `customtkinter` | Apache-2.0 | **Yes**, keep notice |
| CustomTkinter | legacy Tk fallback | MIT | **Yes** |
| pywebview | desktop shell | BSD-3-Clause | **Yes** |
| DashScope SDK | bundled | Apache-2.0 | **Yes** |
| python-docx / python-pptx | bundled | MIT | **Yes** |
| **PyMuPDF / MuPDF** | bundled and used for PDF parsing, rendering and PDF links | **AGPL-3.0 or Artifex commercial** | **NO for a closed-source commercial release without a commercial license.** An AGPL release must provide the corresponding source under AGPL. |
| LibreOffice | **not bundled**; called if installed for PDF conversion | MPL-2.0 | Yes for the separate program; test on the target machine |
| Playwright | bundled runtime for HTML→PDF rendering | Apache-2.0 | Yes |

### Fonts

The UI references these **system fonts**, but does not redistribute their font
files:

- Apple: PingFang SC, Songti SC, Hiragino Sans GB, Iowan Old Style, Palatino
- Microsoft: Microsoft YaHei, SimSun, Georgia
- Noto CJK (if installed)

Using a system font through CSS on a machine where it is licensed is not the
same as embedding that font. **Do not copy PingFang/Songti/YaHei/SimSun files
into the installer.** If you need identical typography on every machine, ship a
font that is explicitly licensed for redistribution (for example Noto Sans CJK
or Noto Serif CJK under SIL OFL) and add its notice.

## Before a public release

1. Decide the PyMuPDF route: buy an Artifex commercial license, or ship the app
   under AGPL-3.0 with complete corresponding source.
2. Keep `licenses/` and this notice inside the distributed app.
3. Do not add a system font file to the bundle without checking its license.
4. Re-run `pip-audit -r requirements.txt` and the test suite after dependency
   updates.

Full texts for the fonts/KaTeX/Roboto notices are in `licenses/`.

## Windows font fallback

On Windows the CSS order falls back to Microsoft YaHei / SimSun and then a
generic family. Those font files are provided by the OS and are not copied into
the installer. For identical typography across Windows/macOS, add Noto Sans CJK
or Noto Serif CJK (SIL OFL) as bundled webfonts and update this notice.
