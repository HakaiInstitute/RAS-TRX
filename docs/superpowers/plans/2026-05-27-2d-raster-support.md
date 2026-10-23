# 2D Raster Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend RAS-TRX to support 2D rasters (pixel values are not heights) by adding a UI toggle, a representative-elevation field, and corresponding processing logic that preserves pixel values and omits the vertical CRS component.

**Architecture:** Add `horizontal_crs` property to `ReferenceConfig`; add `use_vertical_transform` and `representative_elevation` fields to `TransformConfig`; branch `transform_dem()` on the new flag; add UI widgets with enable/disable logic wired through the `transform_config` getter/setter.

**Tech Stack:** Python 3.10+, pydantic, rasterio, pyproj, csrspy, PyQt6, pytest, unittest.mock

---

## File Map

| File | Change |
|------|--------|
| `src/ras_trx/config.py` | Add `horizontal_crs` property to `ReferenceConfig`; add `use_vertical_transform` / `representative_elevation` to `TransformConfig` |
| `src/ras_trx/worker.py` | Branch `transform_dem()` on `config.use_vertical_transform` |
| `src/ras_trx/resources/mainwindow.ui` | Add checkbox, label, and double spinbox widgets |
| `src/ras_trx/__main__.py` | Connect new widgets; update `transform_config` getter/setter |
| `tests/test_config.py` | New tests for `horizontal_crs` and `TransformConfig` round-trip |
| `tests/test_worker.py` | New file; tests for 2D and 3D `transform_dem()` behaviour |

---

### Task 1: Add `horizontal_crs` to `ReferenceConfig`

**Files:**
- Modify: `src/ras_trx/config.py` (after the existing `crs` property, ~line 239)
- Test: `tests/test_config.py` (inside `TestReferenceConfig`)

- [ ] **Step 1.1: Write the failing tests**

Add these four methods to the `TestReferenceConfig` class in `tests/test_config.py`:

```python
def test_horizontal_crs_geographic_is_not_3d(self):
    crs = self._config().horizontal_crs
    assert crs.is_geographic
    assert not crs.is_3d

def test_horizontal_crs_with_vertical_datum_is_not_compound(self):
    crs = self._config(vd=TrxVd.CGG2013).horizontal_crs
    assert not isinstance(crs, CompoundCRS)

def test_horizontal_crs_utm_is_projected(self):
    crs = self._config(coord=TrxCoordType.UTM10).horizontal_crs
    assert crs.is_projected
    assert not isinstance(crs, CompoundCRS)

def test_horizontal_crs_utm_with_vertical_datum_is_not_compound(self):
    crs = self._config(coord=TrxCoordType.UTM10, vd=TrxVd.CGG2013).horizontal_crs
    assert crs.is_projected
    assert not isinstance(crs, CompoundCRS)
```

- [ ] **Step 1.2: Run tests to verify they fail**

```bash
uv run pytest tests/test_config.py::TestReferenceConfig::test_horizontal_crs_geographic_is_not_3d tests/test_config.py::TestReferenceConfig::test_horizontal_crs_with_vertical_datum_is_not_compound tests/test_config.py::TestReferenceConfig::test_horizontal_crs_utm_is_projected tests/test_config.py::TestReferenceConfig::test_horizontal_crs_utm_with_vertical_datum_is_not_compound -v
```

Expected: all FAIL with `AttributeError: 'ReferenceConfig' object has no attribute 'horizontal_crs'`

- [ ] **Step 1.3: Add `horizontal_crs` to `ReferenceConfig`**

In `src/ras_trx/config.py`, add this property to `ReferenceConfig` immediately after the closing `return xy_crs` of the `crs` property (after line 239):

```python
@property
def horizontal_crs(self) -> CRS:
    geodetic_crs = self.ref_frame.geodetic_crs

    if self.coord_type == TrxCoordType.GEOG:
        return geodetic_crs
    elif self.coord_type.is_utm():
        return ProjectedCRS(
            name=f"{geodetic_crs.name} / UTM zone {self.coord_type.utm_zone}N",
            conversion=UTMConversion(str(self.coord_type.utm_zone), hemisphere="N"),
            geodetic_crs=geodetic_crs,
            cartesian_cs=Cartesian2DCS(),
        )
    else:
        raise IndexError(f"Could not create horizontal CRS for {self.coord_type}")
```

- [ ] **Step 1.4: Run the new tests**

```bash
uv run pytest tests/test_config.py::TestReferenceConfig::test_horizontal_crs_geographic_is_not_3d tests/test_config.py::TestReferenceConfig::test_horizontal_crs_with_vertical_datum_is_not_compound tests/test_config.py::TestReferenceConfig::test_horizontal_crs_utm_is_projected tests/test_config.py::TestReferenceConfig::test_horizontal_crs_utm_with_vertical_datum_is_not_compound -v
```

Expected: all PASS

- [ ] **Step 1.5: Run the full suite**

```bash
uv run pytest -v
```

Expected: all previously passing tests still PASS

- [ ] **Step 1.6: Commit**

```bash
git add src/ras_trx/config.py tests/test_config.py
git commit -m "feat: add horizontal_crs property to ReferenceConfig"
```

---

### Task 2: Add `use_vertical_transform` and `representative_elevation` to `TransformConfig`

**Files:**
- Modify: `src/ras_trx/config.py` (`TransformConfig` class, ~line 250)
- Test: `tests/test_config.py` (inside `TestTransformConfig`)

- [ ] **Step 2.1: Write the failing tests**

Add these two methods to the `TestTransformConfig` class in `tests/test_config.py`:

```python
def test_new_fields_default_correctly(self):
    config = TransformConfig(
        origin=ReferenceConfig(
            ref_frame=TrxReference.ITRF14,
            epoch=date(2010, 1, 1),
            vd=TrxVd.GRS80,
            coord_type=TrxCoordType.UTM10,
        ),
        destination=ReferenceConfig(
            ref_frame=TrxReference.NAD83CSRS,
            epoch=date(2010, 1, 1),
            vd=TrxVd.GRS80,
            coord_type=TrxCoordType.UTM10,
        ),
    )
    assert config.use_vertical_transform is True
    assert config.representative_elevation == 0.0

def test_2d_config_roundtrip(self):
    config = TransformConfig(
        origin=ReferenceConfig(
            ref_frame=TrxReference.ITRF14,
            epoch=date(2010, 1, 1),
            vd=TrxVd.GRS80,
            coord_type=TrxCoordType.UTM10,
        ),
        destination=ReferenceConfig(
            ref_frame=TrxReference.NAD83CSRS,
            epoch=date(2010, 1, 1),
            vd=TrxVd.GRS80,
            coord_type=TrxCoordType.UTM10,
        ),
        use_vertical_transform=False,
        representative_elevation=42.5,
    )
    restored = TransformConfig.model_validate_json(config.model_dump_json())
    assert restored.use_vertical_transform is False
    assert restored.representative_elevation == pytest.approx(42.5)
```

- [ ] **Step 2.2: Run tests to verify they fail**

```bash
uv run pytest tests/test_config.py::TestTransformConfig::test_new_fields_default_correctly tests/test_config.py::TestTransformConfig::test_2d_config_roundtrip -v
```

Expected: FAIL with `ValidationError` or `AttributeError`

- [ ] **Step 2.3: Add the two new fields to `TransformConfig`**

In `src/ras_trx/config.py`, replace the `TransformConfig` class definition (the class body, not the `to_csrspy` method):

```python
class TransformConfig(BaseModel):
    origin: ReferenceConfig
    destination: ReferenceConfig
    use_vertical_transform: bool = True
    representative_elevation: float = 0.0

    def to_csrspy(self) -> CSRSPYConfig:
        s = self.origin.to_csrspy()
        t = self.destination.to_csrspy()

        return CSRSPYConfig(
            s_ref_frame=s["ref_frame"],
            s_coords=s["coords"],
            s_vd=s["vd"],
            s_epoch=s["epoch"],
            t_ref_frame=t["ref_frame"],
            t_coords=t["coords"],
            t_vd=t["vd"],
            t_epoch=t["epoch"],
        )
```

- [ ] **Step 2.4: Run the new tests**

```bash
uv run pytest tests/test_config.py::TestTransformConfig::test_new_fields_default_correctly tests/test_config.py::TestTransformConfig::test_2d_config_roundtrip -v
```

Expected: both PASS

- [ ] **Step 2.5: Run the full suite**

```bash
uv run pytest -v
```

Expected: all tests PASS

- [ ] **Step 2.6: Commit**

```bash
git add src/ras_trx/config.py tests/test_config.py
git commit -m "feat: add use_vertical_transform and representative_elevation to TransformConfig"
```

---

### Task 3: Update `transform_dem()` for 2D mode

**Files:**
- Modify: `src/ras_trx/worker.py` (`transform_dem` function)
- Create: `tests/test_worker.py`

- [ ] **Step 3.1: Create `tests/test_worker.py` with all four failing tests**

```python
import multiprocessing
from datetime import date
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import rasterio
from pyproj import CRS
from pyproj.crs import CompoundCRS
from rasterio.transform import from_bounds

from ras_trx.config import (
    ReferenceConfig,
    TransformConfig,
    TrxCoordType,
    TrxReference,
    TrxVd,
)
from ras_trx.worker import transform_dem


def _make_raster(path, data, crs, nodata=None):
    transform = from_bounds(480000, 5450000, 481000, 5451000, data.shape[2], data.shape[1])
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "width": data.shape[2],
        "height": data.shape[1],
        "count": data.shape[0],
        "crs": crs,
        "transform": transform,
    }
    if nodata is not None:
        profile["nodata"] = nodata
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data)


def _make_config(**overrides):
    defaults = dict(
        origin=ReferenceConfig(
            ref_frame=TrxReference.ITRF14,
            epoch=date(2010, 1, 1),
            vd=TrxVd.GRS80,
            coord_type=TrxCoordType.UTM10,
        ),
        destination=ReferenceConfig(
            ref_frame=TrxReference.NAD83CSRS,
            epoch=date(2010, 1, 1),
            vd=TrxVd.GRS80,
            coord_type=TrxCoordType.UTM10,
        ),
    )
    defaults.update(overrides)
    return TransformConfig(**defaults)


@pytest.fixture
def src_raster(tmp_path):
    path = tmp_path / "input.tif"
    data = np.array([[[10.0, 20.0], [30.0, 40.0]]], dtype=np.float32)
    _make_raster(path, data, CRS.from_epsg(32610))
    return path


def test_3d_mode_writes_transformed_z(tmp_path, src_raster):
    output_path = tmp_path / "output.tif"
    config = _make_config()  # use_vertical_transform=True by default

    def fake_transform(coords):
        return [(x, y, 999.0) for x, y, z in coords]

    lock = multiprocessing.RLock()
    cur = multiprocessing.Value("i", 0)

    with patch("ras_trx.worker.CSRSTransformer") as MockTransformer:
        mock_t = MagicMock()
        mock_t.side_effect = fake_transform
        MockTransformer.return_value = mock_t
        transform_dem(config, src_raster, output_path, lock, cur)

    with rasterio.open(output_path) as dst:
        data = dst.read()

    assert np.all(data == pytest.approx(999.0))


def test_2d_mode_preserves_pixel_values(tmp_path, src_raster):
    output_path = tmp_path / "output.tif"
    config = _make_config(use_vertical_transform=False, representative_elevation=0.0)

    def fake_transform(coords):
        # Return a Z of 999.0 — should be discarded in 2D mode
        return [(x, y, 999.0) for x, y, z in coords]

    lock = multiprocessing.RLock()
    cur = multiprocessing.Value("i", 0)

    with patch("ras_trx.worker.CSRSTransformer") as MockTransformer:
        mock_t = MagicMock()
        mock_t.side_effect = fake_transform
        MockTransformer.return_value = mock_t
        transform_dem(config, src_raster, output_path, lock, cur)

    with rasterio.open(output_path) as dst:
        data = dst.read()

    expected = np.array([[[10.0, 20.0], [30.0, 40.0]]], dtype=np.float32)
    assert np.allclose(data, expected)


def test_2d_mode_uses_representative_elevation_as_z(tmp_path, src_raster):
    output_path = tmp_path / "output.tif"
    config = _make_config(use_vertical_transform=False, representative_elevation=42.5)

    captured_z: list[float] = []

    def fake_transform(coords):
        captured_z.extend(z for _, _, z in coords)
        return [(x, y, 0.0) for x, y, z in coords]

    lock = multiprocessing.RLock()
    cur = multiprocessing.Value("i", 0)

    with patch("ras_trx.worker.CSRSTransformer") as MockTransformer:
        mock_t = MagicMock()
        mock_t.side_effect = fake_transform
        MockTransformer.return_value = mock_t
        transform_dem(config, src_raster, output_path, lock, cur)

    assert len(captured_z) == 4  # 2x2 pixels, no nodata
    assert all(z == pytest.approx(42.5) for z in captured_z)


def test_2d_mode_output_crs_is_not_compound(tmp_path, src_raster):
    output_path = tmp_path / "output.tif"
    # Use CGG2013 so that 3D mode *would* produce a CompoundCRS — 2D mode must not
    config = _make_config(
        destination=ReferenceConfig(
            ref_frame=TrxReference.NAD83CSRS,
            epoch=date(2010, 1, 1),
            vd=TrxVd.CGG2013,
            coord_type=TrxCoordType.UTM10,
        ),
        use_vertical_transform=False,
    )

    def fake_transform(coords):
        return [(x, y, 0.0) for x, y, z in coords]

    lock = multiprocessing.RLock()
    cur = multiprocessing.Value("i", 0)

    with patch("ras_trx.worker.CSRSTransformer") as MockTransformer:
        mock_t = MagicMock()
        mock_t.side_effect = fake_transform
        MockTransformer.return_value = mock_t
        transform_dem(config, src_raster, output_path, lock, cur)

    with rasterio.open(output_path) as dst:
        out_crs = CRS.from_wkt(dst.crs.to_wkt())

    assert not out_crs.is_compound
```

- [ ] **Step 3.2: Run tests to verify the right ones fail**

```bash
uv run pytest tests/test_worker.py -v
```

Expected: `test_3d_mode_writes_transformed_z` PASS (existing behaviour), other three FAIL

- [ ] **Step 3.3: Replace `transform_dem()` in `src/ras_trx/worker.py`**

Replace the entire `transform_dem` function with:

```python
def transform_dem(
    config: TransformConfig,
    input_file: Path,
    output_file: Path,
    lock: multiprocessing.RLock,
    cur: multiprocessing.Value,
):
    transformer = CSRSTransformer(**config.to_csrspy().model_dump(exclude_none=True))

    with rasterio.open(input_file) as src:
        dest_crs = (
            config.destination.crs
            if config.use_vertical_transform
            else config.destination.horizontal_crs
        )
        out_profile = transform_raster_profile(src.profile, src.bounds, dest_crs)

        if src.nodata is not None:
            out_profile.update(nodata=src.nodata)

        with rasterio.open(output_file, "w", **out_profile) as dst:
            for ji, window in src.block_windows(1):
                in_data = src.read(window=window)
                pixels_info = get_raster_points_and_values(src, window, in_data)

                out_data = np.full_like(
                    in_data, fill_value=src.nodata if src.nodata is not None else 0
                )

                coords_to_transform = []
                valid_pixel_indices = []

                for i, pixel_info in enumerate(pixels_info):
                    if not pixel_info["is_nodata"]:
                        z = (
                            pixel_info["z"]
                            if config.use_vertical_transform
                            else config.representative_elevation
                        )
                        coords_to_transform.append((pixel_info["x"], pixel_info["y"], z))
                        valid_pixel_indices.append(i)

                if coords_to_transform:
                    transformed_coords = list(transformer(coords_to_transform))

                    for idx_in_transformed, original_flat_index in enumerate(
                        valid_pixel_indices
                    ):
                        original_pixel_info = pixels_info[original_flat_index]
                        out_val = (
                            transformed_coords[idx_in_transformed][2]
                            if config.use_vertical_transform
                            else original_pixel_info["z"]
                        )
                        out_data[
                            0,
                            original_pixel_info["row_in_block"],
                            original_pixel_info["col_in_block"],
                        ] = out_val

                dst.write(out_data, window=window)

                with lock:
                    cur.value += 1
```

- [ ] **Step 3.4: Run all worker tests**

```bash
uv run pytest tests/test_worker.py -v
```

Expected: all 4 tests PASS

- [ ] **Step 3.5: Run the full suite**

```bash
uv run pytest -v
```

Expected: all tests PASS

- [ ] **Step 3.6: Commit**

```bash
git add src/ras_trx/worker.py tests/test_worker.py
git commit -m "feat: support 2D rasters in transform_dem"
```

---

### Task 4: Add new widgets to `mainwindow.ui`

**Files:**
- Modify: `src/ras_trx/resources/mainwindow.ui`

The UI is Qt Designer XML. The new widgets go inside `frame_input`'s `verticalLayout_5`, as a new `<item>` inserted after the `widget` item (batch mode row) and before the `widget_input_options` item.

- [ ] **Step 4.1: Insert the new widget block**

In `src/ras_trx/resources/mainwindow.ui`, find the closing tag of the batch-mode-button item. It looks like this (the `</item>` that closes the `widget` containing `toolButton_help`):

```xml
      </item>
      <item>
       <widget class="QWidget" name="widget_input_options" native="true">
```

Insert the following new `<item>` block between those two lines:

```xml
      <item>
       <widget class="QWidget" name="widget_vertical_mode" native="true">
        <layout class="QHBoxLayout" name="horizontalLayout_5">
         <property name="leftMargin">
          <number>0</number>
         </property>
         <property name="rightMargin">
          <number>0</number>
         </property>
         <item>
          <widget class="QCheckBox" name="checkBox_use_vertical_transform">
           <property name="text">
            <string>Pixel values represent vertical height</string>
           </property>
           <property name="checked">
            <bool>true</bool>
           </property>
          </widget>
         </item>
         <item>
          <spacer name="horizontalSpacer_2">
           <property name="orientation">
            <enum>Qt::Horizontal</enum>
           </property>
           <property name="sizeHint" stdset="0">
            <size>
             <width>40</width>
             <height>20</height>
            </size>
           </property>
          </spacer>
         </item>
         <item>
          <widget class="QLabel" name="label_representative_elevation">
           <property name="enabled">
            <bool>false</bool>
           </property>
           <property name="text">
            <string>Representative Elevation (m)</string>
           </property>
           <property name="buddy">
            <cstring>doubleSpinBox_representative_elevation</cstring>
           </property>
          </widget>
         </item>
         <item>
          <widget class="QDoubleSpinBox" name="doubleSpinBox_representative_elevation">
           <property name="enabled">
            <bool>false</bool>
           </property>
           <property name="styleSheet">
            <string notr="true">border : 1px solid black;</string>
           </property>
           <property name="minimum">
            <double>-500.000000000000000</double>
           </property>
           <property name="maximum">
            <double>9000.000000000000000</double>
           </property>
           <property name="value">
            <double>0.000000000000000</double>
           </property>
          </widget>
         </item>
        </layout>
       </widget>
      </item>
```

- [ ] **Step 4.2: Add the new spinbox to `<tabstops>`**

In the `<tabstops>` section near the bottom of the file, add `doubleSpinBox_representative_elevation` after `spinBox_input_utm_zone` and before `comboBox_input_vertical_reference`:

```xml
  <tabstop>doubleSpinBox_representative_elevation</tabstop>
```

- [ ] **Step 4.3: Commit**

```bash
git add src/ras_trx/resources/mainwindow.ui
git commit -m "feat: add 2D mode checkbox and elevation spinner to mainwindow.ui"
```

---

### Task 5: Wire up new UI in `__main__.py`

**Files:**
- Modify: `src/ras_trx/__main__.py`

- [ ] **Step 5.1: Connect the checkbox signal**

In `MainWindow.__init__`, add after the `checkBox_epoch_trans` signal connection (~line 119):

```python
self.cw.checkBox_use_vertical_transform.clicked.connect(self.toggle_vertical_transform)
```

- [ ] **Step 5.2: Add `toggle_vertical_transform` method**

Add this method to `MainWindow` immediately after `enable_epoch_trans` (~line 220):

```python
def toggle_vertical_transform(self, checked: bool):
    self.cw.comboBox_input_vertical_reference.setEnabled(checked)
    self.cw.label_input_vertical_reference.setEnabled(checked)
    self.cw.comboBox_output_vertical_reference.setEnabled(checked)
    self.cw.label_output_vertical_reference.setEnabled(checked)
    self.cw.doubleSpinBox_representative_elevation.setEnabled(not checked)
    self.cw.label_representative_elevation.setEnabled(not checked)
```

- [ ] **Step 5.3: Update the `transform_config` getter**

Replace the `transform_config` property getter (~line 290) with:

```python
@property
def transform_config(self) -> TransformConfig:
    origin = ReferenceConfig(
        ref_frame=self.s_ref_frame,
        epoch=self.s_epoch,
        vd=self.s_vd,
        coord_type=self.s_coords,
    )
    destination = ReferenceConfig(
        ref_frame=self.t_ref_frame,
        epoch=self.t_epoch,
        vd=self.t_vd,
        coord_type=self.t_coords,
    )
    return TransformConfig(
        origin=origin,
        destination=destination,
        use_vertical_transform=self.cw.checkBox_use_vertical_transform.isChecked(),
        representative_elevation=self.cw.doubleSpinBox_representative_elevation.value(),
    )
```

- [ ] **Step 5.4: Update the `transform_config` setter**

Replace the `transform_config` setter (~line 305) with the full updated version:

```python
@transform_config.setter
def transform_config(self, config: TransformConfig):
    self.cw.comboBox_input_reference.setCurrentText(config.origin.ref_frame.value)
    self.cw.dateEdit_input_epoch.setDate(config.origin.epoch)
    if config.origin.coord_type.is_utm():
        self.cw.spinBox_input_utm_zone.setValue(config.origin.coord_type.utm_zone)
        self.cw.comboBox_input_coordinates.setCurrentText("UTM")
    else:
        self.cw.comboBox_input_coordinates.setCurrentText(
            config.origin.coord_type.value
        )
    self.cw.comboBox_input_vertical_reference.setCurrentText(config.origin.vd.value)

    self.cw.comboBox_output_reference.setCurrentText(
        config.destination.ref_frame.value
    )
    self.cw.dateEdit_output_epoch.setDate(config.destination.epoch)
    if config.destination.coord_type.is_utm():
        self.cw.spinBox_output_utm_zone.setValue(
            config.destination.coord_type.utm_zone
        )
        self.cw.comboBox_output_coordinates.setCurrentText("UTM")
    else:
        self.cw.comboBox_output_coordinates.setCurrentText(
            config.destination.coord_type.value
        )
    self.cw.comboBox_output_vertical_reference.setCurrentText(
        config.destination.vd.value
    )

    self.cw.checkBox_use_vertical_transform.setChecked(config.use_vertical_transform)
    self.cw.doubleSpinBox_representative_elevation.setValue(config.representative_elevation)
    self.toggle_vertical_transform(config.use_vertical_transform)

    if config.origin.epoch != config.destination.epoch:
        self.cw.checkBox_epoch_trans.setChecked(True)
```

- [ ] **Step 5.5: Run the full test suite**

```bash
uv run pytest -v
```

Expected: all tests PASS

- [ ] **Step 5.6: Commit**

```bash
git add src/ras_trx/__main__.py
git commit -m "feat: wire up 2D mode UI in MainWindow"
```
