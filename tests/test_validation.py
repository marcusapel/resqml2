"""Validation tests using Geosiris energyml validation pipeline."""

import pytest
import uuid as uuid_mod

from energyml.eml.v2_0 import commonv2 as eml20
from energyml.eml.v2_3 import commonv2 as eml23
from energyml.resqml.v2_0_1 import resqmlv2 as r201
from energyml.resqml.v2_2 import resqmlv2 as r22
from energyml.utils.epc import Epc
from energyml.utils.validation import validate_epc, validate_objects

from resqml_converter.converter import convert_objects
from resqml_converter.validation import validate_output, validate_single_object


def uid():
    return str(uuid_mod.uuid4())


def citation_201(title):
    return eml20.Citation(title=title, originator="Test", creation="2026-01-01T00:00:00Z", format="test")


def citation_22(title):
    return eml23.Citation(title=title, originator="Test", creation="2026-01-01T00:00:00Z", format="test")


class TestValidation:
    def test_validate_converted_22_objects(self):
        """Validate that converted 2.2 objects pass energyml schema validation."""
        feat = r201.GeneticBoundaryFeature(
            citation=citation_201("Horizon"), uuid=uid(), schema_version="2.0",
            genetic_boundary_kind=r201.GeneticBoundaryKind.HORIZON,
        )
        converted, ctx = convert_objects([feat], "201_to_22")
        assert len(converted) > 0

        # Validate with energyml
        errors = validate_objects(converted)
        # Filter only critical errors (not warnings about missing references)
        critical = [e for e in errors if "Mandatory" in str(type(e).__name__)]
        assert len(critical) == 0, f"Validation errors: {critical}"

    def test_validate_converted_201_objects(self):
        """Validate that converted 2.0.1 objects pass energyml schema validation."""
        feat = r22.BoundaryFeature(
            citation=citation_22("Horizon"), uuid=uid(), schema_version="2.2",
            is_well_known=False,
        )
        converted, ctx = convert_objects([feat], "22_to_201")
        assert len(converted) > 0

        errors = validate_objects(converted)
        critical = [e for e in errors if "Mandatory" in str(type(e).__name__)]
        assert len(critical) == 0, f"Validation errors: {critical}"

    def test_validate_epc_in_memory(self):
        """Validate an in-memory EPC with converted objects."""
        feat = r201.WellboreFeature(
            citation=citation_201("Well"), uuid=uid(), schema_version="2.0",
        )
        converted, _ = convert_objects([feat], "201_to_22")

        epc = Epc()
        for obj in converted:
            epc.add_object(obj)

        report = validate_output(epc)
        # Should not have critical mandatory field errors
        mandatory_errors = [e for e in report.object_errors if "Mandatory" in str(type(e).__name__)]
        assert len(mandatory_errors) == 0

    def test_validate_output_report_structure(self):
        """Test that validation report has correct structure."""
        feat = r201.GeneticBoundaryFeature(
            citation=citation_201("H1"), uuid=uid(), schema_version="2.0",
            genetic_boundary_kind=r201.GeneticBoundaryKind.HORIZON,
        )
        converted, _ = convert_objects([feat], "201_to_22")
        epc = Epc()
        for obj in converted:
            epc.add_object(obj)

        report = validate_output(epc)
        assert hasattr(report, 'object_errors')
        assert hasattr(report, 'is_valid')
        assert hasattr(report, 'summary')
        summary = report.summary()
        assert isinstance(summary, str)
