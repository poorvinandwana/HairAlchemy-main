from django.http import StreamingHttpResponse
import os
import requests as req
import base64
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from django.views.decorators.csrf import csrf_exempt

import cloudinary
import cloudinary.uploader

from .utils import TextInputAi
from .models import report
from .serializers import ReportSerializer

from dotenv import load_dotenv
from pathlib import Path

_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)


# -----------------------------
# OPENROUTER IMAGE ANALYSIS
# -----------------------------
def analyze_image_with_openrouter(image_url: str) -> str:
    """
    Sends an image URL to OpenRouter for hair/scalp analysis.
    Text prompt comes BEFORE image (required by OpenRouter).
    Falls back through multiple free vision models.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is missing from .env")

    # Updated free vision model IDs (April 2026)
    # "openrouter/auto" as last resort: OpenRouter picks the best available free model
    model_candidates = [
        "qwen/qwen2.5-vl-32b-instruct:free",
        "mistralai/mistral-small-3.1-24b-instruct:free",
        "moonshotai/kimi-vl-a3b-thinking:free",
        "openrouter/auto",
    ]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://hairify.app",
        "X-Title": "Hairify",
    }

    # IMPORTANT: text must come BEFORE image_url in the content array
    prompt_text = (
        "Analyze this hair and scalp image carefully. "
        "Identify any visible issues such as hair thinning, "
        "dandruff, scalp irritation, or other concerns. "
        "Provide friendly, actionable suggestions and recommendations. "
        "Keep the tone supportive and helpful."
    )

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt_text,
                },
                {
                    "type": "image_url",
                    "image_url": {"url": image_url},
                },
            ],
        }
    ]

    last_err = None
    for model in model_candidates:
        try:
            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": 1024,
            }
            response = req.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )

            # Log the raw error body for easier debugging
            if not response.ok:
                print(f"[OpenRouter] Model {model} HTTP {response.status_code}: {response.text[:300]}")
                response.raise_for_status()

            data = response.json()
            result = data["choices"][0]["message"]["content"]
            print(f"[OpenRouter] Success with model: {model}")
            return result

        except Exception as e:
            print(f"[OpenRouter] Model {model} failed: {e}")
            last_err = e

    raise last_err or RuntimeError("All OpenRouter models failed")


# -----------------------------
# AUTH TEST
# -----------------------------
class Hi(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        return Response("YOLO")


# -----------------------------
# CHAT (TEXT)
# -----------------------------
class ChatView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        try:
            user = request.user
            message = request.data.get('message')

            print("User:", user.id)
            print("Message:", message)

            a_response = TextInputAi(message, str(user.id))

            if a_response:
                return Response(a_response[0])

            return Response("Invalid data", status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print("Error:", e)
            return Response("Failed", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# -----------------------------
# SIMPLE AUTH TEST
# -----------------------------
@api_view(['POST'])
@csrf_exempt
@permission_classes([IsAuthenticated])
def hi(request):
    return Response("yes " + str(request.user.id))


# -----------------------------
# CHAT HISTORY (TEMP FIX)
# -----------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def historyMessages(request):
    return Response({"messages": []})


# -----------------------------
# DELETE HISTORY (TEMP FIX)
# -----------------------------
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def deleteHistory(request):
    return Response("History cleared")


# -----------------------------
# IMAGE ANALYSIS
# -----------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def imageInput(request):
    try:
        user_id = request.user.id
        image = request.FILES.get('image')

        if not image:
            return Response("No image provided", status=status.HTTP_400_BAD_REQUEST)

        # Upload to Cloudinary
        upload_result = cloudinary.uploader.upload(image, folder="hairfall")
        picture_url = upload_result['secure_url']
        print(f"[Cloudinary] Uploaded: {picture_url}")

        # Analyze with OpenRouter
        result_text = analyze_image_with_openrouter(picture_url)

        # Save report to DB
        report.objects.create(
            user_id=user_id,
            image_url=picture_url,
            report=result_text
        )

        return Response({
            "img": picture_url,
            "analysis": result_text
        })

    except Exception as e:
        print(f"[imageInput] Error: {e}")
        return Response("Failed", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# -----------------------------
# GET REPORTS
# -----------------------------
class GetReport(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        try:
            user_id = request.user.id
            reports = report.objects.filter(user_id=user_id)
            serialized = ReportSerializer(reports, many=True)
            return Response(serialized.data)

        except Exception as e:
            print(e)
            return Response("Failed", status=status.HTTP_500_INTERNAL_SERVER_ERROR)