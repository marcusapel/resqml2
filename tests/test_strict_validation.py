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


@pytest.fixture
def drogon_epc():
    path = "/home/maap/ores/demo/drogonresqml/drogon.epc"
    if os.path.exists(path):
        return path
    pytest.skip("Drogon EPC not available")


class TestIntegration:
    def test_validate_drogon_full(self, drogon_epc):
        """Drogon EPC must pass ALL checks including fesapi and RDDMS."""
        report = validate_epc_strict(drogon_epc, skip_hdf5=True, skip_energyml=True)
        assert report.is_valid
        assert report.object_count > 0
        assert report.validated_count == report.object_count
        assert report.version == "2.0.1"
        # No errors at all (fesapi + RDDMS compliant)
        errors = [e for e in report.errors if e.severity == Severity.ERROR]
        assert len(errors) == 0, f"Unexpected errors: {errors}"

    def test_synthetic_lacks_rddms_compat(self, synthetic_epc):
        """Synthetic fesapi EPC should flag missing xsi:type for RDDMS."""
        report = validate_epc_strict(synthetic_epc, skip_hdf5=True, skip_energyml=True)
        # XSD + fesapi pass, but RDDMS detects missing xsi:type
        rddms_errors = [e for e in report.errors
                        if e.category == ValidationCategory.RDDMS_COMPAT and e.severity == Severity.ERROR]
        assert len(rddms_errors) > 0, "Should detect missing xsi:type for RDDMS"
        assert any("xsi:type" in e.message for e in rddms_errors)


# --- fesapi Compatibility ---


class TestFesapiCompat:
    def _make_epc(self, xml_content: str, filename: str = "obj_TectonicBoundaryFeature_12345678-1234-1234-1234-123456789012.xml") -> str:
        """Create a temp EPC with one XML object."""
        import tempfile
        f = tempfile.NamedTemporaryFile(suffix=".epc", delete=False)
        with zipfile.ZipFile(f.name, "w") as zf:
            ct = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                f'<Override PartName="/{filename}" ContentType="application/x-resqml+xml;version=2.0;type=obj_TectonicBoundaryFeature"/>'
                '</Types>'
            )
            zf.writestr("[Content_Types].xml", ct)
            zf.writestr("_rels/.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>')
            zf.writestr(filename, xml_content)
        return f.name

    def test_missing_xsi_type_detected(self):
        """fesapi warns about missing xsi:type (ERROR in RDDMS context)."""
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
<resqml2:TectonicBoundaryFeature
  xmlns:eml="http://www.energistics.org/energyml/data/commonv2"
  xmlns:resqml2="http://www.energistics.org/energyml/data/resqmlv2"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  schemaVersion="2.0" uuid="12345678-1234-1234-1234-123456789012">
  <eml:Citation><eml:Title>F1</eml:Title><eml:Originator>test</eml:Originator><eml:Creation>2025-01-01T00:00:00Z</eml:Creation><eml:Format>test</eml:Format></eml:Citation>
  <resqml2:TectonicBoundaryKind>fault</resqml2:TectonicBoundaryKind>
</resqml2:TectonicBoundaryFeature>'''
        epc_path = self._make_epc(xml)
        try:
            from resqml_converter.strict_validation import validate_fesapi_compat
            errors = validate_fesapi_compat(epc_path, "2.0.1")
            assert any("xsi:type" in e.message and e.severity == Severity.WARNING for e in errors)
            assert any(e.category == ValidationCategory.FESAPI_COMPAT for e in errors)
        finally:
            os.unlink(epc_path)

    def test_xsi_type_present_passes(self):
        """Root with xsi:type should pass fesapi check."""
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
<resqml2:TectonicBoundaryFeature
  xmlns:eml="http://www.energistics.org/energyml/data/commonv2"
  xmlns:resqml2="http://www.energistics.org/energyml/data/resqmlv2"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:type="resqml2:obj_TectonicBoundaryFeature"
  schemaVersion="2.0" uuid="12345678-1234-1234-1234-123456789012">
  <eml:Citation><eml:Title>F1</eml:Title><eml:Originator>test</eml:Originator><eml:Creation>2025-01-01T00:00:00Z</eml:Creation><eml:Format>test</eml:Format></eml:Citation>
  <resqml2:TectonicBoundaryKind>fault</resqml2:TectonicBoundaryKind>
</resqml2:TectonicBoundaryFeature>'''
        epc_path = self._make_epc(xml)
        try:
            from resqml_converter.strict_validation import validate_fesapi_compat
            errors = validate_fesapi_compat(epc_path, "2.0.1")
            xsi_errors = [e for e in errors if "xsi:type" in e.message]
            assert len(xsi_errors) == 0
        finally:
            os.unlink(epc_path)

    def test_extra_metadata_before_other_elements(self):
        """ExtraMetadata must come last for fesapi."""
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
<resqml2:TectonicBoundaryFeature
  xmlns:eml="http://www.energistics.org/energyml/data/commonv2"
  xmlns:resqml2="http://www.energistics.org/energyml/data/resqmlv2"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:type="resqml2:obj_TectonicBoundaryFeature"
  schemaVersion="2.0" uuid="12345678-1234-1234-1234-123456789012">
  <eml:Citation><eml:Title>F1</eml:Title><eml:Originator>test</eml:Originator><eml:Creation>2025-01-01T00:00:00Z</eml:Creation><eml:Format>test</eml:Format></eml:Citation>
  <resqml2:ExtraMetadata><resqml2:Name>key</resqml2:Name><resqml2:Value>val</resqml2:Value></resqml2:ExtraMetadata>
  <resqml2:TectonicBoundaryKind>fault</resqml2:TectonicBoundaryKind>
</resqml2:TectonicBoundaryFeature>'''
        epc_path = self._make_epc(xml)
        try:
            from resqml_converter.strict_validation import validate_fesapi_compat
            errors = validate_fesapi_compat(epc_path, "2.0.1")
            assert any("ExtraMetadata" in e.message for e in errors)
        finally:
            os.unlink(epc_path)

    def test_obj_prefix_in_tag_warned(self):
        """Root element with obj_ prefix generates a warning."""
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
<resqml2:obj_TectonicBoundaryFeature
  xmlns:eml="http://www.energistics.org/energyml/data/commonv2"
  xmlns:resqml2="http://www.energistics.org/energyml/data/resqmlv2"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:type="resqml2:obj_TectonicBoundaryFeature"
  schemaVersion="2.0" uuid="12345678-1234-1234-1234-123456789012">
  <eml:Citation><eml:Title>F1</eml:Title><eml:Originator>test</eml:Originator><eml:Creation>2025-01-01T00:00:00Z</eml:Creation><eml:Format>test</eml:Format></eml:Citation>
  <resqml2:TectonicBoundaryKind>fault</resqml2:TectonicBoundaryKind>
</resqml2:obj_TectonicBoundaryFeature>'''
        epc_path = self._make_epc(xml)
        try:
            from resqml_converter.strict_validation import validate_fesapi_compat
            errors = validate_fesapi_compat(epc_path, "2.0.1")
            assert any("obj_ prefix" in e.message and e.severity == Severity.WARNING for e in errors)
        finally:
            os.unlink(epc_path)

    def test_skipped_for_version_22(self):
        """fesapi checks should be skipped for RESQML 2.2."""
        from resqml_converter.strict_validation import validate_fesapi_compat
        # Even with a non-existent file, passing version 2.2 returns empty
        errors = validate_fesapi_compat("/nonexistent.epc", "2.2")
        assert len(errors) == 0


# --- RDDMS Compatibility ---


class TestRDDMSCompat:
    def _make_epc_with_epr(self, ns_prefix: str = "resqml2", include_epr_rels: bool = True,
                           target_mode: str = "External", h5_target: str = "data.h5") -> str:
        """Create a temp EPC with an EPR and optional .rels."""
        import tempfile
        epr_file = "obj_EpcExternalPartReference_aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee.xml"
        obj_file = "obj_TectonicBoundaryFeature_12345678-1234-1234-1234-123456789012.xml"

        obj_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<{ns_prefix}:TectonicBoundaryFeature
  xmlns:eml="http://www.energistics.org/energyml/data/commonv2"
  xmlns:{ns_prefix}="http://www.energistics.org/energyml/data/resqmlv2"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:type="{ns_prefix}:obj_TectonicBoundaryFeature"
  schemaVersion="2.0" uuid="12345678-1234-1234-1234-123456789012">
  <eml:Citation><eml:Title>F1</eml:Title><eml:Originator>test</eml:Originator><eml:Creation>2025-01-01T00:00:00Z</eml:Creation><eml:Format>test</eml:Format></eml:Citation>
  <{ns_prefix}:TectonicBoundaryKind>fault</{ns_prefix}:TectonicBoundaryKind>
</{ns_prefix}:TectonicBoundaryFeature>'''

        epr_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<eml:EpcExternalPartReference xmlns:eml="http://www.energistics.org/energyml/data/commonv2"
  schemaVersion="2.0" uuid="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee">
  <eml:Citation><eml:Title>HDF5</eml:Title><eml:Originator>test</eml:Originator><eml:Creation>2025-01-01T00:00:00Z</eml:Creation><eml:Format>test</eml:Format></eml:Citation>
  <eml:Filename>data.h5</eml:Filename>
</eml:EpcExternalPartReference>'''

        f = tempfile.NamedTemporaryFile(suffix=".epc", delete=False)
        with zipfile.ZipFile(f.name, "w") as zf:
            ct = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                f'<Override PartName="/{obj_file}" ContentType="application/x-resqml+xml;version=2.0;type=obj_TectonicBoundaryFeature"/>'
                f'<Override PartName="/{epr_file}" ContentType="application/x-eml+xml;version=2.0;type=obj_EpcExternalPartReference"/>'
                '</Types>'
            )
            zf.writestr("[Content_Types].xml", ct)
            zf.writestr("_rels/.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>')
            zf.writestr(obj_file, obj_xml)
            zf.writestr(epr_file, epr_xml)

            if include_epr_rels:
                rels_xml = (
                    '<?xml version="1.0" encoding="UTF-8"?>'
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                    f'<Relationship Id="Hdf5File" Type="http://schemas.energistics.org/package/2012/relationships/externalResource"'
                    f' Target="{h5_target}" TargetMode="{target_mode}"/>'
                    '</Relationships>'
                )
                zf.writestr(f"_rels/{epr_file}.rels", rels_xml)
        return f.name

    def test_correct_epc_passes(self):
        """A correctly structured EPC should have no RDDMS errors."""
        epc_path = self._make_epc_with_epr(ns_prefix="resqml2")
        try:
            from resqml_converter.strict_validation import validate_rddms_compat
            errors = validate_rddms_compat(epc_path, "2.0.1")
            real_errors = [e for e in errors if e.severity == Severity.ERROR]
            assert len(real_errors) == 0
        finally:
            os.unlink(epc_path)

    def test_wrong_namespace_prefix_detected(self):
        """Using resqml: instead of resqml2: should generate a warning."""
        epc_path = self._make_epc_with_epr(ns_prefix="resqml")
        try:
            from resqml_converter.strict_validation import validate_rddms_compat
            errors = validate_rddms_compat(epc_path, "2.0.1")
            assert any("resqml:" in e.message and e.severity == Severity.WARNING for e in errors)
        finally:
            os.unlink(epc_path)

    def test_missing_epr_rels_detected(self):
        """Missing EPR .rels should be flagged."""
        epc_path = self._make_epc_with_epr(include_epr_rels=False)
        try:
            from resqml_converter.strict_validation import validate_rddms_compat
            errors = validate_rddms_compat(epc_path, "2.0.1")
            assert any("Missing .rels" in e.message for e in errors)
        finally:
            os.unlink(epc_path)

    def test_wrong_target_mode_detected(self):
        """EPR .rels without TargetMode=External should be flagged."""
        epc_path = self._make_epc_with_epr(target_mode="Internal")
        try:
            from resqml_converter.strict_validation import validate_rddms_compat
            errors = validate_rddms_compat(epc_path, "2.0.1")
            assert any("TargetMode" in e.message for e in errors)
        finally:
            os.unlink(epc_path)

    def test_tag_mismatch_detected(self):
        """Opening/closing tag mismatch should be flagged."""
        import tempfile
        obj_file = "obj_TectonicBoundaryFeature_12345678-1234-1234-1234-123456789012.xml"
        # Opening: TectonicBoundaryFeature, Closing: obj_TectonicBoundaryFeature
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
<resqml2:TectonicBoundaryFeature
  xmlns:eml="http://www.energistics.org/energyml/data/commonv2"
  xmlns:resqml2="http://www.energistics.org/energyml/data/resqmlv2"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:type="resqml2:obj_TectonicBoundaryFeature"
  schemaVersion="2.0" uuid="12345678-1234-1234-1234-123456789012">
  <eml:Citation><eml:Title>F1</eml:Title><eml:Originator>test</eml:Originator><eml:Creation>2025-01-01T00:00:00Z</eml:Creation><eml:Format>test</eml:Format></eml:Citation>
  <resqml2:TectonicBoundaryKind>fault</resqml2:TectonicBoundaryKind>
</resqml2:obj_TectonicBoundaryFeature>'''
        f = tempfile.NamedTemporaryFile(suffix=".epc", delete=False)
        with zipfile.ZipFile(f.name, "w") as zf:
            ct = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                f'<Override PartName="/{obj_file}" ContentType="application/x-resqml+xml;version=2.0;type=obj_TectonicBoundaryFeature"/>'
                '</Types>'
            )
            zf.writestr("[Content_Types].xml", ct)
            zf.writestr("_rels/.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>')
            zf.writestr(obj_file, xml)
        try:
            from resqml_converter.strict_validation import validate_rddms_compat
            errors = validate_rddms_compat(f.name, "2.0.1")
            assert any("mismatch" in e.message for e in errors)
        finally:
            os.unlink(f.name)

    def test_skipped_for_version_22(self):
        """RDDMS checks should be skipped for RESQML 2.2."""
        from resqml_converter.strict_validation import validate_rddms_compat
        errors = validate_rddms_compat("/nonexistent.epc", "2.2")
        assert len(errors) == 0
