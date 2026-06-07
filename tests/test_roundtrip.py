"""Roundtrip tests: verify 2.0.1 -> 2.2 -> 2.0.1 preserves data integrity."""

import pytest
import uuid as uuid_mod

from energyml.eml.v2_0 import commonv2 as eml20
from energyml.eml.v2_3 import commonv2 as eml23
from energyml.resqml.v2_0_1 import resqmlv2 as r201
from energyml.resqml.v2_2 import resqmlv2 as r22
from energyml.utils.introspection import get_obj_uuid

from resqml_converter.converter import convert_objects


def uid():
    return str(uuid_mod.uuid4())


def citation_201(title):
    return eml20.Citation(title=title, originator="Test", creation="2026-01-01T00:00:00Z", format="test")


def dor_201(obj):
    return eml20.DataObjectReference(
        content_type=f"application/x-resqml+xml;version=2.0;type=obj_{type(obj).__name__}",
        title=obj.citation.title, uuid=obj.uuid,
    )


class TestRoundtrip:
    def test_wellbore_feature_roundtrip(self):
        """UUID and title preserved through 201 -> 22 -> 201."""
        original = r201.WellboreFeature(
            citation=citation_201("Well Alpha"), uuid=uid(), schema_version="2.0",
        )
        # Forward
        fwd, _ = convert_objects([original], "201_to_22")
        assert len(fwd) == 1
        assert fwd[0].uuid == original.uuid

        # Reverse
        rev, _ = convert_objects(fwd, "22_to_201")
        assert len(rev) == 1
        assert rev[0].uuid == original.uuid
        assert rev[0].citation.title == "Well Alpha"
        assert isinstance(rev[0], r201.WellboreFeature)

    def test_horizon_interp_roundtrip(self):
        """HorizonInterpretation preserves domain and references."""
        feat_uuid = uid()
        feat = r201.GeneticBoundaryFeature(
            citation=citation_201("H1"), uuid=feat_uuid, schema_version="2.0",
            genetic_boundary_kind=r201.GeneticBoundaryKind.HORIZON,
        )
        interp = r201.HorizonInterpretation(
            citation=citation_201("H1 Interp"), uuid=uid(), schema_version="2.0",
            domain=r201.Domain.DEPTH,
            interpreted_feature=dor_201(feat),
        )

        # Forward
        fwd, _ = convert_objects([feat, interp], "201_to_22")
        interp_22 = next(c for c in fwd if isinstance(c, r22.HorizonInterpretation))
        assert interp_22.domain == r22.Domain.DEPTH
        assert interp_22.interpreted_feature.uuid == feat_uuid

        # Reverse
        rev, _ = convert_objects(fwd, "22_to_201")
        interp_201 = next(c for c in rev if isinstance(c, r201.HorizonInterpretation))
        assert interp_201.domain == r201.Domain.DEPTH
        assert interp_201.interpreted_feature.uuid == feat_uuid

    def test_seismic_lattice_roundtrip(self):
        """SeismicLatticeFeature field values preserved through roundtrip."""
        original = r201.SeismicLatticeFeature(
            citation=citation_201("Survey"), uuid=uid(), schema_version="2.0",
            crossline_count=150,
            crossline_index_increment=2,
            first_crossline_index=500,
            first_inline_index=100,
            inline_count=300,
            inline_index_increment=1,
        )

        # Forward
        fwd, _ = convert_objects([original], "201_to_22")
        assert isinstance(fwd[0], r22.SeismicLatticeFeature)

        # Reverse
        rev, _ = convert_objects(fwd, "22_to_201")
        result = rev[0]
        assert isinstance(result, r201.SeismicLatticeFeature)
        assert result.crossline_count == 150
        assert result.crossline_index_increment == 2
        assert result.first_crossline_index == 500
        assert result.first_inline_index == 100
        assert result.inline_count == 300
        assert result.inline_index_increment == 1

    def test_multi_object_graph_roundtrip(self):
        """Complete object graph roundtrip preserves object count and UUIDs."""
        feat1 = r201.GeneticBoundaryFeature(
            citation=citation_201("H1"), uuid=uid(), schema_version="2.0",
            genetic_boundary_kind=r201.GeneticBoundaryKind.HORIZON,
        )
        feat2 = r201.TectonicBoundaryFeature(
            citation=citation_201("F1"), uuid=uid(), schema_version="2.0",
            tectonic_boundary_kind=r201.TectonicBoundaryKind.FAULT,
        )
        well = r201.WellboreFeature(
            citation=citation_201("W1"), uuid=uid(), schema_version="2.0",
        )
        interp1 = r201.HorizonInterpretation(
            citation=citation_201("H1 Interp"), uuid=uid(), schema_version="2.0",
            domain=r201.Domain.DEPTH,
            interpreted_feature=dor_201(feat1),
        )
        interp2 = r201.FaultInterpretation(
            citation=citation_201("F1 Interp"), uuid=uid(), schema_version="2.0",
            domain=r201.Domain.DEPTH,
            interpreted_feature=dor_201(feat2),
            is_listric=False,
        )

        objects = [feat1, feat2, well, interp1, interp2]
        original_uuids = {get_obj_uuid(o) for o in objects}

        # Forward
        fwd, ctx_fwd = convert_objects(objects, "201_to_22")
        assert len(ctx_fwd.errors) == 0
        fwd_uuids = {get_obj_uuid(o) for o in fwd}
        assert original_uuids.issubset(fwd_uuids)

        # Reverse
        rev, ctx_rev = convert_objects(fwd, "22_to_201")
        assert len(ctx_rev.errors) == 0
        rev_uuids = {get_obj_uuid(o) for o in rev}
        assert original_uuids.issubset(rev_uuids)
