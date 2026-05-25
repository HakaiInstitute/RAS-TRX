# Further Development Needed

## Self-Contained Binary Distribution

The goal is to ship RAS-TRX as a single self-contained executable (no Python installation required), mirroring how [LAS-TRX](https://github.com/HakaiInstitute/LAS-TRX) is distributed.

### What's already in place

The codebase was written with this in mind:

- PyInstaller is already a listed dev dependency
- `freeze_support()` is called in `__main__.py` (required for Windows multiprocessing in frozen executables)
- `resource_path()` in `utils.py` already resolves paths for both dev and `_MEIPASS` (PyInstaller) environments
- LAS-TRX's `gui-release.yml` GitHub Actions workflow is a near-direct template — same stack, same flags, same CI structure

### Primary risk: `rasterio` / GDAL

LAS-TRX's heaviest native dependency is `laspy`/`laszip` — relatively simple C extensions. RAS-TRX adds **rasterio**, which wraps **GDAL** — a larger C/C++ library with a plugin architecture (drivers for GeoTIFF, etc.).

**Why this is likely fine in practice:** Modern rasterio wheels ship with a vendored GDAL, and `pyinstaller-hooks-contrib` (included with PyInstaller ≥5) has hooks for rasterio. However, a custom `.spec` file may be needed to explicitly declare hidden imports for GDAL drivers. If the one-liner approach fails, enumerating GDAL's hidden imports is a well-documented process — roughly half a day of iteration.

### Minor issues to fix before building

| Issue | Fix |
|---|---|
| No `--add-data` flags for `.ui` file and icon in any build command | Add them (copy pattern from LAS-TRX) |
| No GitHub Actions workflow for automated releases | Create `.github/workflows/gui-release.yml` based on LAS-TRX |

### PROJ grid files (shared limitation with LAS-TRX)

Both projects call `sync_missing_grid_files()` on startup, which downloads Canadian PROJ grids (~50 MB) to the user's data directory on first run. LAS-TRX ships this way — first run requires an internet connection. No change needed; document as a known limitation.

### Estimated effort

| Task | Estimate |
|---|---|
| Write GitHub Actions workflow (adapt from LAS-TRX `gui-release.yml`) | ~1 hour |
| Test Windows PyInstaller build locally; iterate on GDAL hidden imports if needed | 2–4 hours |
| Optional: Linux build | ~1 hour if Windows works cleanly |

**Total: 1 day optimistic, 2 days with GDAL iteration.**

### Reference

LAS-TRX uses the following build pattern (adapt paths for RAS-TRX):

```bash
# Windows
pyinstaller --onefile --windowed \
  --icon="ras_trx/resources/ras-trx.ico" \
  --add-data="ras_trx/resources/ras-trx.ico;resources" \
  --add-data="ras_trx/resources/mainwindow.ui;resources" \
  --name RAS-TRX-v{version}-win64.exe \
  ras_trx/__main__.py

# Linux
pyinstaller --onefile \
  --icon="ras_trx/resources/ras-trx.ico" \
  --add-data="ras_trx/resources/ras-trx.ico:resources" \
  --add-data="ras_trx/resources/mainwindow.ui:resources" \
  --name RAS-TRX-v{version}-linux \
  ras_trx/__main__.py
```
