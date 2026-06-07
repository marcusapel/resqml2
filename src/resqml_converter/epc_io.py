"""EPC I/O: read/write EPC packages using energyml utilities."""

import re
import zipfile
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
    """Write an Epc object collection to an EPC file then fix OPC compliance."""
    epc.export_file(output_path)
    _fix_opc_content_types(output_path)


def _fix_opc_content_types(epc_path: str) -> None:
    """Post-process EPC to fix [Content_Types].xml for OPC/ETP compatibility.

    Fixes:
      - ns6: namespace prefix → bare xmlns
      - Missing leading / on PartName
      - obj_ prefix on filenames (2.2 uses bare type names)
      - version=2.0 for objects serialized from 2.0.1 classes but targeting 2.2
    """
    import tempfile, shutil

    with zipfile.ZipFile(epc_path, 'r') as zin:
        if '[Content_Types].xml' not in zin.namelist():
            return
        ct_xml = zin.read('[Content_Types].xml').decode('utf-8')

        # Fix namespace prefix: ns6:Types -> Types with default xmlns
        ct_xml = re.sub(
            r'<ns6:Types[^>]*>',
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
            ct_xml,
        )
        ct_xml = ct_xml.replace('</ns6:Types>', '</Types>')
        ct_xml = ct_xml.replace('<ns6:Default', '<Default')
        ct_xml = ct_xml.replace('<ns6:Override', '<Override')
        ct_xml = ct_xml.replace('</ns6:Default>', '</Default>')
        ct_xml = ct_xml.replace('</ns6:Override>', '</Override>')

        # Fix PartName: ensure leading /
        ct_xml = re.sub(
            r'PartName="(?!/)',
            'PartName="/',
            ct_xml,
        )

        # Fix obj_ prefix: version=2.0;type=obj_X → version=2.2;type=X
        # and PartName with obj_ prefix → without
        ct_xml = re.sub(
            r'version=2\.0;type=obj_(\w+)',
            r'version=2.2;type=\1',
            ct_xml,
        )
        ct_xml = re.sub(
            r'PartName="/obj_(\w+)',
            r'PartName="/\1',
            ct_xml,
        )

        # Determine which files need renaming (obj_ prefix removal)
        renames = {}
        for item in zin.namelist():
            if item.startswith('obj_'):
                new_name = item[4:]  # strip obj_ prefix
                renames[item] = new_name
            elif item.startswith('_rels/obj_'):
                new_name = '_rels/' + item[10:]
                renames[item] = new_name

        # Write fixed zip
        tmp = epc_path + '.tmp'
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.namelist():
                data = zin.read(item) if item != '[Content_Types].xml' else ct_xml.encode('utf-8')
                out_name = renames.get(item, item)

                # For .rels files referencing obj_ targets, fix those too
                if out_name.endswith('.rels'):
                    data_str = data.decode('utf-8')
                    data_str = re.sub(r'Target="obj_(\w+)', r'Target="\1', data_str)
                    data = data_str.encode('utf-8')

                # For XML files with obj_ root element prefix, fix the root tag
                elif out_name.endswith('.xml') and item in renames:
                    data_str = data.decode('utf-8')
                    # Fix root element: <resqml:obj_TypeName → <resqml:TypeName
                    data_str = re.sub(
                        r'<(\w+):obj_(\w+)',
                        r'<\1:\2',
                        data_str,
                    )
                    data_str = re.sub(
                        r'</(\w+):obj_(\w+)',
                        r'</\1:\2',
                        data_str,
                    )
                    # Also fix xsi:type if present
                    data_str = re.sub(
                        r'xsi:type="(\w+):obj_(\w+)"',
                        r'xsi:type="\1:\2"',
                        data_str,
                    )
                    data = data_str.encode('utf-8')

                zout.writestr(out_name, data)

    shutil.move(tmp, epc_path)


def get_all_objects(epc: Epc) -> List[Any]:
    """Extract all parsed energyml objects from an Epc."""
    return list(epc.energyml_objects)


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
