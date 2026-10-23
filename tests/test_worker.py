import multiprocessing
from datetime import date
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import rasterio
from pyproj import CRS
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
    transform = from_bounds(
        480000, 5450000, 481000, 5451000, data.shape[2], data.shape[1]
    )
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

    with patch("ras_trx.worker.CSRSTransformer") as mock_transformer_cls:
        mock_t = MagicMock()
        mock_t.side_effect = fake_transform
        mock_transformer_cls.return_value = mock_t
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

    with patch("ras_trx.worker.CSRSTransformer") as mock_transformer_cls:
        mock_t = MagicMock()
        mock_t.side_effect = fake_transform
        mock_transformer_cls.return_value = mock_t
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

    with patch("ras_trx.worker.CSRSTransformer") as mock_transformer_cls:
        mock_t = MagicMock()
        mock_t.side_effect = fake_transform
        mock_transformer_cls.return_value = mock_t
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

    with patch("ras_trx.worker.CSRSTransformer") as mock_transformer_cls:
        mock_t = MagicMock()
        mock_t.side_effect = fake_transform
        mock_transformer_cls.return_value = mock_t
        transform_dem(config, src_raster, output_path, lock, cur)

    with rasterio.open(output_path) as dst:
        out_crs = CRS.from_wkt(dst.crs.to_wkt())

    assert not out_crs.is_compound
