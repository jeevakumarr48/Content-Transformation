"""AI Provider abstraction layer. Supports real API or falls back to demo mode."""
import os
import json
import httpx
from . import demo_data


class AIProvider:
    def __init__(self):
        self.api_key = os.getenv("AI_API_KEY", "")
        self.provider = os.getenv("AI_PROVIDER", "openai")
        self.model = os.getenv("AI_MODEL", "gpt-3.5-turbo")
        self.demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true" or not self.api_key

    async def generate(self, prompt, system_prompt="", max_tokens=2000):
        if self.demo_mode:
            return self._demo_response(prompt)
        try:
            return await self._call_api(prompt, system_prompt, max_tokens)
        except Exception as e:
            print(f"AI API error: {e}. Falling back to demo mode.")
            self.demo_mode = True
            return self._demo_response(prompt)

    async def _call_api(self, prompt, system_prompt, max_tokens):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": self.model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.7},
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

    def _demo_response(self, prompt):
        return json.dumps({"demo": True, "message": "Using demo mode data"})


ai_provider = AIProvider()
