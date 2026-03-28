# backend/apps/accounts/views.py
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView


from .serializers import RegisterSerializer, MeSerializer,UpdateMeSerializer


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        ser = RegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.save()
        return Response({"status": "created", "user_id": user.id}, status=status.HTTP_201_CREATED)


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(MeSerializer.from_user(request.user))

    def patch(self, request):
        ser = UpdateMeSerializer(instance=request.user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        user = ser.save()
        return Response(MeSerializer.from_user(user), status=status.HTTP_200_OK)

