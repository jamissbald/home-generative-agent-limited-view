"""Langgraph tools for Home Generative Agent."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import math
import re
from collections.abc import Mapping, Generator
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import aiofiles
import homeassistant.util.dt as dt_util
import voluptuous as vol
import yaml

from homeassistant.components import camera
from homeassistant.components.automation.config import _async_validate_config_item
from homeassistant.components.automation.const import DOMAIN as AUTOMATION_DOMAIN
from homeassistant.components.recorder import history as recorder_history
from homeassistant.components.recorder import statistics as recorder_statistics
from homeassistant.config import AUTOMATION_CONFIG_PATH
from homeassistant.const import ATTR_FRIENDLY_NAME, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import State
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import llm
from homeassistant.helpers.recorder import get_instance as get_recorder_instance
from homeassistant.helpers.recorder import session_scope as recorder_session_scope
from homeassistant.util import ulid

from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig, RunnableSerializable
from langchain_core.tools import InjectedToolArg, tool

from langgraph.prebuilt.tool_node import InjectedStore
from langgraph.store.base import BaseStore

from voluptuous import MultipleInvalid

from ..const import (
    AUTOMATION_TOOL_BLUEPRINT_NAME,
    AUTOMATION_TOOL_EVENT_REGISTERED,
    CONF_CRITICAL_ACTION_PIN_HASH,
    CONF_CRITICAL_ACTION_PIN_SALT,
    CONF_NOTIFY_SERVICE,
    CRITICAL_PIN_MAX_LEN,
    CRITICAL_PIN_MIN_LEN,
    HISTORY_TOOL_CONTEXT_LIMIT,
    HISTORY_TOOL_PURGE_KEEP_DAYS,
    VLM_IMAGE_HEIGHT,
    VLM_IMAGE_WIDTH,
    VLM_SYSTEM_PROMPT,
    VLM_USER_KW_TEMPLATE,
    VLM_USER_PROMPT,
)

from ..core.conversation_helpers import _resolve_entity_id
from ..core.utils import extract_final, verify_pin
from .camera_activity import get_camera_last_events_from_states
from .helpers import (
    maybe_fill_lock_entity,
    normalize_intent_for_alarm,
    normalize_intent_for_lock,
    sanitize_tool_args,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

LOGGER = logging.getLogger(__name__)

# -------------------------------------------------------------
# STUBS TO PREVENT IMPORT CRASHES
# -------------------------------------------------------------
def analyze_image(*args, **kwargs):
    """Temporary stub so integration loads."""
    return None

def get_and_analyze_camera_image(*args, **kwargs):
    """Temporary stub so integration loads."""
    return None

def add_automation(*args, **kwargs):
    """Temporary stub so integration loads."""
    return None

# -------------------------------------------------------------
# FIXED ENTITY LOOKUP
# -------------------------------------------------------------
async def _get_existing_entity_id(
    name: str | None,
    hass: HomeAssistant,
    domain: str | None = "sensor",
) -> str:
    """Lookup entity by friendly name (HGASentinel filtered version)."""
    from homeassistant.helpers import entity_registry as er

    if not isinstance(name, str) or not name.strip():
        raise ValueError("Name must be a non-empty string")

    if not isinstance(domain, str):
        raise ValueError("Invalid domain")

    target = name.strip().lower()
    prefix = f"{domain}."
    
    # Use Entity Registry for reliable label checking
    registry = er.async_get(hass)
    allowed_ids = {
        entry.entity_id for entry in registry.entities.values()
        if entry.labels and "HGASentinel" in entry.labels
    }

    candidates: list[str] = []
    for state in hass.states.async_all():
        if state.entity_id not in allowed_ids:
            continue

        if not state.entity_id.startswith(prefix):
            continue

        fn = state.attributes.get("friendly_name", "")
        if isinstance(fn, str) and fn.strip().lower() == target:
            candidates.append(state.entity_id)

    if not candidates:
        raise ValueError(f"No '{domain}' entity found with friendly name '{name}' (or not tagged HGASentinel)")

    if len(candidates) > 1:
        raise ValueError(f"Multiple matches found: {candidates}")

    return candidates[0]
