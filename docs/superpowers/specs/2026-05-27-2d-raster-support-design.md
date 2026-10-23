# 2D Raster Support Design

**Date:** 2026-05-27
**Status:** Approved

## Overview

RAS-TRX currently only processes DEMs where pixel values represent vertical height (3D rasters). This change adds support for 2D rasters — rasters where pixel values are arbitrary (e.g. orthophotos, intensity grids, classification maps). In 2D mode the spatial reference frame is still transformed using csrspy, but pixel values are passed through unchanged.

## Config model (`config.py`)

Two new fields are added to `TransformConfig`:

```python
use_vertical_transform: bool = True
representative_elevation: float = 0.0
```

- `use_vertical_transform=True` is the default, preserving all existing behaviour.
- `representative_elevation` is only meaningful when `use_vertical_transform=False`. It is the fixed Z value passed to csrspy for every pixel so the horizontal coordinate shift is accurate. Defaults to `0.0` (sea level).
- Both fields are serialised in `model_dump_json` so saved configs round-trip correctly.

`ReferenceConfig` gains a new `horizontal_crs` property that mirrors the existing `crs` property but always omits the vertical component and skips the geographic `to_3d()` promotion. The existing `crs` property is unchanged. `transform_dem()` selects `config.destination.horizontal_crs` instead of `config.destination.crs` when building the output raster profile in 2D mode.

## Processing (`worker.py`, `dem_utils.py`)

`transform_dem()` branches on `config.use_vertical_transform`:

**3D mode (unchanged):** pixel values are used as Z input to csrspy; transformed Z is written back to the output raster; output CRS is `config.destination.crs` (may be compound).

**2D mode:**
1. `coords_to_transform` is built using `config.representative_elevation` as Z for every valid pixel instead of the pixel value.
2. The transformed Z output from csrspy is discarded.
3. Original pixel values are written unchanged to the output raster.
4. The output raster profile uses `config.destination.horizontal_crs` — a horizontal-only CRS.

`get_raster_points_and_values()` is unchanged; the Z-override occurs inside `transform_dem()` when assembling coordinates, keeping the utility function single-purpose.

## UI (`mainwindow.ui`, `__main__.py`)

### New widgets

| Widget | Type | Name | Default |
|--------|------|------|---------|
| "Pixel values represent vertical height" | `QCheckBox` | `checkBox_use_vertical_transform` | checked |
| "Representative Elevation (m)" label | `QLabel` | `label_representative_elevation` | — |
| Elevation spinner | `QDoubleSpinBox` | `doubleSpinBox_representative_elevation` | `0.0`, range `-500`–`9000` |

The checkbox and elevation widgets are placed in `frame_input`, below the input file row.

### Enable/disable rules

When `checkBox_use_vertical_transform` is **unchecked**:
- `label_input_vertical_reference` and `comboBox_input_vertical_reference` → disabled
- `label_output_vertical_reference` and `comboBox_output_vertical_reference` → disabled
- `label_representative_elevation` and `doubleSpinBox_representative_elevation` → enabled

When **checked** (default): vertical reference controls enabled, elevation spinner disabled.

### Config getter/setter

`transform_config` property getter reads `checkBox_use_vertical_transform.isChecked()` and `doubleSpinBox_representative_elevation.value()` to populate the two new `TransformConfig` fields.

`transform_config` setter restores both widgets when loading a saved config.

## Testing

### `tests/test_config.py`

- `ReferenceConfig.horizontal_crs` returns a non-compound CRS even when a vertical datum with a defined `VerticalCRS` (e.g. `CGG2013`) is selected.
- `ReferenceConfig.horizontal_crs` for geographic type does not return a 3D CRS.
- `TransformConfig` with `use_vertical_transform=False` and `representative_elevation=42.5` round-trips correctly through `model_dump_json` / `model_validate_json`.

### `tests/test_worker.py` (new file)

- In 2D mode, `transform_dem()` writes original pixel values unchanged to the output raster (no vertical shift).
- In 2D mode, the output raster's CRS is horizontal-only (not a `CompoundCRS`).
- In 2D mode with a non-zero representative elevation, csrspy receives that elevation as Z (verified by mocking the transformer).
- In 3D mode (default), pixel values are transformed and written back — existing behaviour is unaffected.
