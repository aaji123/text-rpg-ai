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
        """Return one assistant response while keeping SDK details internal."""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            temperature=0.8,
            max_tokens=700,
        )
        return response.choices[0].message.content or "The narrator has no response."
