import numpy as np
import rasterio
from pyproj import CRS
from rasterio.transform import Affine
from rasterio.warp import calculate_default_transform, reproject, Resampling

def transform_raster_profile(profile: dict, bounds: rasterio.coords.BoundingBox, target_crs: CRS) -> dict:
    """
    Transforms a rasterio profile to a new CRS.
    This function will update the CRS and recalculate the affine transform
    to maintain spatial integrity.
    """
    # Calculate new transform and dimensions
    transform, width, height = calculate_default_transform(
        profile['crs'], target_crs, profile['width'], profile['height'], *bounds
    )

    new_profile = profile.copy()
    new_profile.update({
        'crs': target_crs,
        'transform': transform,
        'width': width,
        'height': height
    })
    return new_profile

def get_raster_points_and_values(src: rasterio.DatasetReader, window: rasterio.windows.Window, data: np.ndarray) -> list:
    """
    Extracts (X, Y, Z) coordinates for each pixel in a given raster window,
    along with their original block row/column and a NoData flag.
    X, Y are derived from the raster's georeferencing, Z is the pixel value.
    """
    pixels_info = []
    rows, cols = data.shape[1], data.shape[2]
    window_transform = src.window_transform(window)
    nodata_value = src.nodata

    for r in range(rows):
        for c in range(cols):
            x, y = window_transform * (c + 0.5, r + 0.5)
            z = data[0, r, c]
            is_nodata = (nodata_value is not None) and (z == nodata_value)
            pixels_info.append({
                'x': x,
                'y': y,
                'z': z,
                'row_in_block': r,
                'col_in_block': c,
                'is_nodata': is_nodata
            })
    return pixels_info
