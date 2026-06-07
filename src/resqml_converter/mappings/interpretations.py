"""Interpretation type mappings between RESQML 2.0.1 and 2.2.

Key changes:
- interpreted_feature DOR format change (content_type vs qualified_type)
- has_occured_during (2.0.1) -> has_occurred_during (2.2) spelling fix
- FaultInterpretation: is_listric field removed in 2.2
- StructuralOrganizationInterpretation: ordering_criteria -> ascending_ordering_criteria
- Various new optional fields in 2.2 (existence, osduintegration, etc.)
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
    SCHEMA_VERSION_22,
    SCHEMA_VERSION_201,
)


# ─── 2.0.1 -> 2.2 Interpretation Mappers ─────────────────────────────────────

@registry.register_201_to_22(r"HorizonInterpretation")
def convert_horizon_interp_to_22(obj: r201.HorizonInterpretation, ctx: ConversionContext) -> Any:
    """HorizonInterpretation 2.0.1 -> 2.2."""
    return r22.HorizonInterpretation(
        citation=convert_citation_201_to_23(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_22,
        domain=_convert_domain_201_to_22(obj.domain),
        interpreted_feature=convert_dor_201_to_23(obj.interpreted_feature, ctx),
        sequence_stratigraphy_surface=_convert_seq_strat_surface_201_to_22(obj.sequence_stratigraphy_surface),
    )


@registry.register_201_to_22(r"FaultInterpretation")
def convert_fault_interp_to_22(obj: r201.FaultInterpretation, ctx: ConversionContext) -> Any:
    """FaultInterpretation 2.0.1 -> 2.2. Note: is_listric removed in 2.2."""
    result = r22.FaultInterpretation(
        citation=convert_citation_201_to_23(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_22,
        domain=_convert_domain_201_to_22(obj.domain),
        interpreted_feature=convert_dor_201_to_23(obj.interpreted_feature, ctx),
    )
    # Preserve is_listric as extra metadata if True
    if getattr(obj, 'is_listric', False):
        ctx.warn(f"FaultInterpretation {get_obj_uuid(obj)}: is_listric=True not representable in 2.2")
    return result


@registry.register_201_to_22(r"GeobodyInterpretation")
def convert_geobody_interp_to_22(obj: Any, ctx: ConversionContext) -> Any:
    return r22.GeobodyInterpretation(
        citation=convert_citation_201_to_23(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_22,
        domain=_convert_domain_201_to_22(obj.domain),
        interpreted_feature=convert_dor_201_to_23(obj.interpreted_feature, ctx),
    )


@registry.register_201_to_22(r"GeobodyBoundaryInterpretation")
def convert_geobody_boundary_interp_to_22(obj: Any, ctx: ConversionContext) -> Any:
    return r22.GeobodyBoundaryInterpretation(
        citation=convert_citation_201_to_23(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_22,
        domain=_convert_domain_201_to_22(obj.domain),
        interpreted_feature=convert_dor_201_to_23(obj.interpreted_feature, ctx),
    )


@registry.register_201_to_22(r"WellboreInterpretation")
def convert_wellbore_interp_to_22(obj: r201.WellboreInterpretation, ctx: ConversionContext) -> Any:
    return r22.WellboreInterpretation(
        citation=convert_citation_201_to_23(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_22,
        domain=_convert_domain_201_to_22(obj.domain),
        interpreted_feature=convert_dor_201_to_23(obj.interpreted_feature, ctx),
        is_drilled=getattr(obj, 'is_drilled', True),
    )


@registry.register_201_to_22(r"StratigraphicUnitInterpretation")
def convert_strat_unit_interp_to_22(obj: Any, ctx: ConversionContext) -> Any:
    return r22.StratigraphicUnitInterpretation(
        citation=convert_citation_201_to_23(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_22,
        domain=_convert_domain_201_to_22(obj.domain),
        interpreted_feature=convert_dor_201_to_23(obj.interpreted_feature, ctx),
    )


@registry.register_201_to_22(r"StructuralOrganizationInterpretation")
def convert_struct_org_interp_to_22(obj: r201.StructuralOrganizationInterpretation, ctx: ConversionContext) -> Any:
    """StructuralOrganizationInterpretation: ordering_criteria -> ascending_ordering_criteria.

    Also restructures faults/horizons into ordered_boundary_feature_interpretation.
    """
    # Build ordered boundary feature list from faults + horizons
    ordered_boundaries = []
    rank = 0

    for fault_dor in getattr(obj, 'faults', []) or []:
        ordered_boundaries.append(
            r22.BoundaryFeatureInterpretationPlusItsRank(
                boundary_feature_interpretation=convert_dor_201_to_23(fault_dor, ctx),
                stratigraphic_rank=rank,
            )
        )
        rank += 1

    for h_idx in getattr(obj, 'horizons', []) or []:
        h_dor = h_idx.horizon if hasattr(h_idx, 'horizon') else h_idx
        ordered_boundaries.append(
            r22.BoundaryFeatureInterpretationPlusItsRank(
                boundary_feature_interpretation=convert_dor_201_to_23(h_dor, ctx),
                stratigraphic_rank=rank,
            )
        )
        rank += 1

    return r22.StructuralOrganizationInterpretation(
        citation=convert_citation_201_to_23(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_22,
        domain=_convert_domain_201_to_22(obj.domain),
        interpreted_feature=convert_dor_201_to_23(obj.interpreted_feature, ctx),
        ascending_ordering_criteria=_convert_ordering_criteria_201_to_22(
            getattr(obj, 'ordering_criteria', None)
        ),
        ordered_boundary_feature_interpretation=ordered_boundaries or None,
    )


@registry.register_201_to_22(r"EarthModelInterpretation")
def convert_earth_model_interp_to_22(obj: r201.EarthModelInterpretation, ctx: ConversionContext) -> Any:
    return r22.EarthModelInterpretation(
        citation=convert_citation_201_to_23(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_22,
        domain=_convert_domain_201_to_22(obj.domain),
        interpreted_feature=convert_dor_201_to_23(obj.interpreted_feature, ctx),
        structure=convert_dor_201_to_23(getattr(obj, 'structure', None), ctx),
        stratigraphic_column=convert_dor_201_to_23(getattr(obj, 'stratigraphic_column', None), ctx),
    )


@registry.register_201_to_22(r"StratigraphicColumnRankInterpretation")
def convert_strat_col_rank_to_22(obj: Any, ctx: ConversionContext) -> Any:
    strat_units = []
    for su in getattr(obj, 'stratigraphic_units', []) or []:
        strat_units.append(convert_dor_201_to_23(su, ctx))

    return r22.StratigraphicColumnRankInterpretation(
        citation=convert_citation_201_to_23(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_22,
        domain=_convert_domain_201_to_22(obj.domain),
        interpreted_feature=convert_dor_201_to_23(obj.interpreted_feature, ctx),
        ascending_ordering_criteria=_convert_ordering_criteria_201_to_22(
            getattr(obj, 'ordering_criteria', None) or getattr(obj, 'ascending_ordering_criteria', None)
        ),
        rank_in_stratigraphic_column=getattr(obj, 'rank_in_stratigraphic_column', 0),
        stratigraphic_units=strat_units or None,
    )


# ─── 2.2 -> 2.0.1 Interpretation Mappers ─────────────────────────────────────

@registry.register_22_to_201(r"HorizonInterpretation")
def convert_horizon_interp_to_201(obj: r22.HorizonInterpretation, ctx: ConversionContext) -> Any:
    return r201.HorizonInterpretation(
        citation=convert_citation_23_to_201(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_201,
        domain=_convert_domain_22_to_201(obj.domain),
        interpreted_feature=convert_dor_23_to_201(obj.interpreted_feature, ctx),
    )


@registry.register_22_to_201(r"FaultInterpretation")
def convert_fault_interp_to_201(obj: r22.FaultInterpretation, ctx: ConversionContext) -> Any:
    return r201.FaultInterpretation(
        citation=convert_citation_23_to_201(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_201,
        domain=_convert_domain_22_to_201(obj.domain),
        interpreted_feature=convert_dor_23_to_201(obj.interpreted_feature, ctx),
        is_listric=False,
    )


@registry.register_22_to_201(r"GeobodyInterpretation")
def convert_geobody_interp_to_201(obj: Any, ctx: ConversionContext) -> Any:
    return r201.GeobodyInterpretation(
        citation=convert_citation_23_to_201(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_201,
        domain=_convert_domain_22_to_201(obj.domain),
        interpreted_feature=convert_dor_23_to_201(obj.interpreted_feature, ctx),
    )


@registry.register_22_to_201(r"GeobodyBoundaryInterpretation")
def convert_geobody_boundary_interp_to_201(obj: Any, ctx: ConversionContext) -> Any:
    return r201.GeobodyBoundaryInterpretation(
        citation=convert_citation_23_to_201(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_201,
        domain=_convert_domain_22_to_201(obj.domain),
        interpreted_feature=convert_dor_23_to_201(obj.interpreted_feature, ctx),
    )


@registry.register_22_to_201(r"WellboreInterpretation")
def convert_wellbore_interp_to_201(obj: r22.WellboreInterpretation, ctx: ConversionContext) -> Any:
    return r201.WellboreInterpretation(
        citation=convert_citation_23_to_201(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_201,
        domain=_convert_domain_22_to_201(obj.domain),
        interpreted_feature=convert_dor_23_to_201(obj.interpreted_feature, ctx),
        is_drilled=getattr(obj, 'is_drilled', True),
    )


@registry.register_22_to_201(r"StratigraphicUnitInterpretation")
def convert_strat_unit_interp_to_201(obj: Any, ctx: ConversionContext) -> Any:
    return r201.StratigraphicUnitInterpretation(
        citation=convert_citation_23_to_201(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_201,
        domain=_convert_domain_22_to_201(obj.domain),
        interpreted_feature=convert_dor_23_to_201(obj.interpreted_feature, ctx),
    )


@registry.register_22_to_201(r"StructuralOrganizationInterpretation")
def convert_struct_org_interp_to_201(obj: r22.StructuralOrganizationInterpretation, ctx: ConversionContext) -> Any:
    """Reverse: split ordered_boundary_feature_interpretation back into faults/horizons."""
    faults = []
    horizons = []

    for bfi in getattr(obj, 'ordered_boundary_feature_interpretation', []) or []:
        dor_23 = bfi.boundary_feature_interpretation
        dor_201 = convert_dor_23_to_201(dor_23, ctx)
        # Determine if fault or horizon from the referenced interpretation
        if dor_23 and _is_fault_dor(dor_23, ctx):
            faults.append(dor_201)
        else:
            idx = len(horizons)
            horizons.append(r201.HorizonInterpretationIndex(index=idx, horizon=dor_201))

    return r201.StructuralOrganizationInterpretation(
        citation=convert_citation_23_to_201(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_201,
        domain=_convert_domain_22_to_201(obj.domain),
        interpreted_feature=convert_dor_23_to_201(obj.interpreted_feature, ctx),
        ordering_criteria=_convert_ordering_criteria_22_to_201(
            getattr(obj, 'ascending_ordering_criteria', None)
        ),
        faults=faults or None,
        horizons=horizons or None,
    )


@registry.register_22_to_201(r"EarthModelInterpretation")
def convert_earth_model_interp_to_201(obj: r22.EarthModelInterpretation, ctx: ConversionContext) -> Any:
    return r201.EarthModelInterpretation(
        citation=convert_citation_23_to_201(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_201,
        domain=_convert_domain_22_to_201(obj.domain),
        interpreted_feature=convert_dor_23_to_201(obj.interpreted_feature, ctx),
        structure=convert_dor_23_to_201(getattr(obj, 'structure', None), ctx),
        stratigraphic_column=convert_dor_23_to_201(getattr(obj, 'stratigraphic_column', None), ctx),
    )


@registry.register_22_to_201(r"StratigraphicColumnRankInterpretation")
def convert_strat_col_rank_to_201(obj: Any, ctx: ConversionContext) -> Any:
    strat_units = []
    for su in getattr(obj, 'stratigraphic_units', []) or []:
        strat_units.append(convert_dor_23_to_201(su, ctx))

    return r201.StratigraphicColumnRankInterpretation(
        citation=convert_citation_23_to_201(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_201,
        domain=_convert_domain_22_to_201(obj.domain),
        interpreted_feature=convert_dor_23_to_201(obj.interpreted_feature, ctx),
        ordering_criteria=_convert_ordering_criteria_22_to_201(
            getattr(obj, 'ascending_ordering_criteria', None)
        ),
        rank_in_stratigraphic_column=getattr(obj, 'rank_in_stratigraphic_column', 0),
        stratigraphic_units=strat_units or None,
    )


@registry.register_22_to_201(r"RockFluidOrganizationInterpretation")
def convert_rock_fluid_org_to_201(obj: Any, ctx: ConversionContext) -> Any:
    """RockFluidOrganizationInterpretation exists in both versions."""
    return r201.RockFluidOrganizationInterpretation(
        citation=convert_citation_23_to_201(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_201,
        domain=_convert_domain_22_to_201(obj.domain),
        interpreted_feature=convert_dor_23_to_201(obj.interpreted_feature, ctx),
    )


@registry.register_201_to_22(r"RockFluidOrganizationInterpretation")
def convert_rock_fluid_org_to_22(obj: Any, ctx: ConversionContext) -> Any:
    return r22.RockFluidOrganizationInterpretation(
        citation=convert_citation_201_to_23(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_22,
        domain=_convert_domain_201_to_22(obj.domain),
        interpreted_feature=convert_dor_201_to_23(obj.interpreted_feature, ctx),
    )


@registry.register_22_to_201(r"RockFluidUnitInterpretation")
def convert_rock_fluid_unit_to_201(obj: Any, ctx: ConversionContext) -> Any:
    return r201.RockFluidUnitInterpretation(
        citation=convert_citation_23_to_201(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_201,
        domain=_convert_domain_22_to_201(obj.domain),
        interpreted_feature=convert_dor_23_to_201(obj.interpreted_feature, ctx),
    )


@registry.register_201_to_22(r"RockFluidUnitInterpretation")
def convert_rock_fluid_unit_to_22(obj: Any, ctx: ConversionContext) -> Any:
    return r22.RockFluidUnitInterpretation(
        citation=convert_citation_201_to_23(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_22,
        domain=_convert_domain_201_to_22(obj.domain),
        interpreted_feature=convert_dor_201_to_23(obj.interpreted_feature, ctx),
    )


@registry.register_22_to_201(r"FluidBoundaryInterpretation")
def convert_fluid_boundary_to_201(obj: Any, ctx: ConversionContext) -> Any:
    """FluidBoundaryInterpretation -> may not exist as separate type in 2.0.1; use HorizonInterpretation."""
    ctx.warn(f"FluidBoundaryInterpretation {get_obj_uuid(obj)} mapped to HorizonInterpretation in 2.0.1")
    return r201.HorizonInterpretation(
        citation=convert_citation_23_to_201(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_201,
        domain=_convert_domain_22_to_201(obj.domain),
        interpreted_feature=convert_dor_23_to_201(obj.interpreted_feature, ctx),
    )


@registry.register_201_to_22(r"FluidBoundaryInterpretation")
def convert_fluid_boundary_to_22(obj: Any, ctx: ConversionContext) -> Any:
    return r22.FluidBoundaryInterpretation(
        citation=convert_citation_201_to_23(obj.citation),
        uuid=get_obj_uuid(obj),
        schema_version=SCHEMA_VERSION_22,
        domain=_convert_domain_201_to_22(obj.domain),
        interpreted_feature=convert_dor_201_to_23(obj.interpreted_feature, ctx),
    )


# ─── Domain Conversion Helpers ────────────────────────────────────────────────

def _convert_domain_201_to_22(domain: Any) -> Optional[Any]:
    """Convert RESQML 2.0.1 Domain enum to 2.2."""
    if domain is None:
        return None
    try:
        return r22.Domain(domain.value)
    except (ValueError, AttributeError):
        return r22.Domain.DEPTH


def _convert_domain_22_to_201(domain: Any) -> Optional[Any]:
    """Convert RESQML 2.2 Domain enum to 2.0.1."""
    if domain is None:
        return None
    try:
        return r201.Domain(domain.value)
    except (ValueError, AttributeError):
        return r201.Domain.DEPTH


def _convert_ordering_criteria_201_to_22(oc: Any) -> Optional[Any]:
    if oc is None:
        return r22.OrderingCriteria.AGE
    try:
        return r22.OrderingCriteria(oc.value)
    except (ValueError, AttributeError):
        return r22.OrderingCriteria.AGE


def _convert_ordering_criteria_22_to_201(oc: Any) -> Optional[Any]:
    if oc is None:
        return r201.OrderingCriteria.AGE
    try:
        return r201.OrderingCriteria(oc.value)
    except (ValueError, AttributeError):
        return r201.OrderingCriteria.AGE


def _convert_seq_strat_surface_201_to_22(sss: Any) -> Optional[Any]:
    """Convert SequenceStratigraphySurface enum to the 2.2 kind."""
    if sss is None:
        return None
    try:
        return r22.SequenceStratigraphySurfaceKind(sss.value)
    except (ValueError, AttributeError):
        return None


def _is_fault_dor(dor: Any, ctx: ConversionContext) -> bool:
    """Check if a DOR points to a FaultInterpretation by looking at source objects."""
    uuid = getattr(dor, 'uuid', None)
    if uuid:
        src = ctx.get_source(uuid)
        if src and "Fault" in type(src).__name__:
            return True
        # Check qualified type
        qt = getattr(dor, 'qualified_type', '') or ''
        if "Fault" in qt:
            return True
    return False
