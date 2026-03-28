from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import Page, RuleSection
from .serializers import PageListSerializer, PageDetailSerializer, RuleSectionSerializer


class PageListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = PageListSerializer

    def get_queryset(self):
        return Page.objects.filter(is_published=True).order_by("title")


class PageDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = PageDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return Page.objects.filter(is_published=True)


class RuleSectionListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = RuleSectionSerializer

    def get_queryset(self):
        return RuleSection.objects.filter(is_published=True).order_by("order", "title")
