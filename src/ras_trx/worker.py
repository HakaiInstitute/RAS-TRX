import multiprocessing
import os
from concurrent import futures
from pathlib import Path
from time import sleep

import numpy as np
import rasterio
from csrspy import CSRSTransformer
from PyQt6.QtCore import QThread, pyqtSignal as Signal

from ras_trx.config import TransformConfig
from ras_trx.dem_utils import get_raster_points_and_values, transform_raster_profile
from ras_trx.logger import logger


class TransformWorker(QThread):
    started = Signal()
    finished = Signal()
    progress = Signal(int)
    success = Signal()
    error = Signal(BaseException)

    def __init__(
        self, config: TransformConfig, input_pattern: str, output_pattern: str
    ):
        super().__init__(parent=None)
        self.config = config
        self.input_pattern = Path(input_pattern)
        self.output_pattern = output_pattern
        self.input_files = [
            f
            for f in self.input_pattern.parent.glob(self.input_pattern.name)
            if f.is_file() and f.suffix.lower() in [".tif", ".tiff"]
        ]
        self.output_files = [
            Path(output_pattern.format(f.stem)) for f in self.input_files
        ]

        logger.info(f"Found {len(self.input_files)} input files")
        logger.info(f"Transform config: {self.config}")
        logger.info(f"Input CRS\n{self.config.origin.crs.to_wkt(pretty=True)}")
        logger.info(f"Output CRS\n{self.config.destination.crs.to_wkt(pretty=True)}")
        logger.info("Calculating total number of iterations")

        num_workers = min(os.cpu_count(), 61)
        self.pool = futures.ProcessPoolExecutor(max_workers=num_workers)
        self.manager = multiprocessing.Manager()
        self.lock = self.manager.RLock()
        self.current_iter = self.manager.Value("i", 0)
        logger.info(f"CPU process pool size: {num_workers}")

        self.total_iters = 0
        for input_file in self.input_files:
            with rasterio.open(str(input_file)) as src:
                # Count the number of blocks/windows for progress tracking
                self.total_iters += len(list(src.block_windows()))
        logger.info(f"Total iterations until complete: {self.total_iters}")

        self.futs = {}

    def check_file_names(self):
        for in_file, out_file in zip(self.input_files, self.output_files):
            if in_file == out_file:
                raise AssertionError(
                    "Input file name matches output file name. "
                    "Aborting because this would overwrite the input file."
                )

        if len(self.output_files) != len(list(set(self.output_files))):
            raise AssertionError(
                "Duplicate output file name detected. "
                "Use a format string for the output path to output a file based on the "
                "stem of the corresponding input file. "
                r"e.g. 'C:\\some\path\{}_transformed.tif'"
            )

    def _do_transform(self):
        self.check_file_names()
        self.futs = {}
        for input_file, output_file in zip(self.input_files, self.output_files):
            if not Path(output_file).suffix:
                output_file += ".tif"

            fut = self.pool.submit(
                transform_dem,
                self.config,
                input_file,
                output_file,
                self.lock,
                self.current_iter,
            )
            fut.add_done_callback(self.on_process_complete)
            self.futs[fut] = (input_file, output_file)

        while any([f.running() for f in self.futs.keys()]):
            self.progress.emit(self.progress_val)
            sleep(0.1)
        self.progress.emit(self.progress_val)

    def on_process_complete(self, fut: futures.Future):
        input_file, output_file = self.futs[fut]
        err = fut.exception()
        if err is not None:
            logger.error(f"Error transforming {input_file}")
            raise err
        else:
            logger.info(f"{input_file} -> {output_file}")

    @property
    def progress_val(self):
        return int(100 * self.current_iter.value / float(self.total_iters))

    def run(self):
        self.started.emit()

        try:
            self._do_transform()
            self.success.emit()
        except Exception as e:
            self.error.emit(e)

        self.finished.emit()


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
                        coords_to_transform.append((
                            pixel_info["x"],
                            pixel_info["y"],
                            z,
                        ))
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
