"""Feature type mappings between RESQML 2.0.1 and 2.2.

Key changes:
- 2.0.1 GeneticBoundaryFeature (horizon) + TectonicBoundaryFeature (fault) -> 2.2 BoundaryFeature
- 2.0.1 OrganizationFeature -> 2.2 Model
- 2.0.1 GeologicUnitFeature -> 2.2 RockVolumeFeature
- 2.0.1 SeismicLatticeFeature struct changed
- WellboreFeature is mostly the same
"""

from __future__ import annotations

from typing import Any

from energyml.eml.v2_0 import commonv2 as eml20
from energyml.eml.v2_3 import commonv2 as eml23
from energyml.resqml.v2_0_1 import resqmlv2 as r201
from energyml.resqml.v2_2 import resqmlv2 as r22
from energyml.utils.introspection import get_obj_uuid

from resqml_converter.mappings.base import ConversionContext, registry
from resqml_converter.mappings.common import (
    convert_citation_201_to_23,
    convert_citation_23_to_201,
    SCHEMA_VERSION_22,
    SCHEMA_VERSION_201,
)


# ─── 2.0.1 -> 2.2 Feature Mappers ────────────────────────────────────────────

@registry.register_201_to_22(r"GeneticBoundaryFeature")
def convert_genetic_boundary_to_22(obj: r201.GeneticBoundaryFeature, ctx: ConversionContext) -> Any:
    """GeneticBoundaryFeature (horizon/geobody boundary) -> BoundaryFeature in 2.2."""
    return r22.BoundaryFeature(
        citation=convert_citation_201_to_23(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_22,
        is_well_known=False,
    )


@registry.register_201_to_22(r"TectonicBoundaryFeature")
def convert_tectonic_boundary_to_22(obj: r201.TectonicBoundaryFeature, ctx: ConversionContext) -> Any:
    """TectonicBoundaryFeature (fault/fracture) -> BoundaryFeature in 2.2."""
    return r22.BoundaryFeature(
        citation=convert_citation_201_to_23(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_22,
        is_well_known=False,
    )


@registry.register_201_to_22(r"OrganizationFeature")
def convert_organization_feature_to_22(obj: r201.OrganizationFeature, ctx: ConversionContext) -> Any:
    """OrganizationFeature -> Model in 2.2."""
    return r22.Model(
        citation=convert_citation_201_to_23(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_22,
        is_well_known=False,
    )


@registry.register_201_to_22(r"GeologicUnitFeature")
def convert_geologic_unit_to_22(obj: r201.GeologicUnitFeature, ctx: ConversionContext) -> Any:
    """GeologicUnitFeature -> RockVolumeFeature in 2.2."""
    return r22.RockVolumeFeature(
        citation=convert_citation_201_to_23(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_22,
        is_well_known=False,
    )


@registry.register_201_to_22(r"WellboreFeature")
def convert_wellbore_feature_to_22(obj: r201.WellboreFeature, ctx: ConversionContext) -> Any:
    """WellboreFeature -> WellboreFeature (similar structure)."""
    return r22.WellboreFeature(
        citation=convert_citation_201_to_23(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_22,
        is_well_known=False,
    )


@registry.register_201_to_22(r"SeismicLatticeFeature")
def convert_seismic_lattice_to_22(obj: r201.SeismicLatticeFeature, ctx: ConversionContext) -> Any:
    """SeismicLatticeFeature: struct changes between versions.

    2.0.1 uses flat fields (crossline_count, inline_count, etc.)
    2.2 uses IntegerLatticeArray for inline_labels/crossline_labels.
    """
    crossline_count = getattr(obj, 'crossline_count', 100) or 100
    inline_count = getattr(obj, 'inline_count', 200) or 200
    first_crossline = getattr(obj, 'first_crossline_index', 0) or 0
    first_inline = getattr(obj, 'first_inline_index', 0) or 0
    crossline_inc = getattr(obj, 'crossline_index_increment', 1) or 1
    inline_inc = getattr(obj, 'inline_index_increment', 1) or 1

    return r22.SeismicLatticeFeature(
        citation=convert_citation_201_to_23(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_22,
        is_well_known=False,
        crossline_labels=r22.IntegerLatticeArray(
            start_value=first_crossline,
            offset=[eml23.IntegerConstantArray(value=crossline_inc, count=crossline_count - 1)],
        ),
        inline_labels=r22.IntegerLatticeArray(
            start_value=first_inline,
            offset=[eml23.IntegerConstantArray(value=inline_inc, count=inline_count - 1)],
        ),
    )


# ─── 2.2 -> 2.0.1 Feature Mappers ────────────────────────────────────────────

@registry.register_22_to_201(r"BoundaryFeature")
def convert_boundary_feature_to_201(obj: r22.BoundaryFeature, ctx: ConversionContext) -> Any:
    """BoundaryFeature -> GeneticBoundaryFeature or TectonicBoundaryFeature.

    Heuristic: check if any FaultInterpretation references this feature.
    Default to GeneticBoundaryFeature (horizon).
    """
    uuid = get_obj_uuid(obj)

    # Check context: is this feature referenced by a FaultInterpretation?
    is_fault = _is_referenced_as_fault(uuid, ctx)

    if is_fault:
        return r201.TectonicBoundaryFeature(
            citation=convert_citation_23_to_201(obj.citation),
            uuid=uuid,
            schema_version=SCHEMA_VERSION_201,
            tectonic_boundary_kind=r201.TectonicBoundaryKind.FAULT,
        )
    else:
        return r201.GeneticBoundaryFeature(
            citation=convert_citation_23_to_201(obj.citation),
            uuid=uuid,
            schema_version=SCHEMA_VERSION_201,
            genetic_boundary_kind=r201.GeneticBoundaryKind.HORIZON,
        )


@registry.register_22_to_201(r"^Model$")
def convert_model_to_201(obj: r22.Model, ctx: ConversionContext) -> Any:
    """Model -> OrganizationFeature."""
    return r201.OrganizationFeature(
        citation=convert_citation_23_to_201(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_201,
        organization_kind=r201.OrganizationKind.EARTH_MODEL,
    )


@registry.register_22_to_201(r"RockVolumeFeature")
def convert_rock_volume_to_201(obj: r22.RockVolumeFeature, ctx: ConversionContext) -> Any:
    """RockVolumeFeature -> GeologicUnitFeature."""
    return r201.GeologicUnitFeature(
        citation=convert_citation_23_to_201(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_201,
    )


@registry.register_22_to_201(r"WellboreFeature")
def convert_wellbore_feature_to_201(obj: r22.WellboreFeature, ctx: ConversionContext) -> Any:
    """WellboreFeature -> WellboreFeature."""
    return r201.WellboreFeature(
        citation=convert_citation_23_to_201(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_201,
    )


@registry.register_22_to_201(r"SeismicLatticeFeature")
def convert_seismic_lattice_to_201(obj: r22.SeismicLatticeFeature, ctx: ConversionContext) -> Any:
    """SeismicLatticeFeature: extract flat fields from IntegerLatticeArrays."""
    # Extract from crossline_labels
    first_crossline = 0
    crossline_count = 100
    crossline_inc = 1
    if obj.crossline_labels:
        first_crossline = obj.crossline_labels.start_value or 0
        if obj.crossline_labels.offset:
            off = obj.crossline_labels.offset[0]
            crossline_count = (off.count or 99) + 1
            crossline_inc = off.value or 1

    first_inline = 0
    inline_count = 200
    inline_inc = 1
    if obj.inline_labels:
        first_inline = obj.inline_labels.start_value or 0
        if obj.inline_labels.offset:
            off = obj.inline_labels.offset[0]
            inline_count = (off.count or 199) + 1
            inline_inc = off.value or 1

    return r201.SeismicLatticeFeature(
        citation=convert_citation_23_to_201(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_201,
        crossline_count=crossline_count,
        crossline_index_increment=crossline_inc,
        first_crossline_index=first_crossline,
        first_inline_index=first_inline,
        inline_count=inline_count,
        inline_index_increment=inline_inc,
    )


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _is_referenced_as_fault(feature_uuid: str, ctx: ConversionContext) -> bool:
    """Check if a BoundaryFeature is referenced by a FaultInterpretation."""
    for obj in ctx.source_objects.values():
        cls_name = type(obj).__name__
        if "FaultInterpretation" in cls_name:
            interp_feat = getattr(obj, 'interpreted_feature', None)
            if interp_feat and getattr(interp_feat, 'uuid', None) == feature_uuid:
                return True
    return False
