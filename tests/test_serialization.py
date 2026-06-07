"""Tests for OSDU JSON serialization compatibility and EPC structure validation."""

import pytest
import uuid as uuid_mod

from energyml.eml.v2_0 import commonv2 as eml20
from energyml.eml.v2_3 import commonv2 as eml23
from energyml.resqml.v2_0_1 import resqmlv2 as r201
from energyml.resqml.v2_2 import resqmlv2 as r22
from energyml.utils.serialization import serialize_xml, serialize_json, JSON_VERSION
from energyml.utils.introspection import get_qualified_type_from_class

from resqml_converter.converter import convert_objects


def uid():
    return str(uuid_mod.uuid4())


def citation_201(title):
    return eml20.Citation(title=title, originator="Test", creation="2026-01-01T00:00:00Z", format="test")


def citation_22(title):
    return eml23.Citation(title=title, originator="Test", creation="2026-01-01T00:00:00Z", format="test")


class TestXMLSerialization:
    """Verify converted objects produce valid XML."""

    def test_boundary_feature_22_serializes(self):
        feat = r201.GeneticBoundaryFeature(
            citation=citation_201("Horizon"), uuid=uid(), schema_version="2.0",
            genetic_boundary_kind=r201.GeneticBoundaryKind.HORIZON,
        )
        converted, _ = convert_objects([feat], "201_to_22")
        xml = serialize_xml(converted[0])
        assert "BoundaryFeature" in xml
        assert "Horizon" in xml
        assert "2.2" in xml or "resqml22" in xml.lower() or "resqmlv2" in xml.lower()

    def test_wellbore_feature_201_serializes(self):
        feat = r22.WellboreFeature(
            citation=citation_22("Well"), uuid=uid(), schema_version="2.2",
            is_well_known=False,
        )
        converted, _ = convert_objects([feat], "22_to_201")
        xml = serialize_xml(converted[0])
        assert "WellboreFeature" in xml
        assert "Well" in xml

    def test_horizon_interp_22_xml_has_correct_namespace(self):
        feat = r201.GeneticBoundaryFeature(
            citation=citation_201("H"), uuid=uid(), schema_version="2.0",
            genetic_boundary_kind=r201.GeneticBoundaryKind.HORIZON,
        )
        interp = r201.HorizonInterpretation(
            citation=citation_201("HI"), uuid=uid(), schema_version="2.0",
            domain=r201.Domain.DEPTH,
            interpreted_feature=eml20.DataObjectReference(
                content_type="application/x-resqml+xml;version=2.0;type=obj_GeneticBoundaryFeature",
                title="H", uuid=feat.uuid,
            ),
        )
        converted, _ = convert_objects([feat, interp], "201_to_22")
        hi_22 = next(c for c in converted if isinstance(c, r22.HorizonInterpretation))
        xml = serialize_xml(hi_22)
        assert "HorizonInterpretation" in xml
        assert "energistics" in xml.lower() or "resqml" in xml.lower()


class TestOSDUJsonSerialization:
    """Verify converted objects can serialize to OSDU JSON format."""

    def test_boundary_feature_22_to_osdu_json(self):
        feat = r201.GeneticBoundaryFeature(
            citation=citation_201("Horizon"), uuid=uid(), schema_version="2.0",
            genetic_boundary_kind=r201.GeneticBoundaryKind.HORIZON,
        )
        converted, _ = convert_objects([feat], "201_to_22")
        json_str = serialize_json(converted[0], json_version=JSON_VERSION.OSDU_OFFICIAL)
        assert "Horizon" in json_str
        assert len(json_str) > 10

    def test_model_22_to_osdu_json(self):
        org = r201.OrganizationFeature(
            citation=citation_201("Earth Model"), uuid=uid(), schema_version="2.0",
            organization_kind=r201.OrganizationKind.EARTH_MODEL,
        )
        converted, _ = convert_objects([org], "201_to_22")
        model_22 = next(c for c in converted if isinstance(c, r22.Model))
        json_str = serialize_json(model_22, json_version=JSON_VERSION.OSDU_OFFICIAL)
        assert "Earth Model" in json_str

    def test_wellbore_feature_201_to_osdu_json(self):
        feat = r22.WellboreFeature(
            citation=citation_22("Well"), uuid=uid(), schema_version="2.2",
            is_well_known=False,
        )
        converted, _ = convert_objects([feat], "22_to_201")
        json_str = serialize_json(converted[0], json_version=JSON_VERSION.OSDU_OFFICIAL)
        assert "Well" in json_str


class TestQualifiedTypes:
    """Verify converted objects have correct qualified types for OSDU/ETP."""

    def test_boundary_feature_qualified_type(self):
        feat = r201.GeneticBoundaryFeature(
            citation=citation_201("H"), uuid=uid(), schema_version="2.0",
            genetic_boundary_kind=r201.GeneticBoundaryKind.HORIZON,
        )
        converted, _ = convert_objects([feat], "201_to_22")
        qt = get_qualified_type_from_class(type(converted[0]))
        assert "resqml" in qt
        assert "BoundaryFeature" in qt

    def test_model_qualified_type(self):
        org = r201.OrganizationFeature(
            citation=citation_201("M"), uuid=uid(), schema_version="2.0",
            organization_kind=r201.OrganizationKind.EARTH_MODEL,
        )
        converted, _ = convert_objects([org], "201_to_22")
        model = next(c for c in converted if isinstance(c, r22.Model))
        qt = get_qualified_type_from_class(type(model))
        assert "Model" in qt

    def test_ijk_grid_qualified_type(self):
        """IjkGridRepresentation retains its type name across versions."""
        qt_201 = get_qualified_type_from_class(r201.IjkGridRepresentation)
        qt_22 = get_qualified_type_from_class(r22.IjkGridRepresentation)
        assert "IjkGridRepresentation" in qt_201
        assert "IjkGridRepresentation" in qt_22


class TestNamespaceCorrectness:
    """Verify namespace handling is correct for both versions."""

    def test_201_objects_use_eml20_module(self):
        feat = r22.BoundaryFeature(
            citation=citation_22("H"), uuid=uid(), schema_version="2.2",
            is_well_known=False,
        )
        converted, _ = convert_objects([feat], "22_to_201")
        result = converted[0]
        assert "v2_0_1" in type(result).__module__ or "v2_0" in type(result).__module__

    def test_22_objects_use_eml23_module(self):
        feat = r201.GeneticBoundaryFeature(
            citation=citation_201("H"), uuid=uid(), schema_version="2.0",
            genetic_boundary_kind=r201.GeneticBoundaryKind.HORIZON,
        )
        converted, _ = convert_objects([feat], "201_to_22")
        result = converted[0]
        assert "v2_2" in type(result).__module__

    def test_citation_version_matches_target(self):
        """After conversion, citation should be in correct EML version module."""
        feat = r201.WellboreFeature(
            citation=citation_201("W"), uuid=uid(), schema_version="2.0",
        )
        converted, _ = convert_objects([feat], "201_to_22")
        cit = converted[0].citation
        assert isinstance(cit, eml23.Citation)

        # Reverse
        rev, _ = convert_objects(converted, "22_to_201")
        cit_201 = rev[0].citation
        assert isinstance(cit_201, eml20.Citation)
