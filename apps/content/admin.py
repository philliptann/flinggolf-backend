from django.contrib import admin
from .models import Page, RuleSection


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_published", "updated_at")
    list_filter = ("is_published",)
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(RuleSection)
class RuleSectionAdmin(admin.ModelAdmin):
    list_display = ("order", "title", "is_published", "updated_at")
    list_filter = ("is_published",)
    search_fields = ("title",)
    ordering = ("order",)
