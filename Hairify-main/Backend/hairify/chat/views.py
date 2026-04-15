import os

from django.http import StreamingHttpResponse

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

from google import genai
import os

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

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
                def event_stream():
                    for chunk in a_response:
                        yield chunk

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
    return Response({"messages": []})  # ✅ removed LangChain


# -----------------------------
# DELETE HISTORY (TEMP FIX)
# -----------------------------
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def deleteHistory(request):
    return Response("History cleared")  # ✅ removed LangChain


# -----------------------------
# IMAGE ANALYSIS
# -----------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def imageInput(request):
    try:
        user_id = request.user.id
        image = request.FILES['image']

        upload_result = cloudinary.uploader.upload(image, folder="hairfall")
        picture_url = upload_result['secure_url']

        response = client.models.generate_content(
    model="gemini-1.5-flash",
    contents=[
        {
            "role": "user",
            "parts": [
                {"text": "Analyze this hair/scalp image. Identify possible issues and suggest solutions in a friendly tone."},
                {
                    "file_data": {
                        "mime_type": "image/jpeg",
                        "file_uri": picture_url
                    }
                }
            ]
        }
    ]
)

        result_text = response.text if response.text else "No analysis generated."

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
        print(e)
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