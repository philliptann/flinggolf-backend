#flinggolf/backend/apps/core/views.py
from django.db import connections
from django.db.utils import OperationalError
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import render

class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        # DB connectivity check
        db_ok = True
        db_error = None
        try:
            connections["default"].cursor()
        except OperationalError as exc:
            db_ok = False
            db_error = str(exc)

        payload = {
            "status": "ok" if db_ok else "degraded",
            "db": {"ok": db_ok, "error": db_error},
        }
        return Response(payload, status=200 if db_ok else 503)

def index(request):
    return render(request, "index.html")