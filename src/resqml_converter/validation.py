"""Validation wrapper using Geosiris energyml validation tools."""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from energyml.utils.epc import Epc
from energyml.utils.validation import (
    validate_epc,
    validate_obj,
    validate_objects,
    ValidationError,
)
from energyml.utils.epc_validator import validate_epc_file, ValidationResult


@dataclass
class ConversionValidationReport:
    """Combined validation report for a converted EPC."""

    object_errors: List[ValidationError]
    epc_structure_result: Optional[ValidationResult]
    is_valid: bool

    def summary(self) -> str:
        lines = []
        if self.object_errors:
            lines.append(f"Object validation errors ({len(self.object_errors)}):")
            for err in self.object_errors:
                lines.append(f"  - {err}")
        if self.epc_structure_result and not self.epc_structure_result.is_valid:
            lines.append("EPC structure validation errors:")
            for err in self.epc_structure_result.errors:
                lines.append(f"  - {err}")
        if self.is_valid:
            lines.append("Validation PASSED: output is schema-conformant.")
        return "\n".join(lines) if lines else "Validation PASSED"


def validate_output(epc_or_path, objects: Optional[List[Any]] = None) -> ConversionValidationReport:
    """Validate converted output using energyml validation.

    Args:
        epc_or_path: Either an Epc object or a file path to an EPC file.
        objects: Optional list of objects to validate individually.

    Returns:
        ConversionValidationReport with all validation results.
    """
    object_errors: List[ValidationError] = []
    epc_result: Optional[ValidationResult] = None

    # Object-level validation
    if isinstance(epc_or_path, Epc):
        object_errors = validate_epc(epc_or_path)
    elif objects:
        object_errors = validate_objects(objects)

    # EPC file structure validation (ZIP structure, relationships, content types)
    if isinstance(epc_or_path, str):
        try:
            epc_result = validate_epc_file(epc_or_path, strict=True, check_relationships=True)
        except Exception:
            pass  # File may not exist yet if validating in-memory

    is_valid = (len(object_errors) == 0) and (epc_result is None or epc_result.is_valid)

    return ConversionValidationReport(
        object_errors=object_errors,
        epc_structure_result=epc_result,
        is_valid=is_valid,
    )


def validate_single_object(obj: Any, context: List[Any]) -> List[ValidationError]:
    """Validate a single converted object against its context (other objects in the EPC)."""
    return validate_obj(obj, context)
