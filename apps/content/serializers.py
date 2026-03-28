from rest_framework import serializers
from .models import Page, RuleSection


class PageListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = ["id", "title", "slug", "updated_at"]


class PageDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = ["id", "title", "slug", "body", "updated_at"]


class RuleSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuleSection
        fields = ["id", "order", "title", "body", "updated_at"]
