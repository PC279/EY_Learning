"""
ai_client.py
------------
Sends the question + retrieved chunks to an AI model and returns its answer.

You only need ONE provider. Pick it in the .env file:
    AI_PROVIDER=gemini      (free tier available: https://aistudio.google.com/apikey)
    AI_PROVIDER=openai      (https://platform.openai.com/api-keys)
    AI_PROVIDER=anthropic   (https://console.anthropic.com)
    AI_PROVIDER=openrouter  (https://openrouter.ai/keys - one key, hundreds of models)
"""

import os

import config

NOT_FOUND_MESSAGE = "I cannot find the answer in the provided documents."

# The instructions we give the AI. This is what keeps it "grounded".
SYSTEM_PROMPT = f"""You are a helpful assistant for Cedarline Systems employees.
Answer the question using ONLY the information in the context below.
Do not use any outside knowledge and do not guess.
If the context does not contain the answer, reply exactly:
"{NOT_FOUND_MESSAGE}"
Keep the answer short (1-3 sentences) and name the source document you used."""


def build_user_prompt(question, chunks):
    """Join the retrieved chunks into one context block, then add the question."""
    context_parts = []
    for i, chunk in enumerate(chunks, start=1):
        context_parts.append(f"[Chunk {i} | Source: {chunk['source']}]\n{chunk['text'].strip()}")
    context = "\n\n".join(context_parts)

    return f"CONTEXT:\n{context}\n\nQUESTION: {question}"


def _get_key(name):
    key = os.getenv(name, "").strip()
    if not key or key.startswith("paste-"):
        raise RuntimeError(
            f"{name} is missing. Open the .env file in your project folder and paste your API key."
        )
    return key


# ---------------- One small function per provider ----------------
def _ask_gemini(system_prompt, user_prompt):
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=_get_key("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model=config.AI_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(system_instruction=system_prompt),
    )
    return response.text


def _ask_openai(system_prompt, user_prompt):
    from openai import OpenAI

    client = OpenAI(api_key=_get_key("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=config.AI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


def _ask_anthropic(system_prompt, user_prompt):
    import anthropic

    client = anthropic.Anthropic(api_key=_get_key("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model=config.AI_MODEL,
        max_tokens=500,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return response.content[0].text


def _ask_openrouter(system_prompt, user_prompt):
    # OpenRouter speaks the same "language" as OpenAI, so we reuse the openai
    # library and only change the address (base_url) and the key.
    from openai import OpenAI

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=_get_key("OPENROUTER_API_KEY"),
    )
    response = client.chat.completions.create(
        model=config.AI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    answer = response.choices[0].message.content or ""
    # With "openrouter/free" a different model may answer each time, so show which one did.
    if response.model and response.model != config.AI_MODEL:
        answer += f"\n  (answered by: {response.model})"
    return answer


PROVIDERS = {
    "gemini": _ask_gemini,
    "openai": _ask_openai,
    "anthropic": _ask_anthropic,
    "openrouter": _ask_openrouter,
}


def ask_ai(question, chunks):
    """Main function used by Task 4: returns the AI's answer as text."""
    if config.AI_PROVIDER not in PROVIDERS:
        raise RuntimeError(
            f"Unknown AI_PROVIDER '{config.AI_PROVIDER}'. Use gemini, openai, anthropic or openrouter in .env"
        )
    user_prompt = build_user_prompt(question, chunks)
    answer = PROVIDERS[config.AI_PROVIDER](SYSTEM_PROMPT, user_prompt)
    return (answer or "").strip()
