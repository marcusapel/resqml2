"""OSDU Schema Compliance Validator.

Fetches official OSDU M27 schema definitions from gitlab.opengroup.org
and compares converter output fields against canonical field names.

This is a Python port of the TypeScript validator from rddms/open-etp-client.
"""

import json
import re
import urllib.request
import ssl
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ─── Configuration ────────────────────────────────────────────────────────────

GITLAB_HOST = "gitlab.opengroup.org"
PROJECT_ID = "osdu%2Fsubcommittees%2Fdata-def%2Fwork-products%2Fschema"
SCHEMA_REF = "master"


@dataclass
class SchemaField:
    path: str  # e.g. "FeatureID"
    type: str  # e.g. "string"
    required: bool
    description: str = ""


@dataclass
class ValidationResult:
    kind: str
    converter_file: str
    missing_required: list[str] = field(default_factory=list)
    missing_optional: list[str] = field(default_factory=list)
    extra_fields: list[str] = field(default_factory=list)
    name_discrepancies: list[dict] = field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        return (
            len(self.missing_required) > 0
            or len(self.name_discrepancies) > 0
            or len(self.extra_fields) > 0
        )

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "converter_file": self.converter_file,
            "missing_required": self.missing_required,
            "missing_optional": self.missing_optional,
            "extra_fields": self.extra_fields,
            "name_discrepancies": self.name_discrepancies,
        }


# ─── Schema Fetcher ──────────────────────────────────────────────────────────


def fetch_schema_markdown(
    category: str, type_name: str, version: str, token: Optional[str] = None
) -> str:
    """Fetch schema markdown from OSDU GitLab."""
    file_path = f"E-R/{category}/{type_name}.{version}.md"
    encoded_path = urllib.request.quote(file_path, safe="")
    url = (
        f"https://{GITLAB_HOST}/api/v4/projects/{PROJECT_ID}"
        f"/repository/files/{encoded_path}/raw?ref={SCHEMA_REF}"
    )

    req = urllib.request.Request(url)
    if token:
        req.add_header("PRIVATE-TOKEN", token)

    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        return resp.read().decode("utf-8")


# ─── Markdown Parser ─────────────────────────────────────────────────────────


def parse_schema_fields(markdown: str) -> list[SchemaField]:
    """Parse schema fields from OSDU markdown table."""
    fields: list[SchemaField] = []

    for line in markdown.split("\n"):
        # Match property table rows: |data.FieldName...|
        match = re.match(r"^\|data\.([^\s|<]+)", line)
        if not match:
            continue

        field_path = match.group(1).replace("[]", "")

        # Parse columns: |path|type|required/optional|title|description|...
        cols = [c.strip() for c in line.split("|") if c.strip()]
        field_type = cols[1] if len(cols) > 1 else "unknown"
        required_col = (cols[2] if len(cols) > 2 else "").lower()
        is_required = required_col == "required"
        description = cols[4] if len(cols) > 4 else ""

        # Skip Abstract* fields (handled by base class spread)
        if any(
            field_path.startswith(prefix)
            for prefix in ("AbstractCommon", "AbstractWPC", "AbstractWork")
        ):
            continue

        fields.append(
            SchemaField(
                path=field_path,
                type=field_type,
                required=is_required,
                description=description,
            )
        )

    # Deduplicate nested fields to top-level
    top_level: dict[str, SchemaField] = {}
    for f in fields:
        top_name = f.path.split(".")[0]
        if top_name not in top_level:
            top_level[top_name] = SchemaField(
                path=top_name, type=f.type, required=f.required, description=f.description
            )
        elif f.required and not top_level[top_name].required:
            top_level[top_name].required = True

    return list(top_level.values())


# ─── Converter Field Extractor ────────────────────────────────────────────────

# Fields injected by abstract base class spread operators
ABSTRACT_COMMON_FIELDS = [
    "Name", "Description", "CreationDateTime", "Tags", "SubmitterName",
    "BusinessActivities", "AuthorIDs", "LineageAssertions",
]
ABSTRACT_WPC_GROUP_FIELDS = [
    "Datasets", "DDMSDatasets", "Artefacts", "IsExtendedLoad", "IsDiscoverable",
    "NameAliases",
]
ABSTRACT_WPC_FIELDS = [
    "SpatialPoint", "SpatialArea", "GeoContexts",
]
ABSTRACT_INTERPRETATION_FIELDS = [
    "DomainTypeID", "FeatureID", "FeatureName",
    "MeanPossibleAge", "OlderPossibleAge", "YoungerPossibleAge",
]

IGNORED_NAMES = {
    "ReservoirDMSUrl", "Promise", "SimpleJson", "OSDUContext", "ResqmlClient"
}


def extract_converter_fields(file_path: Path) -> list[str]:
    """Extract field names from a TypeScript converter file."""
    if not file_path.exists():
        return []

    content = file_path.read_text(encoding="utf-8")
    fields: list[str] = []

    # Match fields in `this.data = { ... }` blocks
    data_block_match = re.search(r"this\.data\s*=\s*\{([\s\S]*?)\};", content)
    if not data_block_match:
        return []

    block = data_block_match.group(1)

    # Detect which abstract spreads are used
    if "AbstractCommonResources" in block:
        fields.extend(ABSTRACT_COMMON_FIELDS)
    if "AbstractWPCGroupType" in block:
        fields.extend(ABSTRACT_WPC_GROUP_FIELDS)
    if "AbstractWorkProductComponent" in block:
        fields.extend(ABSTRACT_WPC_FIELDS)
    if "AbstractInterpretation" in block:
        fields.extend(ABSTRACT_INTERPRETATION_FIELDS)

    # Extract field names (skip spread operators and comments)
    field_regex = re.compile(r"^\s+([A-Z][A-Za-z0-9]+)\s*[,:]", re.MULTILINE)
    for m in field_regex.finditer(block):
        name = m.group(1)
        if not name.startswith("Abstract") and name not in IGNORED_NAMES:
            fields.append(name)

    return list(dict.fromkeys(fields))  # deduplicate preserving order


# ─── JSON Manifest Validator ──────────────────────────────────────────────────


def extract_manifest_fields(manifest: dict) -> list[str]:
    """Extract top-level field names from an OSDU JSON manifest's data block."""
    data = manifest.get("data", {})
    return list(data.keys())


def extract_manifest_kind(manifest: dict) -> Optional[str]:
    """Extract kind string from a manifest."""
    return manifest.get("kind")


def parse_kind(kind: str) -> Optional[tuple[str, str, str]]:
    """Parse kind string into (category, type_name, version)."""
    # Format: osdu:wks:category--TypeName:version
    match = re.match(r"osdu:wks:([\w-]+)--([\w]+):([\d.]+)", kind)
    if match:
        return match.group(1), match.group(2), match.group(3)
    return None


# ─── Comparison Logic ─────────────────────────────────────────────────────────


def levenshtein(a: str, b: str) -> int:
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    return dp[m][n]


def similarity(a: str, b: str) -> float:
    max_len = max(len(a), len(b))
    if max_len == 0:
        return 1.0
    return 1 - levenshtein(a.lower(), b.lower()) / max_len


def compare_fields(
    schema_fields: list[SchemaField],
    manifest_fields: list[str],
    kind: str,
    source: str,
) -> ValidationResult:
    """Compare manifest fields against schema fields."""
    result = ValidationResult(kind=kind, converter_file=source)

    schema_names = {f.path for f in schema_fields}
    manifest_set = set(manifest_fields)

    # Check for missing schema fields in manifest
    for sf in schema_fields:
        if sf.path not in manifest_set:
            # Check for similar names (potential misspelling)
            best_match = ""
            best_sim = 0.0
            for mf in manifest_fields:
                if mf in schema_names:
                    continue
                sim = similarity(sf.path, mf)
                if sim > best_sim and sim > 0.6:
                    best_sim = sim
                    best_match = mf

            if best_match and best_sim > 0.8:
                result.name_discrepancies.append({
                    "manifest": best_match,
                    "schema": sf.path,
                    "similarity": round(best_sim, 2),
                })
            elif sf.required:
                result.missing_required.append(sf.path)
            else:
                result.missing_optional.append(sf.path)

    # Check for extra fields not in schema
    for mf in manifest_fields:
        if mf not in schema_names:
            if not any(d["manifest"] == mf for d in result.name_discrepancies):
                result.extra_fields.append(mf)

    return result


# ─── High-level API ───────────────────────────────────────────────────────────


def validate_manifest(
    manifest_path: Path,
    token: Optional[str] = None,
) -> list[ValidationResult]:
    """Validate one or more OSDU JSON manifests against official schemas.

    Args:
        manifest_path: Path to a JSON manifest file (single object or array).
        token: Optional GitLab PAT for gitlab.opengroup.org.

    Returns:
        List of validation results, one per manifest object.
    """
    content = manifest_path.read_text(encoding="utf-8")
    data = json.loads(content)

    # Support both single manifest and array
    if isinstance(data, list):
        manifests = data
    else:
        manifests = [data]

    results: list[ValidationResult] = []

    for manifest in manifests:
        kind = extract_manifest_kind(manifest)
        if not kind:
            results.append(
                ValidationResult(
                    kind="unknown",
                    converter_file=str(manifest_path),
                    missing_required=["(no 'kind' field found in manifest)"],
                )
            )
            continue

        parsed = parse_kind(kind)
        if not parsed:
            results.append(
                ValidationResult(
                    kind=kind,
                    converter_file=str(manifest_path),
                    missing_required=[f"(cannot parse kind: {kind})"],
                )
            )
            continue

        category, type_name, version = parsed

        try:
            markdown = fetch_schema_markdown(category, type_name, version, token)
        except Exception as e:
            results.append(
                ValidationResult(
                    kind=kind,
                    converter_file=str(manifest_path),
                    missing_required=[f"(schema fetch failed: {e})"],
                )
            )
            continue

        schema_fields = parse_schema_fields(markdown)
        manifest_fields = extract_manifest_fields(manifest)

        result = compare_fields(schema_fields, manifest_fields, kind, str(manifest_path))
        results.append(result)

    return results


def validate_converter_file(
    converter_path: Path,
    kind: str,
    token: Optional[str] = None,
) -> Optional[ValidationResult]:
    """Validate a TypeScript converter file against official OSDU schema.

    Args:
        converter_path: Path to a TypeScript converter file.
        kind: OSDU kind string (e.g. osdu:wks:work-product-component--WellLog:1.2.0).
        token: Optional GitLab PAT for gitlab.opengroup.org.

    Returns:
        ValidationResult or None if kind cannot be parsed.
    """
    parsed = parse_kind(kind)
    if not parsed:
        return None

    category, type_name, version = parsed

    markdown = fetch_schema_markdown(category, type_name, version, token)
    schema_fields = parse_schema_fields(markdown)
    converter_fields = extract_converter_fields(converter_path)

    return compare_fields(
        schema_fields, converter_fields, kind, str(converter_path)
    )
