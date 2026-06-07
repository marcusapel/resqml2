"""EPC I/O: read/write EPC packages using energyml utilities."""

from pathlib import Path
from typing import List, Optional, Tuple, Any

from energyml.utils.epc import Epc, get_obj_uuid
from energyml.utils.serialization import read_energyml_xml_bytes, serialize_xml
from energyml.utils.epc_utils import (
    gen_energyml_object_path,
    create_external_part_reference,
    get_content_type_from_class,
)
from energyml.utils.introspection import get_class_pkg_version


def read_epc(epc_path: str) -> Epc:
    """Read an EPC file into an Epc object with all energyml objects parsed."""
    epc = Epc.read_file(epc_path)
    return epc


def write_epc(epc: Epc, output_path: str) -> None:
    """Write an Epc object collection to an EPC file."""
    epc.export_file(output_path)


def get_all_objects(epc: Epc) -> List[Any]:
    """Extract all parsed energyml objects from an Epc."""
    return list(epc.energyml_objects.values()) if hasattr(epc, 'energyml_objects') else epc.get_all_objects()


def detect_version(epc: Epc) -> str:
    """Detect whether an EPC contains RESQML 2.0.1 or 2.2 objects.

    Returns '2.0.1' or '2.2' based on the module of the first RESQML object found.
    """
    for obj in get_all_objects(epc):
        module = type(obj).__module__
        if "resqml" in module:
            if "v2_0_1" in module:
                return "2.0.1"
            elif "v2_2" in module:
                return "2.2"
    # Check EML version as fallback
    for obj in get_all_objects(epc):
        module = type(obj).__module__
        if "eml" in module:
            if "v2_0" in module:
                return "2.0.1"
            elif "v2_3" in module:
                return "2.2"
    raise ValueError("Cannot detect RESQML version from EPC contents")


def create_output_epc(objects: List[Any], h5_paths: Optional[List[str]] = None) -> Epc:
    """Create a new Epc from a list of converted objects."""
    epc = Epc()
    for obj in objects:
        epc.add_object(obj)
    return epc
