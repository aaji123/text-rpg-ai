"""Normalize narrator JSON so presentation and state updates stay separate."""

import json
import re
from typing import Any


def parse_narrator_response(raw_response: str) -> dict[str, Any]:
    """Extract plain narrative, optional action buttons, and safe state metadata."""

    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", raw_response).strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    payload: dict[str, Any] = {}
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        opening = cleaned.find("{")
        if opening >= 0:
            try:
                candidate, _ = json.JSONDecoder().raw_decode(cleaned[opening:])
                if isinstance(candidate, dict):
                    payload = candidate
            except json.JSONDecodeError:
                pass

    legacy_update = re.search(r"<!--\s*RPG_STATE_UPDATE:\s*(\{[\s\S]*?\})\s*-->", cleaned)
    state_update = payload.get("state_update", {}) if isinstance(payload.get("state_update"), dict) else {}
    if legacy_update:
        try:
            old_data = json.loads(legacy_update.group(1))
            if isinstance(old_data, dict):
                state_update = old_data
        except json.JSONDecodeError:
            pass

    narrative = payload.get("narrative") if isinstance(payload.get("narrative"), str) else cleaned
    if legacy_update and not payload:
        narrative = narrative.replace(legacy_update.group(0), "")
    narrative = _plain_prose(narrative)

    raw_actions = payload.get("suggested_actions", [])
    actions: list[str] = []
    if isinstance(raw_actions, list):
        for item in raw_actions:
            if isinstance(item, str) and item.strip():
                action = _plain_prose(item)[:160]
                if action:
                    actions.append(action)
            if len(actions) == 3:
                break
    if len(actions) < 2:
        actions = ["Look more closely at a detail that catches your attention.", "Listen for where the unusual sound is coming from."]
    summary = payload.get("session_summary", "")
    if not isinstance(summary, str):
        summary = ""
    return {
        "narrative": narrative or "The scene holds for a moment.",
        "suggested_actions": actions,
        "state_update": state_update,
        "session_summary": _plain_prose(summary),
    }


def _plain_prose(value: str) -> str:
    """Strip common Markdown formatting that breaks an immersive transcript."""

    value = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", value)
    value = re.sub(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+", "", value)
    value = re.sub(r"\*\*(.*?)\*\*|__(.*?)__", lambda match: match.group(1) or match.group(2), value)
    value = re.sub(r"(?<!\*)\*(?!\*)(.*?)\*(?!\*)|(?<!_)_(?!_)(.*?)_(?!_)", lambda match: match.group(1) or match.group(2), value)
    return value.strip()


def plain_command_text(value: str) -> str:
    """Remove Markdown decoration while preserving readable command line breaks."""

    return _plain_prose(value)
