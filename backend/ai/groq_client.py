"""Wrap the Groq SDK so the rest of the app only depends on a small interface."""

from groq import AsyncGroq


class GroqNarrator:
    """Send grounded game messages to the configured Groq chat model."""

    def __init__(self, api_key: str, model: str) -> None:
        """Create the provider client only when a key is available."""

        if not api_key:
            raise ValueError("GROQ_API_KEY is not configured.")
        self.client = AsyncGroq(api_key=api_key)
        self.model = model

    async def reply(self, system_prompt: str, message: str) -> str:
        """Collect streamed narrator text while keeping SDK details internal."""

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            temperature=0.6,
            max_completion_tokens=2048,
            top_p=0.95,
            reasoning_effort="default",
            stream=True,
            stop=None,
        )
        response_parts: list[str] = []
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                response_parts.append(content)
        return "".join(response_parts) or "The narrator has no response."

    async def brainstorm(self, idea: str, world_template: str) -> str:
        """Turn a vague campaign premise into three selectable story anchors."""

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You help a player brainstorm RPG plot pillars. Return only a JSON array "
                        "of exactly three concise, distinct strings. Each is an optional long-term "
                        "goal or event, specific enough to guide play but open-ended enough for "
                        "player agency. Do not include markdown or extra keys."
                    ),
                },
                {
                    "role": "user",
                    "content": f"World template: {world_template}\nVague idea: {idea}",
                },
            ],
            temperature=0.6,
            max_completion_tokens=2048,
            top_p=0.95,
            reasoning_effort="default",
            stream=True,
            stop=None,
        )
        response_parts: list[str] = []
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                response_parts.append(content)
        return "".join(response_parts) or "[]"
