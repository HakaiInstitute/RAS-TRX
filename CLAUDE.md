# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**RAS-TRX** is a Python application that converts raster DEM (Digital Elevation Model) coordinates between various ITRF realizations and NAD83(CSRS). It is a raster-focused fork of [LAS-TRX](https://github.com/HakaiInstitute/LAS-TRX), extending that tool's coordinate transformation capabilities to GeoTIFF raster files instead of LAS/LAZ point cloud files.

- **Repository**: https://github.com/HakaiInstitute/RAS-TRX
- **Developer**: Santiago Gonzalez Arriola (santiago@hakai.org)
- **Original LAS-TRX author**: Taylor Denouden (taylor.denouden@hakai.org)
- **Language**: Python 3.10+
- **Build System**: uv

## Architecture Overview

### High-Level Design

The application is split into two main components:

1. **GUI Application** (`__main__.py`): A PyQt6-based desktop interface for interactive coordinate transformations
2. **Worker/Processing Engine**: Multi-threaded raster processing with coordinate transformation

### Key Components

- **`config.py`**: Enums and Pydantic models for coordinate systems. `TrxReference`, `TrxVd`, `TrxCoordType` map GUI values to csrspy enums. `ReferenceConfig` builds a `pyproj.CRS` (used for rasterio profile updates). `TransformConfig` serializes to `CSRSPYConfig` to drive the csrspy transformer.

- **`worker.py`**: `TransformWorker` (QThread) submits per-file `transform_dem()` calls to a `ProcessPoolExecutor`. **Critically: only Z values are transformed per-pixel** — csrspy is called to update elevation; horizontal reprojection is handled at the profile level by `transform_raster_profile()` in `dem_utils.py`.

- **`dem_utils.py`**: `transform_raster_profile()` uses `rasterio.warp.calculate_default_transform` to update the affine transform and dimensions for the new CRS. `get_raster_points_and_values()` iterates pixels within a block window to produce (X, Y, Z, nodata_flag) records.

- **`utils.py`**: `resource_path()` resolves bundled resources under both dev (`src/`) and PyInstaller (`_MEIPASS`) environments.

### Data Flow

1. User configures source/destination reference frames, epochs, vertical datums, and coordinate types in GUI
2. User selects input DEM file(s) and output location (supports batch processing with wildcards)
3. `TransformWorker` is spawned as a separate QThread
4. Worker pre-counts raster blocks across all files for progress tracking, then submits one future per file to a `ProcessPoolExecutor`
5. For each raster block in `transform_dem()`:
   - Pixels extracted as (X, Y, Z) coordinates; nodata pixels filtered out
   - csrspy transformer updates Z (elevation) for all valid pixels
   - Output raster profile uses the destination CRS with recalculated affine transform
   - Z values written back; X/Y positions remain on the original grid
6. GUI polls progress every 100ms via multiprocessing-safe shared `Value`

### External Dependencies

- **rasterio**: Raster I/O and geospatial metadata
- **pyproj**: CRS/coordinate system definitions (EPSG codes, compound CRS creation)
- **csrspy**: Core coordinate transformation library (handles ITRF/NAD83 conversions and epoch transforms)
- **pydantic**: Data validation and configuration models
- **PyQt6**: Desktop GUI framework
- **requests**: GitHub API calls for version checking

## Development Setup

### Install Dependencies

```bash
uv sync
```

### Run the Application

```bash
uv run ras-trx
```

With debug mode and pre-populated fields:

```bash
DEBUG=1 uv run ras-trx
```

### Run Tests

```bash
uv run pytest
```

Run a specific test:

```bash
uv run pytest tests/test_file.py::test_name -v
```

### Code Quality

```bash
uv run ruff format .
uv run ruff check . --fix
uv run mypy src/
```

Pre-commit hooks (uses `prek`):

```bash
uv run prek run --all-files
```

## Important Implementation Details

### CRS and Coordinate System Handling

- `pyproj` constructs compound CRS objects combining horizontal (geographic/projected) and vertical (ellipsoidal/orthometric) components
- Geographic CRS are converted to 3D when no vertical CRS is specified (ellipsoidal height)
- UTM zones are dynamically constructed using `UTMConversion` with Northern hemisphere assumption
- `CGG2013a` has no EPSG code — it is defined via a custom projjson dict in `TrxVd.vertical_crs`

### PROJ Grid Files

On first run, `csrspy.utils.sync_missing_grid_files()` (called in `MainWindow.__init__`) downloads Canadian PROJ grids (~50 MB) to the user data directory. Subsequent runs use the cache. An internet connection is required on first launch.

### Nodata Handling

- Input nodata values are preserved in output rasters
- Pixels with nodata values are filtered before transformation and left unmodified in output
- Output arrays are pre-filled with nodata values to handle skipped pixels

### Batch Processing

- Input file pattern supports wildcards (`*.tif`)
- Output filename can include `{}` template to generate names from input stems
- Prevents accidental overwriting of input files
- Detects duplicate output filenames and raises an error

### Progress Tracking

- Multi-process safe using `multiprocessing.RLock` and `multiprocessing.Value`
- Progress calculated as: `100 * current_iteration / total_iterations`
- Total iterations pre-calculated by counting raster blocks across all input files
- GUI updates every 100ms with latest progress

## Build and Distribution

The project uses PyInstaller for creating standalone executables. Use the provided script for local builds (it includes required `--collect-all` flags for rasterio/pyproj/numpy):

```bash
# macOS/Linux
bash scripts/build_local.sh
```

For CI releases, see `.github/workflows/gui-release.yml`.

GUI resources (`.ui` files, icons) are embedded and resolved via `resource_path()` for both dev and packaged environments. `freeze_support()` is called in `__main__` for correct Windows multiprocessing behaviour in frozen executables.

## Configuration Persistence

Users can save/load transformation configurations as JSON via the GUI Config menu. The `TransformConfig` model is serialized/deserialized using Pydantic's `model_dump_json()` and `model_validate_json()`.
