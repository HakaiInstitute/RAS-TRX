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

- **`config.py`**: Configuration and enum classes defining coordinate systems, reference frames, and vertical datums
  - `TrxReference`: Enum for reference frames (NAD83(CSRS), WGS84, ITRF series)
  - `TrxVd`: Enum for vertical datums (WGS84, GRS80, CGVD2013, etc.)
  - `TrxCoordType`: Enum for coordinate types (Geographic, UTM zones 3-23)
  - `ReferenceConfig`: Configuration for a single reference frame including CRS construction
  - `TransformConfig`: Complete source and destination configuration for transformations
  - Provides conversion to csrspy configuration format for actual coordinate transformation

- **`worker.py`**: Multi-threaded DEM processing
  - `TransformWorker`: QThread subclass that processes DEM files in parallel using ProcessPoolExecutor
  - `transform_dem()`: Worker function that processes individual raster files using csrspy for coordinate transformation
  - Handles block-windowed reading/writing for memory efficiency
  - Filters nodata pixels before transformation
  - Progress tracking via shared multiprocessing values

- **`dem_utils.py`**: Raster-specific utilities
  - `transform_raster_profile()`: Updates rasterio profile for new CRS while maintaining spatial integrity
  - `get_raster_points_and_values()`: Extracts (X, Y, Z) coordinates from raster blocks with nodata tracking

- **`logger.py`**: Global logger configuration

- **`utils.py`**: Utility functions
  - `resource_path()`: Resolves resource paths for both dev and PyInstaller bundled environments
  - `get_upgrade_version()`: Checks GitHub releases for newer versions

### Data Flow

1. User configures source and destination reference frames, epochs, vertical datums, and coordinate types in GUI
2. User selects input DEM file(s) and output location (supports batch processing with wildcards)
3. `TransformWorker` is spawned as separate thread
4. Worker divides each DEM into raster blocks for memory efficiency
5. For each block:
   - Raster pixels are converted to (X, Y, Z) coordinates
   - Nodata pixels are filtered out
   - csrspy transformer performs coordinate transformation
   - Results written back to output raster with updated profile
6. Progress updates emitted to GUI during processing
7. Multiple files processed in parallel using CPU thread pool

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

Format and lint code:

```bash
uv run ruff format .
uv run ruff check . --fix
```

Pre-commit hooks are configured in the project:

```bash
uv run pre-commit run --all-files
```

## Important Implementation Details

### CRS and Coordinate System Handling

- The application uses `pyproj` to construct compound CRS objects combining horizontal (geographic/projected) and vertical (ellipsoidal/orthometric) components
- Geographic CRS are converted to 3D when needed for Z components
- UTM zones are dynamically constructed using `UTMConversion` with the specified zone and Northern hemisphere assumption
- Vertical CRS are carefully handled: some are EPSG-defined (CGG2013, HT2_2010v70) while CGG2013a is defined via custom projjson

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

The project uses PyInstaller for creating standalone executables:

```bash
# Windows
uv run pyinstaller --onefile --windowed --icon=src/ras_trx/resources/ras-trx.ico --add-data "src/ras_trx/resources/ras-trx.ico;resources" --add-data "src/ras_trx/resources/mainwindow.ui;resources" --name RAS-TRX src/ras_trx/__main__.py

# Linux
uv run pyinstaller --onefile --icon=src/ras_trx/resources/ras-trx.ico --add-data "src/ras_trx/resources/ras-trx.ico:resources" --add-data "src/ras_trx/resources/mainwindow.ui:resources" --name RAS-TRX src/ras_trx/__main__.py
```

GUI resources (`.ui` files, icons) are embedded and resolved via `resource_path()` for both dev and packaged environments. `freeze_support()` is called in `__main__` for correct Windows multiprocessing behaviour in frozen executables.

## Configuration Persistence

Users can save/load transformation configurations as JSON via the GUI Config menu. The `TransformConfig` model is serialized/deserialized using Pydantic's `model_dump_json()` and `model_validate_json()`.
