# backend/apps/scoring/admin.py

from django.contrib import admin

from apps.scoring.models import Round, RoundPlayer, RoundHoleScore, HandicapHistory


class RoundHoleScoreInline(admin.TabularInline):
    model = RoundHoleScore
    extra = 0


class RoundPlayerInline(admin.TabularInline):
    model = RoundPlayer
    extra = 0


@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "date_played",
        "course_name_snapshot",
        "tee_set_name_snapshot",
        "status",
        "scoring_format",
        "created_by",
    )
    list_filter = ("status", "scoring_format", "date_played")
    search_fields = ("name", "course_name_snapshot", "club_name_snapshot")
    inlines = [RoundPlayerInline]


@admin.register(RoundPlayer)
class RoundPlayerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "display_name",
        "round",
        "player_order",
        "handicap_index_snapshot",
        "playing_handicap_snapshot",
        "gross_total",
        "stableford_total",
    )
    list_filter = ("is_primary_player",)
    search_fields = ("display_name",)
    inlines = [RoundHoleScoreInline]


@admin.register(RoundHoleScore)
class RoundHoleScoreAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "round_player",
        "hole_number",
        "strokes",
        "net_strokes",
        "stableford_points",
        "is_complete",
    )
    list_filter = ("is_complete",)
    search_fields = ("round_player__display_name",)


@admin.register(HandicapHistory)
class HandicapHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "handicap_index", "effective_date", "source")
    list_filter = ("effective_date", "source")
    search_fields = ("user__username", "user__email")