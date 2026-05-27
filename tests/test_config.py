from datetime import date

import pytest
from csrspy.enums import CoordType, Reference, VerticalDatum
from pyproj.crs import CompoundCRS, GeographicCRS

from ras_trx.config import (
    CSRSPYConfig,
    ReferenceConfig,
    TransformConfig,
    TrxCoordType,
    TrxReference,
    TrxVd,
)


class TestTrxCoordType:
    def test_geog_is_not_utm(self):
        assert TrxCoordType.GEOG.is_utm() is False

    def test_utm_is_utm(self):
        assert TrxCoordType.UTM10.is_utm() is True

    def test_utm_zone_property(self):
        assert TrxCoordType.UTM10.utm_zone == 10
        assert TrxCoordType.UTM3.utm_zone == 3

    def test_utm_zone_raises_for_geog(self):
        with pytest.raises(ValueError):
            _ = TrxCoordType.GEOG.utm_zone

    def test_from_utm_zone_valid(self):
        assert TrxCoordType.from_utm_zone(10) == TrxCoordType.UTM10
        assert TrxCoordType.from_utm_zone(3) == TrxCoordType.UTM3

    def test_from_utm_zone_below_range(self):
        with pytest.raises(ValueError):
            TrxCoordType.from_utm_zone(2)

    def test_from_utm_zone_above_range(self):
        with pytest.raises(ValueError):
            TrxCoordType.from_utm_zone(24)

    def test_to_csrspy(self):
        assert TrxCoordType.UTM10.to_csrspy() == CoordType.UTM10
        assert TrxCoordType.GEOG.to_csrspy() == CoordType.GEOG


class TestTrxReference:
    def test_nad83csrs_geodetic_crs(self):
        crs = TrxReference.NAD83CSRS.geodetic_crs
        assert isinstance(crs, GeographicCRS)
        assert crs.to_epsg() == 4617

    def test_itrf20_geodetic_crs(self):
        crs = TrxReference.ITRF20.geodetic_crs
        assert isinstance(crs, GeographicCRS)
        assert crs.to_epsg() == 9989

    def test_wgs84_geodetic_crs(self):
        crs = TrxReference.WGS84.geodetic_crs
        assert isinstance(crs, GeographicCRS)
        assert crs.to_epsg() == 4326

    def test_to_csrspy(self):
        assert TrxReference.NAD83CSRS.to_csrspy() == Reference.NAD83CSRS
        assert TrxReference.ITRF20.to_csrspy() == Reference.ITRF20
        assert TrxReference.ITRF14.to_csrspy() == Reference.ITRF14


class TestTrxVd:
    def test_wgs84_vertical_crs_is_none(self):
        assert TrxVd.WGS84.vertical_crs is None

    def test_grs80_vertical_crs_is_none(self):
        assert TrxVd.GRS80.vertical_crs is None

    def test_cgg2013_vertical_crs(self):
        from pyproj.crs import VerticalCRS

        assert isinstance(TrxVd.CGG2013.vertical_crs, VerticalCRS)

    def test_cgg2013a_vertical_crs(self):
        from pyproj.crs import VerticalCRS

        assert isinstance(TrxVd.CGG2013A.vertical_crs, VerticalCRS)

    def test_ht2_vertical_crs(self):
        from pyproj.crs import VerticalCRS

        assert isinstance(TrxVd.HT2_2010v70.vertical_crs, VerticalCRS)

    def test_to_csrspy(self):
        assert TrxVd.WGS84.to_csrspy() == VerticalDatum.WGS84
        assert TrxVd.CGG2013A.to_csrspy() == VerticalDatum.CGG2013A
        assert TrxVd.HT2_2010v70.to_csrspy() == VerticalDatum.HT2_2010v70


class TestReferenceConfig:
    def _config(
        self,
        ref=TrxReference.NAD83CSRS,
        epoch=date(2010, 1, 1),
        vd=TrxVd.GRS80,
        coord=TrxCoordType.GEOG,
    ):
        return ReferenceConfig(ref_frame=ref, epoch=epoch, vd=vd, coord_type=coord)

    def test_geographic_no_vertical_crs_is_3d(self):
        crs = self._config().crs
        assert crs.is_geographic

    def test_geographic_with_vertical_crs_is_compound(self):
        crs = self._config(vd=TrxVd.CGG2013).crs
        assert isinstance(crs, CompoundCRS)

    def test_utm_no_vertical_crs_is_projected(self):
        crs = self._config(coord=TrxCoordType.UTM10).crs
        assert crs.is_projected

    def test_utm_with_vertical_crs_is_compound(self):
        crs = self._config(coord=TrxCoordType.UTM10, vd=TrxVd.CGG2013).crs
        assert isinstance(crs, CompoundCRS)


class TestTransformConfig:
    def test_to_csrspy_returns_correct_type(self):
        config = TransformConfig(
            origin=ReferenceConfig(
                ref_frame=TrxReference.ITRF14,
                epoch=date(2010, 1, 1),
                vd=TrxVd.GRS80,
                coord_type=TrxCoordType.UTM10,
            ),
            destination=ReferenceConfig(
                ref_frame=TrxReference.NAD83CSRS,
                epoch=date(2020, 1, 1),
                vd=TrxVd.CGG2013A,
                coord_type=TrxCoordType.UTM10,
            ),
        )
        result = config.to_csrspy()
        assert isinstance(result, CSRSPYConfig)
        assert result.s_ref_frame == Reference.ITRF14
        assert result.t_ref_frame == Reference.NAD83CSRS
        assert result.t_vd == VerticalDatum.CGG2013A
