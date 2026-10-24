"""Handle narrator turns and persistent dice-roll events."""

import json
import logging
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.ai.prompt_engineer import build_command_prompt, build_help_prompt, build_recap_prompt, build_system_prompt
from backend.ai.response_parser import parse_narrator_response, plain_command_text
from backend.ai.groq_client import GroqRequestError
from backend.api.dependencies import get_game_state, get_narrator, get_story_manager
from backend.api.provider_errors import to_http_exception
from backend.observability import request_id_context
from backend.utils.dice_roller import roll_dice

router = APIRouter(prefix="/api/stories/{story_id}", tags=["game"])
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    """Bound action text so requests remain focused and prompt sizes predictable."""

    message: str = Field(min_length=1, max_length=4000)


class DiceRequest(BaseModel):
    """Carry dice notation with an optional target for explicit pass/fail results."""

    notation: str = Field(min_length=3, max_length=32)


@router.post("/chat")
async def send_message(story_id: str, request: ChatRequest) -> dict:
    """Handle an in-world action or an out-of-character rules question."""

    stories = get_story_manager()
    player_message = request.message.strip()
    command = player_message.lower()
    help_command = command == "/help"
    status_command = command in {"/stats", "/status"}
    inventory_command = command == "/inventory"
    ooc = command == "/ooc" or command.startswith("/ooc ")
    if status_command or inventory_command:
        try:
            story = stories.load_story(story_id)
        except ValueError as error:
            raise HTTPException(status_code=400, detail="Invalid story identifier.") from error
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail="Story not found.") from error
        try:
            settings = stories.read_settings(story_id)
            response_text = plain_command_text(await get_narrator().reply(
                build_command_prompt("stats" if status_command else "inventory", story["state"], settings),
                player_message,
            ))
        except GroqRequestError as error:
            raise to_http_exception(error) from error
        except ValueError as error:
            raise HTTPException(status_code=503, detail="Groq API key is not configured in .env.") from error
        heading = "Stats command" if status_command else "Inventory command"
        stories.append_event(story_id, heading, f"**Player:** {player_message}\n\n**Narrator:** {response_text}")
        return {"response": response_text, "suggested_actions": [], "command": "status" if status_command else "inventory", "ooc": False}
    if ooc:
        player_message = player_message[4:].strip() or "Please clarify the rules or campaign details."
    try:
        if not ooc and not help_command:
            item_changes = stories.update_item_usage(story_id, player_message)
            if item_changes:
                stories.append_event(story_id, "Automatic item use", "\n".join(f"- {change}" for change in item_changes))
        turn_count = stories.count_conversation_turns(story_id)
        next_turn = turn_count + (0 if ooc or help_command else 1)
        history_limit = 30 if not ooc and not help_command and next_turn > 0 and next_turn % 12 == 0 else 12
        context = get_game_state().build_context(story_id, history_limit=history_limit)
        settings = stories.read_settings(story_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid story identifier.") from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Story not found.") from error
    try:
        narrator = get_narrator()
    except ValueError as error:
        raise HTTPException(status_code=503, detail="Groq API key is not configured in .env.") from error

    try:
        system_prompt = build_help_prompt() if help_command else build_system_prompt(settings, context, turn_count, ooc=ooc)
        if ooc:
            system_prompt += "\n\nOOC MODE: The player prefixed this with /ooc. Reply as a helpful collaborative partner about rules, continuity, or options. Do not narrate an in-world scene, advance time, alter game state, trigger a world tick, or return suggested actions. Keep the answer concise and place it in the narrative field."
        response = await narrator.reply(system_prompt, "/help" if help_command else player_message)
    except GroqRequestError as error:
        stories.append_event(story_id, "Narrator turn failed", f"**Player:** {request.message.strip()}\n\n**Result:** The AI service could not complete this turn.")
        raise to_http_exception(error) from error
    except Exception as error:
        logger.exception("Unexpected narrator route failure request_id=%s", request_id_context.get())
        stories.append_event(story_id, "Narrator turn failed", f"**Player:** {request.message.strip()}\n\n**Result:** The AI service could not complete this turn.")
        raise HTTPException(status_code=502, detail="The narrator service could not complete the turn.") from error

    result = parse_narrator_response(response)
    if not ooc and not help_command and result["state_update"]:
        try:
            stories.apply_narrative_updates(story_id, result["state_update"])
        except ValueError:
            pass

    session_break = not ooc and not help_command and next_turn > 0 and next_turn % 12 == 0
    heading = "Help command" if help_command else "Out-of-character conversation" if ooc else "Conversation turn"
    log_parts = [f"**Player:** {request.message.strip()}", f"**Narrator:** {result['narrative']}"]
    if result["suggested_actions"] and not ooc and not help_command:
        log_parts.append("**Suggested actions JSON:** " + json.dumps(result["suggested_actions"], ensure_ascii=False))
    stories.append_event(story_id, heading, "\n\n".join(log_parts))
    if session_break and not result["session_summary"]:
        try:
            updated_context = get_game_state().build_context(story_id, history_limit=30)
            result["session_summary"] = (await narrator.reply(build_recap_prompt(updated_context), "Summarize this campaign for the next session.")).strip()
        except Exception:
            result["session_summary"] = ""
    if session_break and result["session_summary"]:
        stories.append_event(story_id, "Session Summary", result["session_summary"])
    return {
        "response": result["narrative"],
        "suggested_actions": [] if ooc or help_command else result["suggested_actions"],
        "session_break": session_break,
        "session_summary": result["session_summary"] if session_break else "",
        "ooc": ooc,
        "command": "help" if help_command else "",
    }


@router.post("/recap")
async def recap_story(story_id: str) -> dict[str, str]:
    """Summarize up to ten recent interactions for quick continuity refresh."""

    stories = get_story_manager()
    try:
        story = stories.load_story(story_id)
        context = get_game_state().build_context(story_id, history_limit=30)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid story identifier.") from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Story not found.") from error
    try:
        recap = (await get_narrator().reply(build_recap_prompt(context), f"Summarize recent events in {story['name']}.")).strip()
    except GroqRequestError as error:
        raise to_http_exception(error) from error
    except ValueError as error:
        raise HTTPException(status_code=503, detail="Groq API key is not configured in .env.") from error
    except Exception as error:
        logger.exception("Unexpected recap route failure request_id=%s", request_id_context.get())
        raise HTTPException(status_code=502, detail="The recap could not be generated.") from error
    if not recap:
        logger.error("Groq recap response was empty request_id=%s", request_id_context.get())
        raise HTTPException(status_code=502, detail="The recap service returned an empty response.")
    stories.append_event(story_id, "Recap", f"**Narrator:** {recap}")
    return {"recap": recap}


@router.post("/dice")
async def roll_for_story(story_id: str, request: DiceRequest) -> dict:
    """Roll and save a result so later narrator context can refer to it."""

    stories = get_story_manager()
    try:
        story = stories.load_story(story_id)
        target_match = re.fullmatch(r"\s*(.+?)(?:\s+(?:vs|dc)\s*(\d+))?\s*", request.notation, re.IGNORECASE)
        if not target_match:
            raise ValueError("Use dice notation such as 1d20 or 1d20 vs 15.")
        result = roll_dice(target_match.group(1))
        difficulty_class = int(target_match.group(2)) if target_match.group(2) else None
        if difficulty_class is not None and not 1 <= difficulty_class <= 10000:
            raise ValueError("A roll target must be from 1 to 10,000.")
    except ValueError as error:
        message = str(error)
        status = 400 if "notation" in message or "Roll limits" in message else 400
        raise HTTPException(status_code=status, detail=message) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Story not found.") from error
    success = result.total >= difficulty_class if difficulty_class is not None else None
    details = f"**Notation:** `{result.notation}`\n\n**Dice:** {result.rolls}\n\n**Modifier:** {result.modifier:+d}\n\n**Total:** {result.total}"
    if difficulty_class is not None:
        details += f"\n\n**Difficulty Class:** {difficulty_class}\n\n**Outcome:** {'Success' if success else 'Failure'}"
    stories.append_event(story_id, "Dice roll", details)
    roll_data = {"notation": result.notation, "rolls": result.rolls, "modifier": result.modifier, "total": result.total, "difficulty_class": difficulty_class, "success": success}
    settings = stories.read_settings(story_id)
    prompt = build_command_prompt("roll", stories.load_state(story_id), settings, roll_data)
    try:
        response = plain_command_text(await get_narrator().reply(prompt, f"/roll {request.notation}"))
    except GroqRequestError as error:
        logger.warning("Dice narration unavailable request_id=%s category=%s", request_id_context.get(), error.category)
        response = "The roll is saved. Narration is temporarily unavailable; the result above remains authoritative."
    except ValueError as error:
        response = "The roll is saved. Add a Groq API key to enable narrated interpretation."
    return {**roll_data, "response": response}
