import os
from google import genai

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def TextInputAi(message, id):
    print("USING NEW GEMINI SDK")
    prompt = f"""
You are HairifyAI, a cheerful AI assistant specializing in hair and scalp problems.
Give helpful, friendly advice in English only.
Keep responses around 150 words.

User: {message}
"""

    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )

        # ✅ SAFE extraction
        if hasattr(response, "text") and response.text:
            return [response.text]
        else:
            return ["Sorry, I couldn't generate a response."]

    except Exception as e:
        return [f"Error: {str(e)}"]