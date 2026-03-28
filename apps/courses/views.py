# backend/apps/courses/views.py
from django.db.models import Prefetch
from rest_framework import generics

from .models import Course, Hole, TeeSet, TeeSetHole
from .serializers import CourseListSerializer, CourseDetailSerializer


class CourseListView(generics.ListAPIView):
    serializer_class = CourseListSerializer

    def get_queryset(self):
        return (
            Course.objects.filter(is_active=True, club__is_active=True)
            .select_related("club")
            .order_by("club__country", "club__name", "name")
        )


class CourseDetailView(generics.RetrieveAPIView):
    serializer_class = CourseDetailSerializer
    lookup_field = "id"

    def get_queryset(self):
        return (
            Course.objects.filter(is_active=True, club__is_active=True)
            .select_related("club")
            .prefetch_related(
                Prefetch(
                    "holes_data",
                    queryset=Hole.objects.order_by("hole_number"),
                ),
                Prefetch(
                    "tee_sets",
                    queryset=TeeSet.objects.filter(is_active=True).prefetch_related(
                        Prefetch(
                            "hole_data",
                            queryset=TeeSetHole.objects.select_related("hole").order_by("hole__hole_number"),
                        )
                    ).order_by("name"),
                ),
            )
        )