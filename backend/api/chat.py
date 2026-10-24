"""Handle narrator turns and persistent dice-roll events."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.ai.prompt_engineer import build_system_prompt
from backend.api.dependencies import get_game_state, get_narrator, get_story_manager
from backend.utils.dice_roller import roll_dice

router = APIRouter(prefix="/api/stories/{story_id}", tags=["game"])


class ChatRequest(BaseModel):
    """Bound action text so requests remain focused and prompt sizes predictable."""

    message: str = Field(min_length=1, max_length=4000)


class DiceRequest(BaseModel):
    """Carry dice notation as text for strict parsing in the dice utility."""

    notation: str = Field(min_length=3, max_length=32)


@router.post("/chat")
async def send_message(story_id: str, request: ChatRequest) -> dict[str, str]:
    """Build current context, ask the narrator, then persist the complete turn."""

    stories = get_story_manager()
    try:
        context = get_game_state().build_context(story_id)
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
        response = await narrator.reply(build_system_prompt(settings, context), request.message.strip())
    except Exception as error:
        stories.append_event(story_id, "Narrator turn failed", f"**Player:** {request.message.strip()}\n\n**Result:** The AI service could not complete this turn.")
        raise HTTPException(status_code=502, detail="The narrator service could not complete the turn.") from error

    stories.append_event(story_id, "Conversation turn", f"**Player:** {request.message.strip()}\n\n**Narrator:** {response}")
    return {"response": response}


@router.post("/dice")
def roll_for_story(story_id: str, request: DiceRequest) -> dict:
    """Roll and save a result so later narrator context can refer to it."""

    stories = get_story_manager()
    try:
        stories.load_story(story_id)
        result = roll_dice(request.notation)
    except ValueError as error:
        message = str(error)
        status = 400 if "notation" in message or "Roll limits" in message else 400
        raise HTTPException(status_code=status, detail=message) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Story not found.") from error
    details = f"**Notation:** `{result.notation}`\n\n**Dice:** {result.rolls}\n\n**Modifier:** {result.modifier:+d}\n\n**Total:** {result.total}"
    stories.append_event(story_id, "Dice roll", details)
    return {"notation": result.notation, "rolls": result.rolls, "modifier": result.modifier, "total": result.total}
