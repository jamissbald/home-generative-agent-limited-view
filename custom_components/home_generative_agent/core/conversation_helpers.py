"""Helper utilities for conversation processing."""

from __future__ import annotations

import difflib
import logging
import re
from typing import TYPE_CHECKING
from .state_filter import get_filtered_states

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_ENTITY_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
_ENTITY_ID_MATCH_SCORE_MIN = 0.6
_ENTITY_ID_TOKEN_OVERLAP_WEIGHT = 0.2

def _resolve_entity_id(entity_id: str, hass: HomeAssistant) -> str:
    """Try to resolve a suggested entity_id to an existing sandboxed entity_id."""
    if not _ENTITY_ID_PATTERN.match(entity_id):
        return entity_id

    # Get the allowed pool from our sandbox
    allowed_states = get_filtered_states(hass)
    allowed_ids = {s.entity_id for s in allowed_states}

    if entity_id in allowed_ids:
        return entity_id

    domain, object_id = entity_id.split(".", 1)
    prefix = f"{domain}."
    
    # Fuzzy match only against sandboxed entities
    candidates = [
        state.entity_id
        for state in allowed_states
        if state.entity_id.startswith(prefix)
    ]
    
    if not candidates:
        return entity_id

    def score_match(candidate: str) -> float:
        candidate_obj = candidate.split(".", 1)[1]
        ratio = difflib.SequenceMatcher(None, object_id, candidate_obj).ratio()
        target_tokens = {t for t in object_id.split("_") if t}
        candidate_tokens = {t for t in candidate_obj.split("_") if t}
        overlap = 0.0
        if target_tokens:
            overlap = len(target_tokens & candidate_tokens) / len(target_tokens)
        return ratio + (overlap * _ENTITY_ID_TOKEN_OVERLAP_WEIGHT)

    scored = max(candidates, key=score_match)
    if score_match(scored) >= _ENTITY_ID_MATCH_SCORE_MIN:
        return scored

    return entity_id

# [Keep other helper functions like _fix_dashboard_entities below]
