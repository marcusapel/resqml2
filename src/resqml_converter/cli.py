"""CLI for RESQML version conversion and strict validation."""

import argparse
import json
import sys

from resqml_converter.converter import convert_epc


def main():
    root_parser = argparse.ArgumentParser(
        description="RESQML converter and strict validator (2.0.1 / 2.2)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = root_parser.add_subparsers(dest="command")

    # --- convert subcommand ---
    convert_parser = subparsers.add_parser(
        "convert",
        help="Convert RESQML files between version 2.0.1 and 2.2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  resqml-convert convert --input model.epc --output model_22.epc --target-version 2.2
  resqml-convert convert --input model_22.epc --output model_201.epc --target-version 2.0.1
        """,
    )
    _add_convert_args(convert_parser)

    # --- validate subcommand ---
    validate_parser = subparsers.add_parser(
        "validate",
        help="Strict XSD + structural validation of RESQML EPC files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  resqml-convert validate --input model.epc
  resqml-convert validate --input model.epc --version 2.2 --h5 model.h5
  resqml-convert validate --input model.epc --json
  resqml-convert validate --input model.epc --skip-xsd
        """,
    )
    _add_validate_args(validate_parser)

    # Backward-compat: if no subcommand, treat as convert
    args = root_parser.parse_args()

    if args.command == "validate":
        _run_validate(args)
    elif args.command == "convert":
        _run_convert(args)
    else:
        # Legacy mode: direct convert arguments
        parser = argparse.ArgumentParser(
            description="Convert RESQML files between version 2.0.1 and 2.2",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  resqml-convert --input model.epc --output model_22.epc --target-version 2.2
  resqml-convert --input model_22.epc --output model_201.epc --target-version 2.0.1
  resqml-convert --input model.epc --output model_22.epc --target-version 2.2 --validate
        """,
        )
        _add_convert_args(parser)
        args = parser.parse_args()
        _run_convert(args)


def _add_convert_args(parser):
def _add_convert_args(parser):
    parser.add_argument(
        "--input", "-i", required=True, help="Input EPC file path"
    )
    parser.add_argument(
        "--output", "-o", required=True, help="Output EPC file path"
    )
    parser.add_argument(
        "--target-version", "-t", required=True,
        choices=["2.0.1", "2.2", "201", "22"],
        help="Target RESQML version",
    )
    parser.add_argument(
        "--validate", "-v", action="store_true",
        help="Validate output using energyml validation",
    )
    parser.add_argument(
        "--no-copy-h5", action="store_true",
        help="Do not copy HDF5 files to output directory",
    )


def _add_validate_args(parser):
    parser.add_argument(
        "--input", "-i", required=True, help="Input EPC file path"
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
        "--skip-fesapi", action="store_true",
        help="Skip fesapi compatibility checks (xsi:type, element ordering)",
    )
    parser.add_argument(
        "--skip-rddms", action="store_true",
        help="Skip RDDMS compatibility checks (namespace, .rels integrity)",
    )
    parser.add_argument(
        "--strict", action="store_true", default=True,
        help="Enable all strict checks (default)",
    )


def _run_convert(args):
    try:
        result = convert_epc(
            input_path=args.input,
            output_path=args.output,
            target_version=args.target_version,
            validate=args.validate,
            copy_h5=not args.no_copy_h5,
        )
        print(result.summary())
        sys.exit(0 if result.success else 1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)


def _run_validate(args):
    from resqml_converter.strict_validation import validate_epc_strict

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
            skip_fesapi=args.skip_fesapi,
            skip_rddms=args.skip_rddms,
        )

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
