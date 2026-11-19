import os


def complete_json(system: str, user: str, model: str) -> str:
    provider = os.getenv("LLM_PROVIDER", "").lower()
    if provider == "openai":
        from openai import OpenAI
        response = OpenAI().chat.completions.create(model=model, response_format={"type": "json_object"}, messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
        return response.choices[0].message.content or ""
    if provider == "anthropic":
        from anthropic import Anthropic
        response = Anthropic().messages.create(model=model, max_tokens=1800, system=system, messages=[{"role": "user", "content": user}])
        return "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
    raise ValueError("LLM_PROVIDER must be openai or anthropic")
