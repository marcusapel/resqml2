"""CLI for RESQML version conversion."""

import argparse
import sys

from resqml_converter.converter import convert_epc


def main():
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

    args = parser.parse_args()

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


if __name__ == "__main__":
    main()
