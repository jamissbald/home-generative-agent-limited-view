"""Full state snapshot builder."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from ..core.state_filter import get_filtered_states
from .camera_activity import extract_camera_activity
from .derived import derive_context
from .schema import (
    SNAPSHOT_SCHEMA_VERSION,
    FullStateSnapshot,
    SnapshotEntity,
    validate_snapshot,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, State

# ... [_as_iso, _jsonify, _build_entity_snapshot, _build_area_lookup functions remain as-is] ...

async def async_build_full_state_snapshot(hass: HomeAssistant) -> FullStateSnapshot:
    """Build a deterministic full state snapshot filtered by HGASentinel."""
    now = dt_util.now()
    timezone = hass.config.time_zone or str(dt_util.DEFAULT_TIME_ZONE)
    
    # 🔒 ENFORCED SANDBOX
    states = get_filtered_states(hass)
    
    area_lookup = _build_area_lookup(hass)
    image_states = hass.states.async_all("image")
    image_by_camera_id: dict[str, State] = {}
    for image_state in image_states:
        camera_id = image_state.attributes.get("camera_id")
        if isinstance(camera_id, str):
            image_by_camera_id[camera_id] = image_state

    entities = [
        _build_entity_snapshot(state, area_lookup.get(state.entity_id))
        for state in states
    ]
    entities.sort(key=lambda item: item["entity_id"])

    camera_activity = []
    for state in states:
        if state.domain != "camera":
            continue
        camera_activity.append(
            extract_camera_activity(
                state,
                area_lookup.get(state.entity_id),
                image_by_camera_id.get(state.entity_id),
            )
        )
    camera_activity.sort(key=lambda item: item["camera_entity_id"])

    derived = derive_context(
        now=now,
        timezone=timezone,
        sun_state=hass.states.get("sun.sun"),
        all_states=states,
        area_lookup=area_lookup,
    )

    snapshot: dict[str, Any] = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "generated_at": _as_iso(now),
        "entities": entities,
        "camera_activity": camera_activity,
        "derived": derived,
    }

    return validate_snapshot(snapshot)
