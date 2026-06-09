"""Standalone CLI entry point for strict RESQML validation."""

import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="resqml-validate",
        description="Strict RESQML XSD + structural validator (2.0.1 / 2.2)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  resqml-validate model.epc
  resqml-validate model.epc --version 2.2 --h5 model.h5
  resqml-validate model.epc --json
  resqml-validate model.epc --skip-xsd
  resqml-validate model.epc --errors-only
        """,
    )
    parser.add_argument(
        "input", help="Input EPC file path"
    )
    parser.add_argument(
        "--version", choices=["2.0.1", "2.2"],
        help="RESQML version override (auto-detected if not specified)",
    )
    parser.add_argument(
        "--h5", help="Path to associated HDF5 file (auto-detected if not specified)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--errors-only", action="store_true",
        help="Only show errors, suppress warnings and info",
    )
    parser.add_argument(
        "--skip-xsd", action="store_true",
        help="Skip XSD schema validation",
    )
    parser.add_argument(
        "--skip-energyml", action="store_true",
        help="Skip energyml object validation",
    )
    parser.add_argument(
        "--skip-dor", action="store_true",
        help="Skip DOR integrity checks",
    )
    parser.add_argument(
        "--skip-epc-structure", action="store_true",
        help="Skip EPC structure validation",
    )
    parser.add_argument(
        "--skip-hdf5", action="store_true",
        help="Skip HDF5 reference validation",
    )
    parser.add_argument(
        "--skip-cross-object", action="store_true",
        help="Skip cross-object consistency checks",
    )

    args = parser.parse_args()

    from resqml_converter.strict_validation import (
        validate_epc_strict,
        Severity,
    )

    try:
        report = validate_epc_strict(
            epc_path=args.input,
            version=args.version,
            h5_path=args.h5,
            skip_xsd=args.skip_xsd,
            skip_energyml=args.skip_energyml,
            skip_dor=args.skip_dor,
            skip_epc_structure=args.skip_epc_structure,
            skip_hdf5=args.skip_hdf5,
            skip_cross_object=args.skip_cross_object,
        )

        if args.errors_only:
            report.errors = [e for e in report.errors if e.severity == Severity.ERROR]

        if args.json:
            output = {
                "version": report.version,
                "is_valid": report.is_valid,
                "object_count": report.object_count,
                "validated_count": report.validated_count,
                "error_count": report.error_count,
                "warning_count": report.warning_count,
                "errors": [e.to_dict() for e in report.errors],
            }
            print(json.dumps(output, indent=2))
        else:
            print(report.summary())

        sys.exit(0 if report.is_valid else 1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
