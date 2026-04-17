import os
from dotenv import load_dotenv
from pathlib import Path

# Ensure local development reads variables from the repo `.env` reliably.
_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"  # Backend/hairify/.env

def TextInputAi(message, id):
    print("Loading .env from:", _ENV_PATH)
    print("GROQ key found:", bool(os.getenv("GROQ_API_KEY")))
    # Reload on each request so Django's reloader / env doesn't get stale.
    load_dotenv(dotenv_path=_ENV_PATH, override=True)
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        return ["Error: GROQ_API_KEY is missing. Put your Groq key in Backend/hairify/.env"]

    from groq import Groq

    client = Groq(api_key=groq_key)
    model = os.getenv("GROQ_MODEL") or "llama-3.1-8b-instant"

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are HairAlchemyAI, a cheerful assistant specializing in hair and scalp problems. "
                        "Give helpful, friendly advice in English only. Keep responses around 150 words."
                    ),
                },
                {"role": "user", "content": str(message or "")},
            ],
            temperature=0.7,
            max_tokens=250,
        )

        text = (completion.choices[0].message.content or "").strip()
        return [text or "Sorry, I couldn't generate a response."]

    except Exception as e:
        return [f"Error: {str(e)}"]