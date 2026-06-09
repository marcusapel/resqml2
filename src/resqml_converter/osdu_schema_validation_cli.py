"""CLI entry point for OSDU schema compliance validation."""

import argparse
import json
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        prog="osdu-schema-validate",
        description="Validate OSDU JSON manifests against official OSDU M27 schema definitions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  osdu-schema-validate manifest.json
  osdu-schema-validate manifests/ --token $OSDU_SCHEMA_TOKEN
  osdu-schema-validate manifest.json --json
  osdu-schema-validate manifest.json --errors-only
  osdu-schema-validate --converter src/lib/jsonTypes/WellLog.ts --kind "osdu:wks:work-product-component--WellLog:1.2.0"
        """,
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Input JSON manifest file or directory containing manifests",
    )
    parser.add_argument(
        "--converter",
        help="Path to a TypeScript converter file to validate (alternative mode)",
    )
    parser.add_argument(
        "--kind",
        help="OSDU kind string (required with --converter)",
    )
    parser.add_argument(
        "--token",
        help="GitLab PAT for gitlab.opengroup.org (or set OSDU_SCHEMA_TOKEN env var)",
    )
    parser.add_argument(
        "--json", action="store_true", dest="output_json",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--errors-only", action="store_true",
        help="Only show kinds with missing required fields or name discrepancies",
    )

    args = parser.parse_args()
    token = args.token or os.environ.get("OSDU_SCHEMA_TOKEN")

    from resqml_converter.osdu_schema_validation import (
        validate_manifest,
        validate_converter_file,
        ValidationResult,
    )

    results: list[ValidationResult] = []

    try:
        if args.converter:
            # Converter file validation mode
            if not args.kind:
                parser.error("--kind is required when using --converter")
            converter_path = Path(args.converter)
            if not converter_path.exists():
                print(f"Error: converter file not found: {args.converter}", file=sys.stderr)
                sys.exit(2)
            result = validate_converter_file(converter_path, args.kind, token)
            if result:
                results.append(result)
            else:
                print(f"Error: cannot parse kind: {args.kind}", file=sys.stderr)
                sys.exit(2)
        elif args.input:
            # Manifest validation mode
            input_path = Path(args.input)
            if input_path.is_dir():
                manifest_files = sorted(input_path.glob("*.json"))
                if not manifest_files:
                    print(f"No JSON files found in {args.input}", file=sys.stderr)
                    sys.exit(2)
                for mf in manifest_files:
                    sys.stdout.write(f"Validating {mf.name}...")
                    sys.stdout.flush()
                    file_results = validate_manifest(mf, token)
                    results.extend(file_results)
                    has_issues = any(r.has_issues for r in file_results)
                    print(" ISSUES FOUND" if has_issues else " OK")
            elif input_path.is_file():
                results = validate_manifest(input_path, token)
            else:
                print(f"Error: input not found: {args.input}", file=sys.stderr)
                sys.exit(2)
        else:
            parser.error("either input path or --converter is required")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    # Filter if errors-only
    if args.errors_only:
        results = [
            r for r in results
            if r.missing_required or r.name_discrepancies
        ]

    # Output
    if args.output_json:
        output = {
            "total": len(results),
            "issues": sum(1 for r in results if r.has_issues),
            "results": [r.to_dict() for r in results],
        }
        print(json.dumps(output, indent=2))
    else:
        _print_report(results)

    has_errors = any(r.missing_required or r.name_discrepancies for r in results)
    sys.exit(1 if has_errors else 0)


def _print_report(results: list) -> None:
    """Print a human-readable compliance report."""
    print()
    print("=" * 72)
    print("OSDU SCHEMA COMPLIANCE REPORT")
    print("=" * 72)

    total_issues = 0

    for r in results:
        if not r.has_issues:
            continue

        print(f"\n+-- {r.kind}")
        print(f"|   Source: {r.converter_file}")

        if r.name_discrepancies:
            print("|")
            print("|   WARNING - FIELD NAME DISCREPANCIES:")
            for d in r.name_discrepancies:
                sim_pct = int(d["similarity"] * 100)
                manifest_key = d.get("manifest", d.get("converter", "?"))
                print(
                    f'|     Manifest: "{manifest_key}" -> Schema: "{d["schema"]}" ({sim_pct}% similar)'
                )
                total_issues += 1

        if r.missing_required:
            print("|")
            print("|   ERROR - MISSING REQUIRED FIELDS:")
            for f in r.missing_required:
                print(f"|     - {f}")
                total_issues += 1

        if r.extra_fields:
            print("|")
            print("|   INFO - EXTRA FIELDS (not in official schema):")
            for f in r.extra_fields:
                print(f"|     + {f}")

        if r.missing_optional:
            print("|")
            print(f"|   Missing optional: {', '.join(r.missing_optional)}")

        print("+--")

    issues_count = sum(1 for r in results if r.missing_required or r.name_discrepancies)
    print()
    print("-" * 72)
    print(f"Summary: {total_issues} issue(s) across {issues_count} source(s)")
    print("-" * 72)


if __name__ == "__main__":
    main()
