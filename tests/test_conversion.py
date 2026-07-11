"""Tests for RESQML 2.0.1 <-> 2.2 conversion using synthetic data."""

import pytest
import uuid as uuid_mod
from typing import Any, List

from energyml.eml.v2_0 import commonv2 as eml20
from energyml.eml.v2_3 import commonv2 as eml23
from energyml.resqml.v2_0_1 import resqmlv2 as r201
from energyml.resqml.v2_2 import resqmlv2 as r22
from energyml.utils.introspection import get_obj_uuid

from resqml_converter.converter import convert_objects
from resqml_converter.mappings.common import (
    convert_citation_201_to_23,
    convert_citation_23_to_201,
    convert_dor_201_to_23,
    convert_dor_23_to_201,
)
from resqml_converter.mappings.base import ConversionContext


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def uid():
    return str(uuid_mod.uuid4())


def citation_201(title):
    return eml20.Citation(
        title=title,
        originator="Test",
        creation="2026-01-01T00:00:00Z",
        format="test",
    )


def citation_22(title):
    return eml23.Citation(
        title=title,
        originator="Test",
        creation="2026-01-01T00:00:00Z",
        format="test",
    )


def dor_201(obj):
    cls_name = type(obj).__name__
    return eml20.DataObjectReference(
        content_type=f"application/x-resqml+xml;version=2.0;type=obj_{cls_name}",
        title=obj.citation.title,
        uuid=obj.uuid,
    )


def dor_22(obj):
    from energyml.utils.introspection import get_qualified_type_from_class
    qtype = get_qualified_type_from_class(type(obj))
    return eml23.DataObjectReference(
        qualified_type=qtype,
        title=obj.citation.title,
        uuid=obj.uuid,
    )


# ─── Citation Tests ───────────────────────────────────────────────────────────

class TestCitationConversion:
    def test_201_to_23(self):
        cit = citation_201("Test Title")
        result = convert_citation_201_to_23(cit)
        assert result.title == "Test Title"
        assert result.originator == "Test"
        assert isinstance(result, eml23.Citation)

    def test_23_to_201(self):
        cit = citation_22("Test Title")
        result = convert_citation_23_to_201(cit)
        assert result.title == "Test Title"
        assert isinstance(result, eml20.Citation)

    def test_none_handling(self):
        assert convert_citation_201_to_23(None) is None
        assert convert_citation_23_to_201(None) is None


# ─── Feature Conversion Tests ─────────────────────────────────────────────────

class TestFeatureConversion:
    def test_genetic_boundary_to_boundary_feature(self):
        """GeneticBoundaryFeature (horizon) -> BoundaryFeature."""
        obj = r201.GeneticBoundaryFeature(
            citation=citation_201("Horizon 1"),
            uuid=uid(),
            schema_version="2.0",
            genetic_boundary_kind=r201.GeneticBoundaryKind.HORIZON,
        )
        converted, ctx = convert_objects([obj], "201_to_22")
        assert len(converted) == 1
        assert isinstance(converted[0], r22.BoundaryFeature)
        assert converted[0].citation.title == "Horizon 1"
        assert converted[0].uuid == obj.uuid

    def test_tectonic_boundary_to_boundary_feature(self):
        """TectonicBoundaryFeature (fault) -> BoundaryFeature."""
        obj = r201.TectonicBoundaryFeature(
            citation=citation_201("Fault 1"),
            uuid=uid(),
            schema_version="2.0",
            tectonic_boundary_kind=r201.TectonicBoundaryKind.FAULT,
        )
        converted, ctx = convert_objects([obj], "201_to_22")
        assert len(converted) == 1
        assert isinstance(converted[0], r22.BoundaryFeature)

    def test_boundary_feature_to_genetic_boundary(self):
        """BoundaryFeature -> GeneticBoundaryFeature (default horizon)."""
        obj = r22.BoundaryFeature(
            citation=citation_22("Horizon 1"),
            uuid=uid(),
            schema_version="2.2",
            is_well_known=False,
        )
        converted, ctx = convert_objects([obj], "22_to_201")
        assert len(converted) == 1
        assert isinstance(converted[0], r201.GeneticBoundaryFeature)

    def test_boundary_feature_to_tectonic_with_fault_interp(self):
        """BoundaryFeature referenced by FaultInterpretation -> TectonicBoundaryFeature."""
        feat_uuid = uid()
        feat = r22.BoundaryFeature(
            citation=citation_22("Fault 1"),
            uuid=feat_uuid,
            schema_version="2.2",
            is_well_known=False,
        )
        interp = r22.FaultInterpretation(
            citation=citation_22("Fault Interp"),
            uuid=uid(),
            schema_version="2.2",
            domain=r22.Domain.DEPTH,
            interpreted_feature=dor_22(feat),
        )
        converted, ctx = convert_objects([feat, interp], "22_to_201")
        # Find the feature in converted
        feat_result = next(c for c in converted if get_obj_uuid(c) == feat_uuid)
        assert isinstance(feat_result, r201.TectonicBoundaryFeature)

    def test_organization_feature_to_model(self):
        """OrganizationFeature -> Model."""
        obj = r201.OrganizationFeature(
            citation=citation_201("Earth Model"),
            uuid=uid(),
            schema_version="2.0",
            organization_kind=r201.OrganizationKind.EARTH_MODEL,
        )
        converted, ctx = convert_objects([obj], "201_to_22")
        assert isinstance(converted[0], r22.Model)

    def test_model_to_organization_feature(self):
        """Model -> OrganizationFeature."""
        obj = r22.Model(
            citation=citation_22("Earth Model"),
            uuid=uid(),
            schema_version="2.2",
            is_well_known=False,
        )
        converted, ctx = convert_objects([obj], "22_to_201")
        assert isinstance(converted[0], r201.OrganizationFeature)

    def test_wellbore_feature_roundtrip(self):
        """WellboreFeature preserves UUID through roundtrip."""
        original_uuid = uid()
        obj = r201.WellboreFeature(
            citation=citation_201("Well A"),
            uuid=original_uuid,
            schema_version="2.0",
        )
        converted_22, _ = convert_objects([obj], "201_to_22")
        assert converted_22[0].uuid == original_uuid

        converted_201, _ = convert_objects(converted_22, "22_to_201")
        assert converted_201[0].uuid == original_uuid
        assert isinstance(converted_201[0], r201.WellboreFeature)

    def test_seismic_lattice_201_to_22(self):
        """SeismicLatticeFeature: flat fields -> IntegerLatticeArray."""
        obj = r201.SeismicLatticeFeature(
            citation=citation_201("Seismic Survey"),
            uuid=uid(),
            schema_version="2.0",
            crossline_count=100,
            crossline_index_increment=1,
            first_crossline_index=1000,
            first_inline_index=500,
            inline_count=200,
            inline_index_increment=1,
        )
        converted, _ = convert_objects([obj], "201_to_22")
        result = converted[0]
        assert isinstance(result, r22.SeismicLatticeFeature)
        assert result.crossline_labels.start_value == 1000
        assert result.inline_labels.start_value == 500

    def test_seismic_lattice_22_to_201(self):
        """SeismicLatticeFeature: IntegerLatticeArray -> flat fields."""
        obj = r22.SeismicLatticeFeature(
            citation=citation_22("Seismic Survey"),
            uuid=uid(),
            schema_version="2.2",
            is_well_known=False,
            crossline_labels=r22.IntegerLatticeArray(
                start_value=1000,
                offset=[eml23.IntegerConstantArray(value=1, count=99)],
            ),
            inline_labels=r22.IntegerLatticeArray(
                start_value=500,
                offset=[eml23.IntegerConstantArray(value=1, count=199)],
            ),
        )
        converted, _ = convert_objects([obj], "22_to_201")
        result = converted[0]
        assert isinstance(result, r201.SeismicLatticeFeature)
        assert result.first_crossline_index == 1000
        assert result.crossline_count == 100
        assert result.first_inline_index == 500
        assert result.inline_count == 200


# ─── Interpretation Conversion Tests ──────────────────────────────────────────

class TestInterpretationConversion:
    def test_horizon_interp_201_to_22(self):
        feat = r201.GeneticBoundaryFeature(
            citation=citation_201("H1"), uuid=uid(), schema_version="2.0",
            genetic_boundary_kind=r201.GeneticBoundaryKind.HORIZON,
        )
        interp = r201.HorizonInterpretation(
            citation=citation_201("H1 Interp"), uuid=uid(), schema_version="2.0",
            domain=r201.Domain.DEPTH,
            interpreted_feature=dor_201(feat),
        )
        converted, _ = convert_objects([feat, interp], "201_to_22")
        interp_22 = next(c for c in converted if isinstance(c, r22.HorizonInterpretation))
        assert interp_22.domain == r22.Domain.DEPTH
        assert interp_22.interpreted_feature is not None
        assert interp_22.interpreted_feature.uuid == feat.uuid

    def test_fault_interp_201_to_22_loses_is_listric(self):
        feat = r201.TectonicBoundaryFeature(
            citation=citation_201("F1"), uuid=uid(), schema_version="2.0",
            tectonic_boundary_kind=r201.TectonicBoundaryKind.FAULT,
        )
        interp = r201.FaultInterpretation(
            citation=citation_201("F1 Interp"), uuid=uid(), schema_version="2.0",
            domain=r201.Domain.DEPTH,
            interpreted_feature=dor_201(feat),
            is_listric=True,
        )
        converted, ctx = convert_objects([feat, interp], "201_to_22")
        interp_22 = next(c for c in converted if isinstance(c, r22.FaultInterpretation))
        assert not hasattr(interp_22, 'is_listric') or getattr(interp_22, 'is_listric', None) is None
        assert len(ctx.warnings) > 0  # Should warn about is_listric loss

    def test_wellbore_interp_roundtrip(self):
        feat = r201.WellboreFeature(
            citation=citation_201("Well"), uuid=uid(), schema_version="2.0",
        )
        interp = r201.WellboreInterpretation(
            citation=citation_201("Well Interp"), uuid=uid(), schema_version="2.0",
            domain=r201.Domain.DEPTH,
            interpreted_feature=dor_201(feat),
            is_drilled=True,
        )
        converted_22, _ = convert_objects([feat, interp], "201_to_22")
        interp_22 = next(c for c in converted_22 if isinstance(c, r22.WellboreInterpretation))
        assert interp_22.is_drilled is True


# ─── DOR Conversion Tests ─────────────────────────────────────────────────────

class TestDORConversion:
    def test_dor_201_to_23_content_type_to_qualified_type(self):
        ctx = ConversionContext(direction="201_to_22")
        dor = eml20.DataObjectReference(
            content_type="application/x-resqml+xml;version=2.0;type=obj_IjkGridRepresentation",
            title="My Grid",
            uuid=uid(),
        )
        result = convert_dor_201_to_23(dor, ctx)
        assert result.qualified_type == "resqml22.IjkGridRepresentation"
        assert result.title == "My Grid"
        assert result.uuid == dor.uuid

    def test_dor_23_to_201_qualified_type_to_content_type(self):
        ctx = ConversionContext(direction="22_to_201")
        dor = eml23.DataObjectReference(
            qualified_type="resqml22.IjkGridRepresentation",
            title="My Grid",
            uuid=uid(),
        )
        result = convert_dor_23_to_201(dor, ctx)
        assert "obj_IjkGridRepresentation" in result.content_type
        assert "version=2.0" in result.content_type

    def test_dor_type_mapping_boundary_feature(self):
        ctx = ConversionContext(direction="201_to_22")
        dor = eml20.DataObjectReference(
            content_type="application/x-resqml+xml;version=2.0;type=obj_GeneticBoundaryFeature",
            title="Horizon",
            uuid=uid(),
        )
        result = convert_dor_201_to_23(dor, ctx)
        assert result.qualified_type == "resqml22.BoundaryFeature"


# ─── CRS Conversion Tests ────────────────────────────────────────────────────

class TestCRSConversion:
    def test_local_depth_3d_crs_stays_flat(self):
        """LocalDepth3dCrs stays flat in 2.2 (RDDMS-compatible, no compound decomposition)."""
        crs = r201.LocalDepth3DCrs(
            citation=citation_201("My CRS"),
            uuid=uid(), schema_version="2.0",
            xoffset=100.0, yoffset=200.0, zoffset=0.0,
            zincreasing_downward=True,
            projected_axis_order=r201.AxisOrder2D.EASTING_NORTHING,
            projected_uom=r201.LengthUom.M,
            vertical_uom=r201.LengthUom.M,
            areal_rotation=r201.PlaneAngleMeasure(value=0.0, uom=r201.PlaneAngleUom.DEGA),
            projected_crs=eml20.ProjectedCrsEpsgCode(epsg_code=32631),
            vertical_crs=eml20.VerticalCrsEpsgCode(epsg_code=5714),
        )
        converted, ctx = convert_objects([crs], "201_to_22")
        # RDDMS-compatible: stays as LocalDepth3dCrs (flat), no compound decomposition
        assert len(converted) == 1
        result = converted[0]
        assert isinstance(result, r201.LocalDepth3DCrs)
        assert result.uuid == crs.uuid
        assert result.schema_version == "2.2"
        assert result.xoffset == 100.0
        assert result.projected_uom == r201.LengthUom.M

    def test_compound_crs_to_local_depth_3d(self):
        """LocalEngineeringCompoundCrs -> LocalDepth3dCrs."""
        vert_uuid = uid()
        twod_uuid = uid()
        comp_uuid = uid()

        vert = eml23.VerticalCrs(
            citation=citation_22("Vert CRS"), uuid=vert_uuid, schema_version="2.3",
            direction=eml23.VerticalDirection.DOWN,
            uom="m",
            abstract_vertical_crs=eml23.VerticalEpsgCrs(epsg_code=5714),
        )
        twod = eml23.LocalEngineering2DCrs(
            citation=citation_22("2D CRS"), uuid=twod_uuid, schema_version="2.3",
            azimuth=eml23.PlaneAngleMeasureExt(value=0.0, uom="dega"),
            azimuth_reference=eml23.NorthReferenceKind.TRUE_NORTH,
            origin_projected_coordinate1=100.0,
            origin_projected_coordinate2=200.0,
            horizontal_axes=eml23.HorizontalAxes(
                direction1=eml23.AxisDirectionKind.EAST,
                direction2=eml23.AxisDirectionKind.NORTH,
                uom="m", is_time=False,
            ),
            origin_projected_crs=eml23.ProjectedCrs(
                citation=citation_22("UTM 31N"), uuid=uid(), schema_version="2.3",
                axis_order=eml23.AxisOrder2D.EASTING_NORTHING,
                abstract_projected_crs=eml23.ProjectedEpsgCrs(epsg_code=32631),
                uom="m",
            ),
        )
        compound = eml23.LocalEngineeringCompoundCrs(
            citation=citation_22("Compound CRS"), uuid=comp_uuid, schema_version="2.3",
            origin_vertical_coordinate=0.0,
            vertical_axis=eml23.VerticalAxis(direction=eml23.VerticalDirection.DOWN, uom="m", is_time=False),
            vertical_crs=eml23.DataObjectReference(uuid=vert_uuid, title="Vert", qualified_type="eml23.VerticalCrs"),
            local_engineering2d_crs=eml23.DataObjectReference(uuid=twod_uuid, title="2D", qualified_type="eml23.LocalEngineering2DCrs"),
        )
        converted, _ = convert_objects([vert, twod, compound], "22_to_201")
        crs_201 = next((c for c in converted if isinstance(c, r201.LocalDepth3DCrs)), None)
        assert crs_201 is not None
        assert crs_201.uuid == comp_uuid
        assert crs_201.xoffset == 100.0
        assert crs_201.yoffset == 200.0
        assert crs_201.zincreasing_downward is True


# ─── Integration Test: Full Object Graph ─────────────────────────────────────

class TestFullConversion:
    def test_201_to_22_full_graph(self):
        """Convert a complete 2.0.1 object graph to 2.2."""
        crs = r201.LocalDepth3DCrs(
            citation=citation_201("CRS"), uuid=uid(), schema_version="2.0",
            xoffset=0.0, yoffset=0.0, zoffset=0.0,
            zincreasing_downward=True,
            projected_axis_order=r201.AxisOrder2D.EASTING_NORTHING,
            projected_uom=r201.LengthUom.M,
            vertical_uom=r201.LengthUom.M,
            areal_rotation=r201.PlaneAngleMeasure(value=0.0, uom=r201.PlaneAngleUom.DEGA),
            projected_crs=eml20.ProjectedCrsEpsgCode(epsg_code=32631),
            vertical_crs=eml20.VerticalCrsEpsgCode(epsg_code=5714),
        )
        feat = r201.GeneticBoundaryFeature(
            citation=citation_201("Horizon"), uuid=uid(), schema_version="2.0",
            genetic_boundary_kind=r201.GeneticBoundaryKind.HORIZON,
        )
        interp = r201.HorizonInterpretation(
            citation=citation_201("Horizon Interp"), uuid=uid(), schema_version="2.0",
            domain=r201.Domain.DEPTH,
            interpreted_feature=dor_201(feat),
        )
        org = r201.OrganizationFeature(
            citation=citation_201("Model"), uuid=uid(), schema_version="2.0",
            organization_kind=r201.OrganizationKind.EARTH_MODEL,
        )
        well_feat = r201.WellboreFeature(
            citation=citation_201("Well A"), uuid=uid(), schema_version="2.0",
        )

        objects = [crs, feat, interp, org, well_feat]
        converted, ctx = convert_objects(objects, "201_to_22")

        assert len(ctx.errors) == 0
        # Should have: flat CRS + BoundaryFeature + HorizonInterp + Model + WellboreFeature
        assert len(converted) >= len(objects)

        # Check types
        type_names = [type(c).__name__ for c in converted]
        assert "BoundaryFeature" in type_names
        assert "HorizonInterpretation" in type_names
        assert "Model" in type_names
        assert "WellboreFeature" in type_names
        assert "LocalDepth3DCrs" in type_names  # stays flat (RDDMS-compatible)
