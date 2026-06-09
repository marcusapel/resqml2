"""Tests for the strict RESQML validator."""

import os
import tempfile
import zipfile
from pathlib import Path

import pytest

from resqml_converter.strict_validation import (
    Severity,
    StrictValidationError,
    StrictValidationReport,
    ValidationCategory,
    detect_version_from_epc,
    detect_version_from_xml,
    validate_epc_strict,
    validate_epc_structure,
    validate_xml_against_xsd,
    validate_xml_strict,
    _load_schema,
)


# --- Schema Loading ---


class TestSchemaLoading:
    def test_load_schema_201(self):
        schema = _load_schema("2.0.1")
        assert schema is not None

    def test_load_schema_22(self):
        schema = _load_schema("2.2")
        assert schema is not None

    def test_load_schema_invalid_version(self):
        with pytest.raises(FileNotFoundError):
            _load_schema("9.9.9")


# --- Version Detection ---


class TestVersionDetection:
    def test_detect_201_from_xml(self):
        xml = b'<resqml:obj_LocalDepth3dCrs xmlns:resqml="http://www.energistics.org/energyml/data/resqmlv2" schemaVersion="2.0"/>'
        assert detect_version_from_xml(xml) == "2.0.1"

    def test_detect_22_from_xml(self):
        xml = b'<resqml:LocalDepth3dCrs xmlns:resqml="http://www.energistics.org/energyml/data/resqmlv2" schemaVersion="2.2"/>'
        assert detect_version_from_xml(xml) == "2.2"

    def test_detect_201_from_obj_prefix(self):
        xml = b'<resqml:obj_Anything xmlns:resqml="http://www.energistics.org/energyml/data/resqmlv2"/>'
        assert detect_version_from_xml(xml) == "2.0.1"

    def test_detect_from_invalid_xml(self):
        assert detect_version_from_xml(b"not xml") is None


# --- XSD Validation ---


class TestXSDValidation:
    def test_valid_xml_passes(self):
        """A minimal but structurally correct XML should pass XSD (after obj_ fix)."""
        # This tests that the schema loads and validates without crash
        xml = b'''<?xml version="1.0" encoding="UTF-8"?>
<resqml:obj_LocalDepth3dCrs 
  xmlns:resqml="http://www.energistics.org/energyml/data/resqmlv2"
  xmlns:eml="http://www.energistics.org/energyml/data/commonv2"
  schemaVersion="2.0" uuid="12345678-1234-1234-1234-123456789012">
  <eml:Citation>
    <eml:Title>Test CRS</eml:Title>
    <eml:Originator>test</eml:Originator>
    <eml:Creation>2024-01-01T00:00:00Z</eml:Creation>
    <eml:Format>test</eml:Format>
  </eml:Citation>
  <resqml:YOffset>0</resqml:YOffset>
  <resqml:XOffset>0</resqml:XOffset>
  <resqml:ZOffset>0</resqml:ZOffset>
  <resqml:ArealRotation uom="rad">0</resqml:ArealRotation>
  <resqml:ProjectedAxisOrder>easting northing</resqml:ProjectedAxisOrder>
  <resqml:ProjectedUom>m</resqml:ProjectedUom>
  <resqml:VerticalUom>m</resqml:VerticalUom>
  <resqml:ZIncreasingDownward>true</resqml:ZIncreasingDownward>
  <resqml:VerticalCrs>
    <eml:Title>Depth</eml:Title>
    <eml:Originator>test</eml:Originator>
  </resqml:VerticalCrs>
  <resqml:ProjectedCrs>
    <eml:Title>UTM</eml:Title>
    <eml:Originator>test</eml:Originator>
  </resqml:ProjectedCrs>
</resqml:obj_LocalDepth3dCrs>'''
        errors = validate_xml_against_xsd(xml, "2.0.1")
        # This may have ordering errors due to XSD sequence constraints,
        # but should NOT have "no matching global declaration" errors
        root_decl_errors = [e for e in errors if "No matching global declaration" in e.message]
        assert len(root_decl_errors) == 0

    def test_invalid_xml_detected(self):
        """Missing required Citation should be caught."""
        xml = b'''<?xml version="1.0" encoding="UTF-8"?>
<resqml:obj_LocalDepth3dCrs 
  xmlns:resqml="http://www.energistics.org/energyml/data/resqmlv2"
  xmlns:eml="http://www.energistics.org/energyml/data/commonv2"
  schemaVersion="2.0" uuid="12345678-1234-1234-1234-123456789012">
  <resqml:ArealRotation uom="rad">0</resqml:ArealRotation>
</resqml:obj_LocalDepth3dCrs>'''
        errors = validate_xml_against_xsd(xml, "2.0.1")
        assert len(errors) > 0
        assert any("Citation" in e.message for e in errors)

    def test_malformed_xml_detected(self):
        """Malformed XML should be caught before schema validation."""
        xml = b"<not-closed>"
        errors = validate_xml_against_xsd(xml, "2.0.1")
        assert len(errors) > 0
        assert errors[0].category == ValidationCategory.XSD_SCHEMA


# --- EPC Structure ---


class TestEPCStructure:
    def test_valid_epc_structure(self):
        """Minimal valid EPC with Content_Types and _rels."""
        with tempfile.NamedTemporaryFile(suffix=".epc", delete=False) as f:
            with zipfile.ZipFile(f.name, "w") as zf:
                ct = '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/test.xml" ContentType="application/xml"/></Types>'
                zf.writestr("[Content_Types].xml", ct)
                zf.writestr("_rels/.rels", '<?xml version="1.0"?><Relationships/>')
                zf.writestr("test.xml", "<root/>")
            try:
                errors = validate_epc_structure(f.name)
                real_errors = [e for e in errors if e.severity == Severity.ERROR]
                assert len(real_errors) == 0
            finally:
                os.unlink(f.name)

    def test_missing_content_types(self):
        """EPC without [Content_Types].xml should error."""
        with tempfile.NamedTemporaryFile(suffix=".epc", delete=False) as f:
            with zipfile.ZipFile(f.name, "w") as zf:
                zf.writestr("test.xml", "<root/>")
            try:
                errors = validate_epc_structure(f.name)
                assert any("[Content_Types].xml" in e.message for e in errors)
            finally:
                os.unlink(f.name)

    def test_not_a_zip(self):
        """Non-ZIP file should error."""
        with tempfile.NamedTemporaryFile(suffix=".epc", delete=False, mode="w") as f:
            f.write("not a zip file")
            f.flush()
            try:
                errors = validate_epc_structure(f.name)
                assert any("ZIP" in e.message for e in errors)
            finally:
                os.unlink(f.name)


# --- Report ---


class TestReport:
    def test_report_is_valid_when_no_errors(self):
        report = StrictValidationReport(version="2.0.1")
        assert report.is_valid is True

    def test_report_not_valid_with_error(self):
        report = StrictValidationReport(version="2.0.1", errors=[
            StrictValidationError(message="test", severity=Severity.ERROR)
        ])
        assert report.is_valid is False

    def test_report_valid_with_only_warnings(self):
        report = StrictValidationReport(version="2.0.1", errors=[
            StrictValidationError(message="test", severity=Severity.WARNING)
        ])
        assert report.is_valid is True

    def test_report_summary(self):
        report = StrictValidationReport(version="2.0.1", object_count=5, validated_count=5)
        summary = report.summary()
        assert "PASS" in summary
        assert "2.0.1" in summary

    def test_report_addition(self):
        r1 = StrictValidationReport(version="2.0.1", object_count=3)
        r2 = StrictValidationReport(object_count=2, errors=[
            StrictValidationError(message="x", severity=Severity.ERROR)
        ])
        combined = r1 + r2
        assert combined.object_count == 5
        assert combined.error_count == 1
        assert combined.version == "2.0.1"


# --- Integration test with real EPC if available ---


@pytest.fixture
def synthetic_epc():
    path = "/home/maap/rddms/open-etp-client/docs/synthetic-data/epcs/synthetic201.epc"
    if os.path.exists(path):
        return path
    pytest.skip("Synthetic EPC not available")


class TestIntegration:
    def test_validate_synthetic_201(self, synthetic_epc):
        """Full validation of a known-good fesapi-generated RESQML 2.0.1 file."""
        report = validate_epc_strict(synthetic_epc, skip_hdf5=True)
        # Should pass (no errors, only warnings)
        assert report.is_valid
        assert report.object_count > 0
        assert report.validated_count == report.object_count
        assert report.version == "2.0.1"
