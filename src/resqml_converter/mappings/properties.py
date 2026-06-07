"""Property type mappings between RESQML 2.0.1 and 2.2.

Key changes:
- supporting_representation DOR format
- property_kind: LocalPropertyKind/StandardPropertyKind (2.0.1) -> DOR to PropertyKind (2.2)
- PropertyKind in 2.0.1 is a RESQML object; in 2.2 it's an EML 2.3 object
- indexable_element enum: IndexableElements (2.0.1) -> IndexableElement (2.2)
- patch_of_values (2.0.1) -> values_for_patch (2.2)
- count field (2.0.1) -> value_count_per_indexable_element list (2.2)
- uom handling differences
"""

from __future__ import annotations

from typing import Any, List, Optional

from energyml.eml.v2_0 import commonv2 as eml20
from energyml.eml.v2_3 import commonv2 as eml23
from energyml.resqml.v2_0_1 import resqmlv2 as r201
from energyml.resqml.v2_2 import resqmlv2 as r22
from energyml.utils.introspection import get_obj_uuid

from resqml_converter.mappings.base import ConversionContext, registry
from resqml_converter.mappings.common import (
    convert_citation_201_to_23,
    convert_citation_23_to_201,
    convert_dor_201_to_23,
    convert_dor_23_to_201,
    convert_float_hdf5_array_to_ext,
    convert_int_hdf5_array_to_ext,
    convert_float_ext_array_to_hdf5,
    convert_int_ext_array_to_hdf5,
    SCHEMA_VERSION_22,
    SCHEMA_VERSION_201,
    SCHEMA_VERSION_EML23,
    SCHEMA_VERSION_EML20,
)


# ─── 2.0.1 -> 2.2 Property Mappers ───────────────────────────────────────────

@registry.register_201_to_22(r"ContinuousProperty")
def convert_continuous_prop_to_22(obj: r201.ContinuousProperty, ctx: ConversionContext) -> Any:
    """ContinuousProperty: patch_of_values -> values_for_patch, property_kind -> DOR."""
    # Convert values
    values_for_patch = []
    for pov in getattr(obj, 'patch_of_values', []) or []:
        vals = getattr(pov, 'values', None)
        ext_arr = convert_float_hdf5_array_to_ext(vals)
        if ext_arr:
            values_for_patch.append(ext_arr)

    # Convert property kind reference
    prop_kind_dor = _convert_property_kind_201_to_22_dor(obj, ctx)

    # UOM
    uom = "Euc"
    if obj.uom:
        uom = str(obj.uom.value) if hasattr(obj.uom, 'value') else str(obj.uom)

    # Indexable element
    indexable = None
    if obj.indexable_element:
        try:
            indexable = r22.IndexableElement(obj.indexable_element.value)
        except (ValueError, AttributeError):
            indexable = r22.IndexableElement.CELLS

    count = getattr(obj, 'count', 1) or 1

    return r22.ContinuousProperty(
        citation=convert_citation_201_to_23(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_22,
        indexable_element=indexable,
        value_count_per_indexable_element=[count],
        supporting_representation=convert_dor_201_to_23(obj.supporting_representation, ctx),
        property_kind=prop_kind_dor,
        uom=uom,
        values_for_patch=values_for_patch or None,
    )


@registry.register_201_to_22(r"DiscreteProperty")
def convert_discrete_prop_to_22(obj: Any, ctx: ConversionContext) -> Any:
    """DiscreteProperty: similar structure change as ContinuousProperty."""
    values_for_patch = []
    for pov in getattr(obj, 'patch_of_values', []) or []:
        vals = getattr(pov, 'values', None)
        ext_arr = convert_int_hdf5_array_to_ext(vals)
        if ext_arr:
            values_for_patch.append(ext_arr)

    prop_kind_dor = _convert_property_kind_201_to_22_dor(obj, ctx)

    indexable = None
    if getattr(obj, 'indexable_element', None):
        try:
            indexable = r22.IndexableElement(obj.indexable_element.value)
        except (ValueError, AttributeError):
            indexable = r22.IndexableElement.CELLS

    count = getattr(obj, 'count', 1) or 1

    return r22.DiscreteProperty(
        citation=convert_citation_201_to_23(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_22,
        indexable_element=indexable,
        value_count_per_indexable_element=[count],
        supporting_representation=convert_dor_201_to_23(obj.supporting_representation, ctx),
        property_kind=prop_kind_dor,
        values_for_patch=values_for_patch or None,
    )


@registry.register_201_to_22(r"CategoricalProperty")
def convert_categorical_prop_to_22(obj: Any, ctx: ConversionContext) -> Any:
    """CategoricalProperty (2.0.1) -> DiscreteProperty (2.2)."""
    values_for_patch = []
    for pov in getattr(obj, 'patch_of_values', []) or []:
        vals = getattr(pov, 'values', None)
        ext_arr = convert_int_hdf5_array_to_ext(vals)
        if ext_arr:
            values_for_patch.append(ext_arr)

    prop_kind_dor = _convert_property_kind_201_to_22_dor(obj, ctx)

    indexable = None
    if getattr(obj, 'indexable_element', None):
        try:
            indexable = r22.IndexableElement(obj.indexable_element.value)
        except (ValueError, AttributeError):
            indexable = r22.IndexableElement.CELLS

    count = getattr(obj, 'count', 1) or 1

    return r22.DiscreteProperty(
        citation=convert_citation_201_to_23(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_22,
        indexable_element=indexable,
        value_count_per_indexable_element=[count],
        supporting_representation=convert_dor_201_to_23(
            getattr(obj, 'supporting_representation', None), ctx
        ),
        property_kind=prop_kind_dor,
        values_for_patch=values_for_patch or None,
    )


@registry.register_201_to_22(r"^PropertyKind$")
def convert_property_kind_to_22(obj: r201.PropertyKind, ctx: ConversionContext) -> Any:
    """PropertyKind (RESQML 2.0.1) -> PropertyKind (EML 2.3).

    2.0.1: resqml object with naming_system, parent_property_kind, representative_uom
    2.2: eml23 object with quantity_class
    """
    quantity_class = "dimensionless"
    # Try to map from representative_uom or parent
    if obj.representative_uom:
        uom_val = str(obj.representative_uom.value) if hasattr(obj.representative_uom, 'value') else str(obj.representative_uom)
        quantity_class = _uom_to_quantity_class(uom_val)

    return eml23.PropertyKind(
        citation=convert_citation_201_to_23(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_EML23,
        is_abstract=getattr(obj, 'is_abstract', False),
        quantity_class=quantity_class,
    )


# ─── 2.2 -> 2.0.1 Property Mappers ───────────────────────────────────────────

@registry.register_22_to_201(r"ContinuousProperty")
def convert_continuous_prop_to_201(obj: r22.ContinuousProperty, ctx: ConversionContext) -> Any:
    """ContinuousProperty: values_for_patch -> patch_of_values."""
    hdf_ref = _get_hdf_proxy_ref_for_props(ctx)

    patch_of_values = []
    for i, ext_arr in enumerate(getattr(obj, 'values_for_patch', []) or []):
        hdf_arr = convert_float_ext_array_to_hdf5(ext_arr, hdf_ref)
        if hdf_arr:
            patch_of_values.append(r201.PatchOfValues(
                representation_patch_index=i,
                values=hdf_arr,
            ))

    # Convert property kind DOR back
    prop_kind = _convert_property_kind_22_to_201_ref(obj, ctx)

    # Indexable element
    indexable = None
    if obj.indexable_element:
        try:
            indexable = r201.IndexableElements(obj.indexable_element.value)
        except (ValueError, AttributeError):
            indexable = r201.IndexableElements.CELLS

    # UOM
    uom = r201.ResqmlUom.EUC
    if obj.uom:
        uom = _parse_resqml_uom(str(obj.uom))

    count = 1
    vcpie = getattr(obj, 'value_count_per_indexable_element', None)
    if vcpie and len(vcpie) > 0:
        count = vcpie[0]

    return r201.ContinuousProperty(
        citation=convert_citation_23_to_201(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_201,
        count=count,
        indexable_element=indexable,
        supporting_representation=convert_dor_23_to_201(obj.supporting_representation, ctx),
        property_kind=prop_kind,
        uom=uom,
        patch_of_values=patch_of_values or None,
    )


@registry.register_22_to_201(r"DiscreteProperty")
def convert_discrete_prop_to_201(obj: r22.DiscreteProperty, ctx: ConversionContext) -> Any:
    """DiscreteProperty (2.2) -> DiscreteProperty (2.0.1)."""
    hdf_ref = _get_hdf_proxy_ref_for_props(ctx)

    patch_of_values = []
    for i, ext_arr in enumerate(getattr(obj, 'values_for_patch', []) or []):
        hdf_arr = convert_int_ext_array_to_hdf5(ext_arr, hdf_ref)
        if hdf_arr:
            patch_of_values.append(r201.PatchOfValues(
                representation_patch_index=i,
                values=hdf_arr,
            ))

    prop_kind = _convert_property_kind_22_to_201_ref(obj, ctx)

    indexable = None
    if obj.indexable_element:
        try:
            indexable = r201.IndexableElements(obj.indexable_element.value)
        except (ValueError, AttributeError):
            indexable = r201.IndexableElements.CELLS

    count = 1
    vcpie = getattr(obj, 'value_count_per_indexable_element', None)
    if vcpie and len(vcpie) > 0:
        count = vcpie[0]

    return r201.DiscreteProperty(
        citation=convert_citation_23_to_201(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_201,
        count=count,
        indexable_element=indexable,
        supporting_representation=convert_dor_23_to_201(obj.supporting_representation, ctx),
        property_kind=prop_kind,
        patch_of_values=patch_of_values or None,
    )


@registry.register_22_to_201(r"^PropertyKind$")
def convert_property_kind_to_201(obj: eml23.PropertyKind, ctx: ConversionContext) -> Any:
    """PropertyKind (EML 2.3) -> PropertyKind (RESQML 2.0.1)."""
    quantity_class = getattr(obj, 'quantity_class', 'dimensionless') or 'dimensionless'
    representative_uom = _quantity_class_to_uom(quantity_class)

    # Determine parent property kind
    parent = r201.StandardPropertyKind(kind=r201.ResqmlPropertyKind.CONTINUOUS)
    if "porosity" in (obj.citation.title or "").lower():
        parent = r201.StandardPropertyKind(kind=r201.ResqmlPropertyKind.POROSITY)
    elif "permeability" in (obj.citation.title or "").lower():
        parent = r201.StandardPropertyKind(kind=r201.ResqmlPropertyKind.PERMEABILITY_ROCK)

    return r201.PropertyKind(
        citation=convert_citation_23_to_201(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_201,
        naming_system="Energistics",
        is_abstract=getattr(obj, 'is_abstract', False),
        representative_uom=representative_uom,
        parent_property_kind=parent,
    )


# ─── Property Kind Reference Helpers ─────────────────────────────────────────

def _convert_property_kind_201_to_22_dor(obj: Any, ctx: ConversionContext) -> Optional[eml23.DataObjectReference]:
    """Convert 2.0.1 property_kind (LocalPropertyKind or StandardPropertyKind) to a DOR."""
    pk = getattr(obj, 'property_kind', None)
    if pk is None:
        return None

    # LocalPropertyKind has a local_property_kind DOR
    if hasattr(pk, 'local_property_kind'):
        return convert_dor_201_to_23(pk.local_property_kind, ctx)

    # StandardPropertyKind has a kind enum
    if hasattr(pk, 'kind'):
        # Create a synthetic DOR pointing to a well-known property kind
        kind_name = str(pk.kind.value) if hasattr(pk.kind, 'value') else str(pk.kind)
        return eml23.DataObjectReference(
            uuid="00000000-0000-0000-0000-000000000000",
            title=kind_name,
            qualified_type="eml23.PropertyKind",
        )

    return None


def _convert_property_kind_22_to_201_ref(obj: Any, ctx: ConversionContext) -> Any:
    """Convert 2.2 property_kind DOR back to 2.0.1 LocalPropertyKind or StandardPropertyKind."""
    pk_dor = getattr(obj, 'property_kind', None)
    if pk_dor is None:
        return r201.StandardPropertyKind(kind=r201.ResqmlPropertyKind.CONTINUOUS)

    # Check if it's a well-known standard kind
    uuid = getattr(pk_dor, 'uuid', '')
    title = getattr(pk_dor, 'title', '') or ''

    # If it references a real PropertyKind object in context
    if uuid and uuid != "00000000-0000-0000-0000-000000000000":
        return r201.LocalPropertyKind(
            local_property_kind=convert_dor_23_to_201(pk_dor, ctx)
        )

    # Map well-known kinds
    kind = _title_to_resqml_property_kind(title)
    return r201.StandardPropertyKind(kind=kind)


def _title_to_resqml_property_kind(title: str) -> r201.ResqmlPropertyKind:
    """Map a property kind title to the RESQML 2.0.1 enum."""
    title_lower = title.lower().replace(" ", "_")
    try:
        return r201.ResqmlPropertyKind(title_lower)
    except (ValueError, KeyError):
        # Try common mappings
        mappings = {
            "porosity": r201.ResqmlPropertyKind.POROSITY,
            "permeability": r201.ResqmlPropertyKind.PERMEABILITY_ROCK,
            "depth": r201.ResqmlPropertyKind.DEPTH,
            "pressure": r201.ResqmlPropertyKind.PRESSURE,
            "saturation": r201.ResqmlPropertyKind.SATURATION,
            "volume": r201.ResqmlPropertyKind.VOLUME,
            "thickness": r201.ResqmlPropertyKind.THICKNESS,
        }
        for key, val in mappings.items():
            if key in title_lower:
                return val
        return r201.ResqmlPropertyKind.CONTINUOUS


def _get_hdf_proxy_ref_for_props(ctx: ConversionContext) -> Optional[eml20.DataObjectReference]:
    """Get HDF proxy ref from context."""
    for obj in ctx.converted_objects.values():
        if type(obj).__name__ == "EpcExternalPartReference":
            return eml20.DataObjectReference(
                content_type="application/x-eml+xml;version=2.0;type=obj_EpcExternalPartReference",
                title="HDF5 Proxy",
                uuid=get_obj_uuid(obj),
            )
    return None


def _uom_to_quantity_class(uom: str) -> str:
    """Map a UOM to a quantity class for EML 2.3 PropertyKind."""
    uom_map = {
        "Euc": "dimensionless",
        "m": "length",
        "ft": "length",
        "m3": "volume",
        "mD": "permeability",
        "Pa": "pressure",
        "bar": "pressure",
    }
    return uom_map.get(uom, "dimensionless")


def _quantity_class_to_uom(qc: str) -> r201.ResqmlUom:
    """Map a quantity class back to a representative UOM."""
    qc_map = {
        "dimensionless": r201.ResqmlUom.EUC,
        "length": r201.ResqmlUom.M,
        "volume": r201.ResqmlUom.M3,
        "pressure": r201.ResqmlUom.PA,
    }
    return qc_map.get(qc, r201.ResqmlUom.EUC)


def _parse_resqml_uom(uom_str: str) -> r201.ResqmlUom:
    """Parse UOM string to RESQML 2.0.1 enum."""
    try:
        return r201.ResqmlUom(uom_str)
    except (ValueError, KeyError):
        uom_map = {"Euc": r201.ResqmlUom.EUC, "m": r201.ResqmlUom.M, "ft": r201.ResqmlUom.FT}
        return uom_map.get(uom_str, r201.ResqmlUom.EUC)
