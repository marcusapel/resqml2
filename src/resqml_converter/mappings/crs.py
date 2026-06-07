"""CRS conversion between RESQML 2.0.1 and 2.2.

RDDMS-compatible approach: LocalDepth3dCrs stays as a single flat object
in RESQML 2.2 (same structure, different schema version). The EML 2.3
compound CRS decomposition is NOT used because RDDMS expects the flat
format with qualified_type 'resqml22.LocalDepth3dCrs'.
"""

from __future__ import annotations

from typing import Any, Optional

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
    SCHEMA_VERSION_EML23,
    SCHEMA_VERSION_201,
    SCHEMA_VERSION_EML20,
)


# ─── 2.0.1 -> 2.2 CRS ───────────────────────────────────────────────────────
# RDDMS keeps LocalDepth3dCrs as-is in RESQML 2.2 (flat structure).
# We preserve the object unchanged, only updating schema_version.

@registry.register_201_to_22(r"LocalDepth3[dD][Cc]rs")
def convert_local_depth_3d_crs_to_22(obj: r201.LocalDepth3DCrs, ctx: ConversionContext) -> Any:
    """Keep LocalDepth3dCrs as-is for 2.2 (RDDMS-compatible flat CRS)."""
    # Return the same object with updated schema_version.
    # energyml serializer will emit it under resqml2 namespace with schemaVersion="2.2"
    obj.schema_version = SCHEMA_VERSION_22
    return obj


@registry.register_201_to_22(r"LocalTime3[dD][Cc]rs")
def convert_local_time_3d_crs_to_22(obj: Any, ctx: ConversionContext) -> Any:
    """Keep LocalTime3dCrs as-is for 2.2."""
    obj.schema_version = SCHEMA_VERSION_22
    return obj


# ─── 2.2 -> 2.0.1 CRS ───────────────────────────────────────────────────────

@registry.register_22_to_201(r"LocalDepth3[dD][Cc]rs")
def convert_local_depth_3d_crs_to_201(obj: Any, ctx: ConversionContext) -> Any:
    """LocalDepth3dCrs from 2.2 back to 2.0.1 — just update schema_version."""
    obj.schema_version = SCHEMA_VERSION_201
    return obj


@registry.register_22_to_201(r"LocalTime3[dD][Cc]rs")
def convert_local_time_3d_crs_to_201(obj: Any, ctx: ConversionContext) -> Any:
    """LocalTime3dCrs from 2.2 back to 2.0.1."""
    obj.schema_version = SCHEMA_VERSION_201
    return obj


@registry.register_22_to_201(r"LocalEngineeringCompoundCrs")
def convert_compound_crs_to_201(obj: eml23.LocalEngineeringCompoundCrs, ctx: ConversionContext) -> Any:
    """Convert EML 2.3 LocalEngineeringCompoundCrs back to LocalDepth3dCrs (2.0.1)."""
    uuid = get_obj_uuid(obj)

    vert_ref = obj.vertical_crs
    twod_ref = obj.local_engineering2d_crs
    vert_obj = ctx.get_source(vert_ref.uuid) if vert_ref else None
    twod_obj = ctx.get_source(twod_ref.uuid) if twod_ref else None

    z_down = True
    if obj.vertical_axis:
        z_down = obj.vertical_axis.direction == eml23.VerticalDirection.DOWN

    xoffset = 0.0
    yoffset = 0.0
    areal_rotation_val = 0.0
    projected_uom = r201.LengthUom.M
    axis_order = r201.AxisOrder2D.EASTING_NORTHING
    projected_crs_val = None

    if twod_obj:
        xoffset = getattr(twod_obj, 'origin_projected_coordinate1', 0.0) or 0.0
        yoffset = getattr(twod_obj, 'origin_projected_coordinate2', 0.0) or 0.0
        if twod_obj.azimuth:
            areal_rotation_val = twod_obj.azimuth.value or 0.0
        if twod_obj.horizontal_axes:
            uom_str = twod_obj.horizontal_axes.uom or "m"
            projected_uom = _parse_length_uom_201(uom_str)
            axis_order = _dirs_to_axis_order(
                twod_obj.horizontal_axes.direction1,
                twod_obj.horizontal_axes.direction2,
            )
        if twod_obj.origin_projected_crs:
            projected_crs_val = _convert_projected_crs_23_to_201(twod_obj.origin_projected_crs)

    vertical_uom = r201.LengthUom.M
    vertical_crs_val = None
    if obj.vertical_axis and obj.vertical_axis.uom:
        vertical_uom = _parse_length_uom_201(obj.vertical_axis.uom)
    if vert_obj:
        vertical_crs_val = _convert_vertical_crs_23_to_201(vert_obj)

    return r201.LocalDepth3DCrs(
        citation=convert_citation_23_to_201(obj.citation),
        uuid=uuid,
        schema_version=SCHEMA_VERSION_201,
        xoffset=xoffset,
        yoffset=yoffset,
        zoffset=obj.origin_vertical_coordinate or 0.0,
        zincreasing_downward=z_down,
        projected_axis_order=axis_order,
        projected_uom=projected_uom,
        vertical_uom=vertical_uom,
        areal_rotation=r201.PlaneAngleMeasure(value=areal_rotation_val, uom=r201.PlaneAngleUom.DEGA),
        projected_crs=projected_crs_val or eml20.ProjectedCrsEpsgCode(epsg_code=32631),
        vertical_crs=vertical_crs_val or eml20.VerticalCrsEpsgCode(epsg_code=5714),
    )


@registry.register_22_to_201(r"VerticalCrs")
def convert_vertical_crs_to_201(obj: eml23.VerticalCrs, ctx: ConversionContext) -> None:
    """VerticalCrs gets folded into LocalDepth3dCrs - skip."""
    return None


@registry.register_22_to_201(r"LocalEngineering2[dD][Cc]rs")
def convert_2d_crs_to_201(obj: eml23.LocalEngineering2DCrs, ctx: ConversionContext) -> None:
    """LocalEngineering2dCrs gets folded into LocalDepth3dCrs - skip."""
    return None


# ─── Helper Functions ─────────────────────────────────────────────────────────

def _convert_vertical_crs_23_to_201(vert_obj: Any) -> Any:
    abs_crs = getattr(vert_obj, 'abstract_vertical_crs', None)
    if abs_crs and hasattr(abs_crs, 'epsg_code'):
        return eml20.VerticalCrsEpsgCode(epsg_code=abs_crs.epsg_code)
    return eml20.VerticalCrsEpsgCode(epsg_code=5714)


def _convert_projected_crs_23_to_201(proj_obj: Any) -> Any:
    abs_crs = getattr(proj_obj, 'abstract_projected_crs', None)
    if abs_crs and hasattr(abs_crs, 'epsg_code'):
        return eml20.ProjectedCrsEpsgCode(epsg_code=abs_crs.epsg_code)
    return eml20.ProjectedCrsEpsgCode(epsg_code=32631)


def _dirs_to_axis_order(dir1: Any, dir2: Any) -> r201.AxisOrder2D:
    if dir1 == eml23.AxisDirectionKind.EAST:
        return r201.AxisOrder2D.EASTING_NORTHING
    elif dir1 == eml23.AxisDirectionKind.NORTH:
        return r201.AxisOrder2D.NORTHING_EASTING
    return r201.AxisOrder2D.EASTING_NORTHING


def _parse_length_uom_201(uom_str: Any) -> r201.LengthUom:
    """Parse a UOM string or enum into the 2.0.1 LengthUom enum."""
    if hasattr(uom_str, 'value'):
        uom_str = uom_str.value
    uom_str = str(uom_str).lower()
    uom_map = {"m": r201.LengthUom.M, "ft": r201.LengthUom.FT, "km": r201.LengthUom.KM}
    return uom_map.get(uom_str, r201.LengthUom.M)
