from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole

from .serializers import AdminIntelligenceQuerySerializer
from .services import answer_question, question_suggestions


class AdminIntelligenceQueryView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request):
        serializer = AdminIntelligenceQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(answer_question(serializer.validated_data["question"]))


class AdminIntelligenceSuggestionsView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        query = request.query_params.get("q", "")
        return Response({"suggestions": question_suggestions(query)})
