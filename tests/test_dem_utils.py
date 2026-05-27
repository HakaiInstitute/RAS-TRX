import numpy as np
import pytest
import rasterio
import rasterio.windows
from pyproj import CRS
from rasterio.transform import from_bounds

from ras_trx.dem_utils import get_raster_points_and_values, transform_raster_profile


@pytest.fixture
def synthetic_raster(tmp_path):
    """4x4 GeoTIFF in UTM zone 10N with one nodata pixel."""
    path = tmp_path / "test.tif"
    crs = CRS.from_epsg(32610)
    transform = from_bounds(480000, 5450000, 481000, 5451000, 4, 4)
    data = np.array(
        [
            [
                [1.0, 2.0, 3.0, 4.0],
                [5.0, 6.0, 7.0, 8.0],
                [9.0, 10.0, -9999.0, 12.0],
                [13.0, 14.0, 15.0, 16.0],
            ]
        ],
        dtype=np.float32,
    )
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "width": 4,
        "height": 4,
        "count": 1,
        "crs": crs,
        "transform": transform,
        "nodata": -9999.0,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data)
    return path


def test_get_raster_points_pixel_count(synthetic_raster):
    with rasterio.open(synthetic_raster) as src:
        window = rasterio.windows.Window(0, 0, 4, 4)
        data = src.read(window=window)
        pixels = get_raster_points_and_values(src, window, data)
    assert len(pixels) == 16


def test_get_raster_points_nodata_flagged(synthetic_raster):
    with rasterio.open(synthetic_raster) as src:
        window = rasterio.windows.Window(0, 0, 4, 4)
        data = src.read(window=window)
        pixels = get_raster_points_and_values(src, window, data)
    nodata_pixels = [p for p in pixels if p["is_nodata"]]
    assert len(nodata_pixels) == 1
    assert nodata_pixels[0]["z"] == pytest.approx(-9999.0)


def test_get_raster_points_coords_finite(synthetic_raster):
    with rasterio.open(synthetic_raster) as src:
        window = rasterio.windows.Window(0, 0, 4, 4)
        data = src.read(window=window)
        pixels = get_raster_points_and_values(src, window, data)
    for p in pixels:
        assert np.isfinite(p["x"])
        assert np.isfinite(p["y"])


def test_get_raster_points_block_indices_in_range(synthetic_raster):
    with rasterio.open(synthetic_raster) as src:
        window = rasterio.windows.Window(0, 0, 4, 4)
        data = src.read(window=window)
        pixels = get_raster_points_and_values(src, window, data)
    for p in pixels:
        assert 0 <= p["row_in_block"] < 4
        assert 0 <= p["col_in_block"] < 4


def test_transform_raster_profile_updates_crs(synthetic_raster):
    target_crs = CRS.from_epsg(4326)
    with rasterio.open(synthetic_raster) as src:
        new_profile = transform_raster_profile(src.profile, src.bounds, target_crs)
    assert new_profile["crs"] == target_crs


def test_transform_raster_profile_preserves_band_count(synthetic_raster):
    target_crs = CRS.from_epsg(4326)
    with rasterio.open(synthetic_raster) as src:
        original_count = src.profile["count"]
        new_profile = transform_raster_profile(src.profile, src.bounds, target_crs)
    assert new_profile["count"] == original_count


def test_transform_raster_profile_has_positive_dimensions(synthetic_raster):
    target_crs = CRS.from_epsg(4326)
    with rasterio.open(synthetic_raster) as src:
        new_profile = transform_raster_profile(src.profile, src.bounds, target_crs)
    assert new_profile["width"] > 0
    assert new_profile["height"] > 0
