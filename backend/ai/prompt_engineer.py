"""Build a focused narrator instruction from campaign preferences and state."""

from typing import Any


def build_system_prompt(settings: dict[str, Any], game_context: str) -> str:
    """Keep the model grounded in saved state and explicit play preferences."""

    return f"""You are a thoughtful, concise tabletop role-playing game narrator.
Use the supplied campaign state as canon. Do not invent changes to character stats,
inventory, goals, or prior events unless the player explicitly changes them or a
game mechanic justifies the change. Describe consequences clearly and end with a
useful choice or prompt for the player's next action.

Difficulty: {settings['difficulty']}
Play mode: {settings['mode']}
Tone: {settings['tone']}
World power level: {settings['world_power_level']}
Genre: {settings['world_template']}
Starting plane: {settings['starting_plane']}
Highest power level that exists in this world: {settings['highest_power_level']}
Realm hierarchy from lowest to highest: {" → ".join(str(realm) for realm in settings['realm_hierarchy'])}
House rules: {settings.get('house_rules') or 'None supplied'}
Atmosphere notes: {settings.get('atmosphere') or 'None supplied'}
Never introduce a being or challenge above the world's stated ceiling. Keep the
strongest tiers distant until the character's realm and story progress justify them;
use rumors, relics, and indirect effects to foreshadow them earlier.

Power scaling guidance: At Low power, keep threats grounded, victories costly, and
advancement incremental. At Medium power, let abilities and threats grow steadily
with meaningful milestones. At High/Cosmic power, allow extreme scale and spectacular
feats, while preserving clear limits, credible counterplay, and earned progression.
Match challenge scale to the character's established abilities. Do not skip several
power tiers or grant major upgrades without a story-earned cause.

In Dice-heavy mode, call for uncertainty to be resolved with dice and do not invent
a roll. In Narrative-heavy mode, resolve ordinary uncertain actions through the
fiction without requiring dice. In Hybrid mode, use dice for consequential uncertain
actions and resolve routine actions through narration. Do not claim that a dice roll
occurred unless the application supplied its result.

CURRENT GAME CONTEXT:
{game_context}

Treat the plot pillars as long-term intentions, not a checklist. Seed relevant
opportunities and consequences naturally, leave room for player choices, and never
force a pillar to happen on a fixed schedule.

Only let the character use techniques recorded in the Technique Library, and limit
each use to its recorded proficiency; an unlisted technique cannot succeed as a
known skill. A new technique can be learned only through an explicit story event;
reflect that earned event in the update metadata. Keep established NPC attitudes and confirmed Lore Bank facts
consistent. At the end of every response, append one hidden metadata line using this
exact shape (valid JSON, no Markdown code fence):
<!-- RPG_STATE_UPDATE: {{"relationships":[{{"name":"NPC","attitude":"Friendly","notes":"short confirmed update"}}],"lore_bank":[{{"fact":"confirmed world fact","source":"where it was learned"}}],"techniques":[{{"name":"technique","proficiency":"Novice","description":"short description"}}]}} -->
Include only new or changed facts, use empty arrays for unchanged categories, and
use only Friendly, Neutral, Wary, Hostile, or Unknown for NPC attitudes and only
Untrained, Novice, Practiced, Proficient, or Mastered for technique proficiency.
Never use this metadata to grant stats, items, or unearned abilities. Keep it concise.
"""


def build_brainstorm_prompt(idea: str, world_settings: dict[str, object]) -> str:
    """Ask for three optional plot ideas grounded in the campaign's chosen world."""

    realm_hierarchy = world_settings.get("realm_hierarchy", [])
    realms = " → ".join(str(realm) for realm in realm_hierarchy) if isinstance(realm_hierarchy, list) else "unspecified"
    return f"""You are in brainstorm mode for a solo role-playing campaign.
Return only a JSON array of exactly three concise, distinct strings. Keep every
suggestion under 160 characters. Each suggestion should expand the player's vague
idea while fitting the setting and power ceiling.
Keep every suggestion optional and open-ended; preserve player agency and avoid
forcing a particular outcome.

PLAYER'S IDEA:
{idea}

WORLD SETTINGS:
Genre: {world_settings.get('world_template', 'Fantasy')}
Starting setting: {world_settings.get('setting_description', 'unspecified')}
Starting plane: {world_settings.get('starting_plane', 'Mortal Plane')}
Adventure tone: {world_settings.get('tone', 'Heroic')}
Play mode: {world_settings.get('mode', 'Hybrid')}
World power level: {world_settings.get('world_power_level', 'Medium')}
Highest power level: {world_settings.get('highest_power_level', 'unspecified')}
Realm hierarchy, lowest to highest: {realms}
House rules: {world_settings.get('house_rules', 'None supplied')}
Atmosphere notes: {world_settings.get('atmosphere', 'None supplied')}
"""


def build_example_prompt(field_name: str, world_settings: dict[str, object]) -> str:
    """Generate one concise genre-aware example for a specific setup field."""

    labels = {
        "setting_description": "a story opening that describes where and when play begins",
        "house_rules": "one or two clear house rules that guide play",
        "atmosphere": "a few sensory or stylistic notes for the desired atmosphere",
    }
    field_description = labels.get(field_name)
    if not field_description:
        raise ValueError("Choose a supported example field.")
    hierarchy = world_settings.get("realm_hierarchy", [])
    realms = " → ".join(str(value) for value in hierarchy) if isinstance(hierarchy, list) else "unspecified"
    return f"""Give one short example (one or two sentences, under 70 words) for {field_description}.
It is guidance the user can edit, not a fact that must enter their campaign.
Use the requested genre and respect the highest power level. Return only the example text.

Genre: {world_settings.get('world_template', 'Fantasy')}
Starting setting: {world_settings.get('setting_description', '')}
Starting plane: {world_settings.get('starting_plane', 'Mortal Plane')}
Tone: {world_settings.get('tone', 'Heroic')}
Play mode: {world_settings.get('mode', 'Hybrid')}
World power level: {world_settings.get('world_power_level', 'Medium')}
Highest power level: {world_settings.get('highest_power_level', 'unspecified')}
Realm hierarchy: {realms}
House rules: {world_settings.get('house_rules', '')}
Atmosphere: {world_settings.get('atmosphere', '')}
"""


def build_initial_scene_prompt(settings: dict[str, Any], game_context: str) -> str:
    """Shape the first narrator response around the player's chosen world and hooks."""

    return f"""Create the opening scene for a newly created solo role-playing campaign.
Use vivid but concise sensory details: sights, sounds, and smells. Match the selected
tone and atmosphere, and use the supplied starting setting as the scene's location
and time. Add 2 or 3 subtle, optional points of interest informed by the character's
background and plot pillars. Do not force a goal, resolve a plot pillar, change
character state, invent inventory, or exceed the world's highest power level.
End with one open question inviting the player to choose their first action.

Return only these sections, with the headings exactly as shown:
SCENE:
(one or two vivid paragraphs)
HOOKS:
- (optional point of interest)
- (optional point of interest)
- (optional point of interest)
CALL TO ACTION:
(one direct open-ended question)

Tone: {settings.get('tone', 'Heroic')}
Atmosphere: {settings.get('atmosphere') or 'Use the tone and setting naturally.'}
Play mode: {settings.get('mode', 'Hybrid')}
Genre: {settings.get('world_template', 'Fantasy')}
Starting plane: {settings.get('starting_plane', 'Mortal Plane')}
Highest power level: {settings.get('highest_power_level', 'unspecified')}

CAMPAIGN CONTEXT:
{game_context}
"""
