#backend/apps/courses/models.py
from django.db import models


class Club(models.Model):
    name = models.CharField(max_length=200)
    city = models.CharField(max_length=120, blank=True)
    region = models.CharField(max_length=120, blank=True)
    country = models.CharField(
        max_length=2,
        blank=True,
        help_text="ISO 3166-1 alpha-2, e.g. GB, IE",
    )
    address = models.TextField(blank=True)
    postcode = models.CharField(max_length=12, blank=True)
    external_booking_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["country", "name"]

    def __str__(self) -> str:
        return self.name


class Course(models.Model):
    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,
        related_name="courses",
    )
    name = models.CharField(max_length=200)
    holes = models.PositiveSmallIntegerField(default=18)
    par_total = models.PositiveSmallIntegerField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["club__name", "name"]
        unique_together = [("club", "name")]

    def __str__(self) -> str:
        return f"{self.club.name} - {self.name}"


class Hole(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="holes_data",
    )
    hole_number = models.PositiveSmallIntegerField()
    default_par = models.PositiveSmallIntegerField()
    default_stroke_index = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["course", "hole_number"]
        unique_together = [("course", "hole_number")]

    def __str__(self) -> str:
        return f"{self.course} Hole {self.hole_number}"


class TeeSet(models.Model):
    COLOUR_WHITE = "white"
    COLOUR_YELLOW = "yellow"
    COLOUR_RED = "red"
    COLOUR_BLUE = "blue"
    COLOUR_BLACK = "black"

    TEE_COLOUR_CHOICES = [
        (COLOUR_WHITE, "White"),
        (COLOUR_YELLOW, "Yellow"),
        (COLOUR_RED, "Red"),
        (COLOUR_BLUE, "Blue"),
        (COLOUR_BLACK, "Black"),
    ]

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="tee_sets",
    )
    name = models.CharField(max_length=100)
    colour = models.CharField(max_length=20, choices=TEE_COLOUR_CHOICES)
    gender_category = models.CharField(max_length=20, blank=True)

    par_total = models.PositiveSmallIntegerField(blank=True, null=True)
    course_rating = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    slope_rating = models.PositiveSmallIntegerField(blank=True, null=True)
    sss_value = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["course", "name"]
        unique_together = [("course", "name"), ("course", "colour")]

    def __str__(self) -> str:
        return f"{self.course} - {self.name}"


class TeeSetHole(models.Model):
    tee_set = models.ForeignKey(
        TeeSet,
        on_delete=models.CASCADE,
        related_name="hole_data",
    )
    hole = models.ForeignKey(
        Hole,
        on_delete=models.CASCADE,
        related_name="tee_overrides",
    )
    yardage = models.PositiveSmallIntegerField()
    par = models.PositiveSmallIntegerField(blank=True, null=True)
    stroke_index = models.PositiveSmallIntegerField(blank=True, null=True)

    class Meta:
        ordering = ["tee_set", "hole__hole_number"]
        unique_together = [("tee_set", "hole")]

    def __str__(self) -> str:
        return f"{self.tee_set} - Hole {self.hole.hole_number}"