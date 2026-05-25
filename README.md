# RAS-TRX

A desktop GUI application for converting raster DEM (Digital Elevation Model) coordinates between various ITRF realizations and NAD83(CSRS), with support for epoch transformations and multiple vertical datums.

RAS-TRX is a raster-focused fork of [LAS-TRX](https://github.com/HakaiInstitute/LAS-TRX), extending its coordinate transformation capabilities to GeoTIFF raster files.

**Developed by:** Santiago Gonzalez Arriola (Hakai Institute)  
**Original LAS-TRX author:** Taylor Denouden (Hakai Institute)

---

## Features

- Transform raster DEM elevation values between ITRF realizations (ITRF88–ITRF2020) and NAD83(CSRS)
- Epoch-to-epoch transformations
- Vertical datum support: GRS80, WGS84, CGVD2013/CGG2013a, CGVD2013/CGG2013, CGVD28/HT2_2010v70
- Coordinate type support: Geographic and UTM zones 3–23
- Batch processing via wildcard input patterns (`*.tif`)
- Memory-efficient block-windowed processing for large rasters
- Save/load transformation configurations as JSON
- Parallel processing using all available CPU cores

## Installation

Requires Python 3.9–3.11 and [Poetry](https://python-poetry.org/).

```bash
git clone https://github.com/HakaiInstitute/RAS-TRX.git
cd RAS-TRX
poetry install
```

On first run, the application will automatically download the required PROJ grid files for Canadian geodetic transformations (internet connection required, ~50 MB).

## Usage

```bash
poetry run python -m ras_trx
```

### Batch Processing

Use `*` in the input file path to select multiple files:
```
C:\path\to\files\*.tif
```

Use `{}` in the output path to generate names from input stems:
```
C:\path\to\files\{}_transformed.tif
```

## Development

```bash
# Run with debug mode (pre-populates fields)
DEBUG=1 poetry run python -m ras_trx

# Run tests
poetry run pytest

# Lint and format
poetry run ruff format .
poetry run ruff check . --fix
```

## License

See [LICENSE](LICENSE).
