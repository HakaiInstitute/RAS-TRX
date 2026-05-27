#!/usr/bin/env bash
set -e
uv run pyinstaller \
    --onefile \
    --windowed \
    --collect-all rasterio \
    --collect-all pyproj \
    --collect-all numpy \
    --icon="src/ras_trx/resources/ras-trx.icns" \
    --add-data="src/ras_trx/resources/ras-trx.ico:resources" \
    --add-data="src/ras_trx/resources/*.ui:resources" \
    --name=RAS-TRX \
    src/ras_trx/__main__.py
