"""CRS conversion between RESQML 2.0.1 (LocalDepth3dCrs) and RESQML 2.2 (EML 2.3 CRS)."""

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

@registry.register_201_to_22(r"LocalDepth3[dD][Cc]rs")
def convert_local_depth_3d_crs_to_22(obj: r201.LocalDepth3DCrs, ctx: ConversionContext) -> Any:
    """Convert LocalDepth3dCrs (2.0.1) to LocalEngineeringCompoundCrs + sub-CRSes (2.2/EML2.3).

    In 2.2, a compound CRS references separate VerticalCrs and LocalEngineering2dCrs objects.
    """
    uuid = get_obj_uuid(obj)

    # Create VerticalCrs
    vertical_crs = eml23.VerticalCrs(
        citation=eml23.Citation(
            title=f"{obj.citation.title} - Vertical",
            originator=obj.citation.originator,
            creation=obj.citation.creation,
            format=obj.citation.format,
        ),
        uuid=_derive_uuid(uuid, "vert"),
        schema_version=SCHEMA_VERSION_EML23,
        direction=eml23.VerticalDirection.DOWN if obj.zincreasing_downward else eml23.VerticalDirection.UP,
        uom=str(obj.vertical_uom.value) if obj.vertical_uom else "m",
        abstract_vertical_crs=_convert_vertical_crs_201_to_23(obj.vertical_crs),
    )

    # Create LocalEngineering2dCrs
    local_2d_crs = eml23.LocalEngineering2DCrs(
        citation=eml23.Citation(
            title=f"{obj.citation.title} - 2D",
            originator=obj.citation.originator,
            creation=obj.citation.creation,
            format=obj.citation.format,
        ),
        uuid=_derive_uuid(uuid, "2d"),
        schema_version=SCHEMA_VERSION_EML23,
        azimuth=eml23.PlaneAngleMeasureExt(
            value=obj.areal_rotation.value if obj.areal_rotation else 0.0,
            uom=str(obj.areal_rotation.uom.value) if obj.areal_rotation and obj.areal_rotation.uom else "dega",
        ),
        azimuth_reference=eml23.NorthReferenceKind.TRUE_NORTH,
        origin_projected_coordinate1=obj.xoffset or 0.0,
        origin_projected_coordinate2=obj.yoffset or 0.0,
        horizontal_axes=eml23.HorizontalAxes(
            direction1=_axis_order_to_dir1(obj.projected_axis_order),
            direction2=_axis_order_to_dir2(obj.projected_axis_order),
            uom=str(obj.projected_uom.value) if obj.projected_uom else "m",
            is_time=False,
        ),
        origin_projected_crs=_convert_projected_crs_201_to_23(obj.projected_crs, obj),
    )

    # Create LocalEngineeringCompoundCrs
    compound_crs = eml23.LocalEngineeringCompoundCrs(
        citation=convert_citation_201_to_23(obj.citation),
        uuid=uuid,
        schema_version=SCHEMA_VERSION_EML23,
        origin_vertical_coordinate=obj.zoffset or 0.0,
        vertical_axis=eml23.VerticalAxis(
            direction=eml23.VerticalDirection.DOWN if obj.zincreasing_downward else eml23.VerticalDirection.UP,
            uom=str(obj.vertical_uom.value) if obj.vertical_uom else "m",
            is_time=False,
        ),
        vertical_crs=eml23.DataObjectReference(
            uuid=vertical_crs.uuid,
            title=vertical_crs.citation.title,
            qualified_type=get_qualified_type_from_class_safe(eml23.VerticalCrs),
        ),
        local_engineering2d_crs=eml23.DataObjectReference(
            uuid=local_2d_crs.uuid,
            title=local_2d_crs.citation.title,
            qualified_type=get_qualified_type_from_class_safe(eml23.LocalEngineering2DCrs),
        ),
    )

    # Register the sub-CRS objects as additional outputs
    ctx.register(_derive_uuid(uuid, "vert"), vertical_crs)
    ctx.register(_derive_uuid(uuid, "2d"), local_2d_crs)

    return compound_crs


@registry.register_201_to_22(r"LocalTime3[dD][Cc]rs")
def convert_local_time_3d_crs_to_22(obj: Any, ctx: ConversionContext) -> Any:
    """Convert LocalTime3dCrs to LocalEngineeringCompoundCrs (time domain)."""
    # Same structure as depth, but vertical axis is_time=True
    uuid = get_obj_uuid(obj)

    vertical_crs = eml23.VerticalCrs(
        citation=eml23.Citation(
            title=f"{obj.citation.title} - Vertical",
            originator=obj.citation.originator,
            creation=obj.citation.creation,
            format=obj.citation.format,
        ),
        uuid=_derive_uuid(uuid, "vert"),
        schema_version=SCHEMA_VERSION_EML23,
        direction=eml23.VerticalDirection.DOWN if getattr(obj, 'time_increasing_downward', True) else eml23.VerticalDirection.UP,
        uom="s",
        abstract_vertical_crs=eml23.VerticalUnknownCrs(unknown="Unknown vertical CRS"),
    )

    local_2d_crs = eml23.LocalEngineering2DCrs(
        citation=eml23.Citation(
            title=f"{obj.citation.title} - 2D",
            originator=obj.citation.originator,
            creation=obj.citation.creation,
            format=obj.citation.format,
        ),
        uuid=_derive_uuid(uuid, "2d"),
        schema_version=SCHEMA_VERSION_EML23,
        azimuth=eml23.PlaneAngleMeasureExt(
            value=obj.areal_rotation.value if obj.areal_rotation else 0.0,
            uom="dega",
        ),
        azimuth_reference=eml23.NorthReferenceKind.TRUE_NORTH,
        origin_projected_coordinate1=obj.xoffset or 0.0,
        origin_projected_coordinate2=obj.yoffset or 0.0,
        horizontal_axes=eml23.HorizontalAxes(
            direction1=_axis_order_to_dir1(obj.projected_axis_order),
            direction2=_axis_order_to_dir2(obj.projected_axis_order),
            uom=str(obj.projected_uom.value) if obj.projected_uom else "m",
            is_time=False,
        ),
        origin_projected_crs=_convert_projected_crs_201_to_23(obj.projected_crs, obj),
    )

    compound_crs = eml23.LocalEngineeringCompoundCrs(
        citation=convert_citation_201_to_23(obj.citation),
        uuid=uuid,
        schema_version=SCHEMA_VERSION_EML23,
        origin_vertical_coordinate=obj.zoffset or 0.0,
        vertical_axis=eml23.VerticalAxis(
            direction=eml23.VerticalDirection.DOWN,
            uom="s",
            is_time=True,
        ),
        vertical_crs=eml23.DataObjectReference(
            uuid=vertical_crs.uuid,
            title=vertical_crs.citation.title,
            qualified_type=get_qualified_type_from_class_safe(eml23.VerticalCrs),
        ),
        local_engineering2d_crs=eml23.DataObjectReference(
            uuid=local_2d_crs.uuid,
            title=local_2d_crs.citation.title,
            qualified_type=get_qualified_type_from_class_safe(eml23.LocalEngineering2DCrs),
        ),
    )

    ctx.register(_derive_uuid(uuid, "vert"), vertical_crs)
    ctx.register(_derive_uuid(uuid, "2d"), local_2d_crs)

    return compound_crs


# ─── 2.2 -> 2.0.1 CRS ───────────────────────────────────────────────────────

@registry.register_22_to_201(r"LocalEngineeringCompoundCrs")
def convert_compound_crs_to_201(obj: eml23.LocalEngineeringCompoundCrs, ctx: ConversionContext) -> Any:
    """Convert LocalEngineeringCompoundCrs (EML 2.3) back to LocalDepth3dCrs (2.0.1).

    Collapses the separate VerticalCrs + LocalEngineering2dCrs back into a single CRS.
    """
    uuid = get_obj_uuid(obj)

    # Resolve sub-CRS from context
    vert_ref = obj.vertical_crs
    twod_ref = obj.local_engineering2d_crs

    vert_obj = ctx.get_source(vert_ref.uuid) if vert_ref else None
    twod_obj = ctx.get_source(twod_ref.uuid) if twod_ref else None

    # Extract vertical direction
    z_down = True
    if obj.vertical_axis:
        z_down = obj.vertical_axis.direction == eml23.VerticalDirection.DOWN

    # Extract offsets from 2D CRS
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
        # Projected CRS
        if twod_obj.origin_projected_crs:
            projected_crs_val = _convert_projected_crs_23_to_201(twod_obj.origin_projected_crs)

    # Vertical CRS and UOM
    vertical_uom = r201.LengthUom.M
    vertical_crs_val = None
    if obj.vertical_axis and obj.vertical_axis.uom:
        vertical_uom = _parse_length_uom_201(obj.vertical_axis.uom)
    if vert_obj:
        vertical_crs_val = _convert_vertical_crs_23_to_201(vert_obj)

    crs = r201.LocalDepth3DCrs(
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
    return crs


@registry.register_22_to_201(r"VerticalCrs")
def convert_vertical_crs_to_201(obj: eml23.VerticalCrs, ctx: ConversionContext) -> None:
    """VerticalCrs gets folded into LocalDepth3dCrs - return None to skip standalone output."""
    return None


@registry.register_22_to_201(r"LocalEngineering2[dD][Cc]rs")
def convert_2d_crs_to_201(obj: eml23.LocalEngineering2DCrs, ctx: ConversionContext) -> None:
    """LocalEngineering2dCrs gets folded into LocalDepth3dCrs - return None to skip."""
    return None


# ─── Helper Functions ─────────────────────────────────────────────────────────

def _derive_uuid(base_uuid: str, suffix: str) -> str:
    """Derive a deterministic UUID from a base UUID by modifying last chars."""
    import hashlib
    h = hashlib.md5(f"{base_uuid}-{suffix}".encode()).hexdigest()
    return f"{h[:8]}-{h[8:12]}-4{h[13:16]}-a{h[17:20]}-{h[20:32]}"


def _convert_vertical_crs_201_to_23(vert: Any) -> Any:
    """Convert 2.0.1 vertical CRS choice to 2.3 abstract_vertical_crs."""
    if vert is None:
        return eml23.VerticalUnknownCrs(unknown="Unknown")
    if hasattr(vert, 'epsg_code'):
        return eml23.VerticalEpsgCrs(epsg_code=vert.epsg_code)
    if hasattr(vert, 'wkt'):
        return eml23.VerticalWktCrs(well_known_text=vert.wkt)
    return eml23.VerticalUnknownCrs(unknown="Unknown")


def _convert_vertical_crs_23_to_201(vert_obj: Any) -> Any:
    """Convert EML 2.3 VerticalCrs object to 2.0.1 vertical CRS reference."""
    abs_crs = getattr(vert_obj, 'abstract_vertical_crs', None)
    if abs_crs is None:
        return eml20.VerticalCrsEpsgCode(epsg_code=5714)
    if hasattr(abs_crs, 'epsg_code'):
        return eml20.VerticalCrsEpsgCode(epsg_code=abs_crs.epsg_code)
    return eml20.VerticalCrsEpsgCode(epsg_code=5714)


def _convert_projected_crs_201_to_23(proj: Any, parent: Any = None) -> Any:
    """Convert 2.0.1 projected CRS to inline EML 2.3 ProjectedCrs."""
    epsg_code = 32631  # Default UTM 31N
    if proj and hasattr(proj, 'epsg_code'):
        epsg_code = proj.epsg_code

    uom = "m"
    axis_order = eml23.AxisOrder2D.EASTING_NORTHING
    if parent:
        if parent.projected_uom:
            uom = str(parent.projected_uom.value)
        if parent.projected_axis_order:
            axis_order = eml23.AxisOrder2D(parent.projected_axis_order.value)

    return eml23.ProjectedCrs(
        citation=eml23.Citation(
            title="Projected CRS",
            originator="resqml-converter",
            creation="2026-01-01T00:00:00Z",
            format="energyml",
        ),
        uuid=_derive_uuid(get_obj_uuid(parent) if parent else "default", "proj"),
        schema_version=SCHEMA_VERSION_EML23,
        axis_order=axis_order,
        abstract_projected_crs=eml23.ProjectedEpsgCrs(epsg_code=epsg_code),
        uom=uom,
    )


def _convert_projected_crs_23_to_201(proj_obj: Any) -> Any:
    """Convert EML 2.3 ProjectedCrs to 2.0.1 projected CRS choice."""
    abs_crs = getattr(proj_obj, 'abstract_projected_crs', None)
    if abs_crs and hasattr(abs_crs, 'epsg_code'):
        return eml20.ProjectedCrsEpsgCode(epsg_code=abs_crs.epsg_code)
    return eml20.ProjectedCrsEpsgCode(epsg_code=32631)


def _axis_order_to_dir1(axis_order: Any) -> eml23.AxisDirectionKind:
    if axis_order and axis_order.value == "easting northing":
        return eml23.AxisDirectionKind.EAST
    elif axis_order and axis_order.value == "northing easting":
        return eml23.AxisDirectionKind.NORTH
    return eml23.AxisDirectionKind.EAST


def _axis_order_to_dir2(axis_order: Any) -> eml23.AxisDirectionKind:
    if axis_order and axis_order.value == "easting northing":
        return eml23.AxisDirectionKind.NORTH
    elif axis_order and axis_order.value == "northing easting":
        return eml23.AxisDirectionKind.EAST
    return eml23.AxisDirectionKind.NORTH


def _dirs_to_axis_order(dir1: Any, dir2: Any) -> r201.AxisOrder2D:
    if dir1 == eml23.AxisDirectionKind.EAST:
        return r201.AxisOrder2D.EASTING_NORTHING
    elif dir1 == eml23.AxisDirectionKind.NORTH:
        return r201.AxisOrder2D.NORTHING_EASTING
    return r201.AxisOrder2D.EASTING_NORTHING


def _parse_length_uom_201(uom_str: str) -> r201.LengthUom:
    """Parse a UOM string into the 2.0.1 LengthUom enum."""
    uom_map = {"m": r201.LengthUom.M, "ft": r201.LengthUom.FT, "km": r201.LengthUom.KM}
    return uom_map.get(uom_str.lower(), r201.LengthUom.M)


def get_qualified_type_from_class_safe(cls) -> str:
    """Get qualified type string, with fallback."""
    try:
        from energyml.utils.introspection import get_qualified_type_from_class
        return get_qualified_type_from_class(cls)
    except Exception:
        return f"eml23.{cls.__name__}"
