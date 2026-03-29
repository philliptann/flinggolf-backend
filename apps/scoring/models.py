# backend/apps/scoring/models.py

from django.conf import settings
from django.db import models

from apps.courses.models import Course, TeeSet

User = settings.AUTH_USER_MODEL


class Round(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    SCORING_STROKEPLAY = "strokeplay"
    SCORING_STABLEFORD = "stableford"
    SCORING_MATCHPLAY = "matchplay"

    SCORING_FORMAT_CHOICES = [
        (SCORING_STROKEPLAY, "Strokeplay"),
        (SCORING_STABLEFORD, "Stableford"),
        (SCORING_MATCHPLAY, "Matchplay"),
    ]

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_rounds",
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name="rounds",
    )
    tee_set = models.ForeignKey(
        TeeSet,
        on_delete=models.PROTECT,
        related_name="rounds",
    )

    name = models.CharField(max_length=200, blank=True)
    date_played = models.DateField()
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )
    scoring_format = models.CharField(
        max_length=20,
        choices=SCORING_FORMAT_CHOICES,
        default=SCORING_STABLEFORD,
    )

    # Snapshot key round metadata at round creation
    course_name_snapshot = models.CharField(max_length=200)
    club_name_snapshot = models.CharField(max_length=200, blank=True)
    tee_set_name_snapshot = models.CharField(max_length=100)
    tee_set_colour_snapshot = models.CharField(max_length=20, blank=True)

    course_par_total_snapshot = models.PositiveSmallIntegerField(null=True, blank=True)
    tee_par_total_snapshot = models.PositiveSmallIntegerField(null=True, blank=True)
    course_rating_snapshot = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    slope_rating_snapshot = models.PositiveSmallIntegerField(null=True, blank=True)
    sss_value_snapshot = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)

    holes_count_snapshot = models.PositiveSmallIntegerField(default=18)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    is_qualifying = models.BooleanField(default=False)
    handicap_applied = models.BooleanField(default=False)

    class Meta:
        ordering = ["-date_played", "-created_at"]

    def __str__(self):
        return self.name or f"{self.course_name_snapshot} - {self.date_played}"


class RoundPlayer(models.Model):
    round = models.ForeignKey(
        Round,
        on_delete=models.CASCADE,
        related_name="players",
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="round_players",
    )

    display_name = models.CharField(max_length=120)

    player_order = models.PositiveSmallIntegerField(default=1)
    is_primary_player = models.BooleanField(default=False)

    # Handicap snapshot at start of round
    handicap_index_snapshot = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    course_handicap_snapshot = models.IntegerField(null=True, blank=True)
    playing_handicap_snapshot = models.IntegerField(null=True, blank=True)

    # Optional round summary cache fields
    gross_total = models.PositiveSmallIntegerField(null=True, blank=True)
    net_total = models.PositiveSmallIntegerField(null=True, blank=True)
    stableford_total = models.PositiveSmallIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["round", "player_order"]
        unique_together = [("round", "player_order")]

    def __str__(self):
        return f"{self.display_name} - {self.round}"


class RoundHoleScore(models.Model):
    round_player = models.ForeignKey(
        RoundPlayer,
        on_delete=models.CASCADE,
        related_name="hole_scores",
    )

    hole_number = models.PositiveSmallIntegerField()

    # Snapshot hole data from selected tee at round start
    yardage_snapshot = models.PositiveSmallIntegerField(null=True, blank=True)
    par_snapshot = models.PositiveSmallIntegerField()
    stroke_index_snapshot = models.PositiveSmallIntegerField()

    strokes = models.PositiveSmallIntegerField(null=True, blank=True)
    adjusted_strokes = models.PositiveSmallIntegerField(null=True, blank=True)

    handicap_strokes_received = models.PositiveSmallIntegerField(default=0)

    gross_to_par = models.SmallIntegerField(null=True, blank=True)
    net_strokes = models.PositiveSmallIntegerField(null=True, blank=True)
    net_to_par = models.SmallIntegerField(null=True, blank=True)
    stableford_points = models.PositiveSmallIntegerField(null=True, blank=True)

    is_complete = models.BooleanField(default=False)
    notes = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["round_player", "hole_number"]
        unique_together = [("round_player", "hole_number")]

    def __str__(self):
        return f"{self.round_player.display_name} - Hole {self.hole_number}"


class HandicapHistory(models.Model):
    ADJUSTMENT_DECREASE = "decrease"
    ADJUSTMENT_NO_CHANGE = "no_change"
    ADJUSTMENT_INCREASE = "increase"

    ADJUSTMENT_TYPE_CHOICES = [
        (ADJUSTMENT_DECREASE, "Decrease"),
        (ADJUSTMENT_NO_CHANGE, "No Change"),
        (ADJUSTMENT_INCREASE, "Increase"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="handicap_history",
    )

    source_round = models.ForeignKey(
        Round,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="handicap_updates",
    )

    old_exact_handicap = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    new_exact_handicap = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    playing_handicap_used = models.IntegerField(null=True, blank=True)
    gross_score = models.IntegerField(null=True, blank=True)
    net_score = models.IntegerField(null=True, blank=True)
    target_score = models.IntegerField(null=True, blank=True)
    buffer_zone_used = models.IntegerField(default=2)
    nett_differential = models.IntegerField(null=True, blank=True)

    adjustment_value = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    adjustment_type = models.CharField(
        max_length=20,
        choices=ADJUSTMENT_TYPE_CHOICES,
        null=True,
        blank=True,
    )

    is_qualifying = models.BooleanField(default=True)
    rule_version = models.CharField(max_length=50, default="legacy_v1")

    handicap_index = models.DecimalField(max_digits=5, decimal_places=2)
    effective_date = models.DateField()



    source = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["user", "-effective_date", "-created_at"]

    def __str__(self):
        return f"{self.user} - {self.handicap_index} ({self.effective_date})"
