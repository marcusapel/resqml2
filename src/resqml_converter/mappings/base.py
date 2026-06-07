"""Base mapper infrastructure for two-way RESQML conversion."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type

from energyml.utils.introspection import (
    get_obj_uuid,
    get_qualified_type_from_class,
    get_class_fields,
    get_class_pkg_version,
)
from energyml.utils.epc_utils import copy_attributes


@dataclass
class ConversionContext:
    """Shared state during a conversion run."""

    direction: str  # "201_to_22" or "22_to_201"
    source_objects: Dict[str, Any] = field(default_factory=dict)  # uuid -> source obj
    converted_objects: Dict[str, Any] = field(default_factory=dict)  # uuid -> converted obj
    uuid_map: Dict[str, str] = field(default_factory=dict)  # source_uuid -> target_uuid (preserved)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def get_source(self, uuid: str) -> Optional[Any]:
        return self.source_objects.get(uuid)

    def get_converted(self, uuid: str) -> Optional[Any]:
        return self.converted_objects.get(uuid)

    def register(self, source_uuid: str, converted_obj: Any) -> None:
        self.converted_objects[source_uuid] = converted_obj
        self.uuid_map[source_uuid] = get_obj_uuid(converted_obj)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def error(self, msg: str) -> None:
        self.errors.append(msg)


# Type for a mapper function: (source_obj, context) -> converted_obj
MapperFn = Callable[[Any, ConversionContext], Any]


class MapperRegistry:
    """Registry of type-specific conversion mappers.

    Mappers are registered by source class name pattern and direction.
    """

    def __init__(self):
        # direction -> [(class_name_pattern, mapper_fn)]
        self._mappers: Dict[str, List[Tuple[str, MapperFn]]] = {
            "201_to_22": [],
            "22_to_201": [],
        }

    def register(self, direction: str, class_pattern: str, fn: MapperFn) -> None:
        """Register a mapper for a class name pattern and direction."""
        self._mappers[direction].append((class_pattern, fn))

    def register_201_to_22(self, class_pattern: str):
        """Decorator to register a 2.0.1 -> 2.2 mapper."""
        def decorator(fn: MapperFn) -> MapperFn:
            self.register("201_to_22", class_pattern, fn)
            return fn
        return decorator

    def register_22_to_201(self, class_pattern: str):
        """Decorator to register a 2.2 -> 2.0.1 mapper."""
        def decorator(fn: MapperFn) -> MapperFn:
            self.register("22_to_201", class_pattern, fn)
            return fn
        return decorator

    def get_mapper(self, direction: str, obj: Any) -> Optional[MapperFn]:
        """Find the most specific mapper for an object."""
        class_name = type(obj).__name__
        for pattern, fn in self._mappers.get(direction, []):
            if re.match(pattern, class_name, re.IGNORECASE):
                return fn
        return None

    def convert(self, obj: Any, ctx: ConversionContext) -> Optional[Any]:
        """Convert an object using the registered mapper."""
        mapper = self.get_mapper(ctx.direction, obj)
        if mapper is None:
            # Fallback: try generic attribute copy
            return self._generic_convert(obj, ctx)
        return mapper(obj, ctx)

    def _generic_convert(self, obj: Any, ctx: ConversionContext) -> Optional[Any]:
        """Generic fallback: try to find matching class in target version and copy attributes."""
        from resqml_converter.mappings.common import find_target_class, create_target_instance
        target_cls = find_target_class(obj, ctx.direction)
        if target_cls is None:
            ctx.warn(f"No mapper or target class found for {type(obj).__name__}")
            return None
        target = create_target_instance(target_cls, obj, ctx)
        return target


# Global registry instance
registry = MapperRegistry()
