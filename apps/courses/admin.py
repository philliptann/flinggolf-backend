# backend/apps/courses/admin.py
from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import Club, Course, Hole, TeeSet, TeeSetHole

admin.site.site_header = "FlingGolf Admin"
admin.site.site_title = "FlingGolf Admin Portal"
admin.site.index_title = "Welcome to FlingGolf Administration"


class ClubResource(resources.ModelResource):
    class Meta:
        model = Club
        import_id_fields = ("name", "postcode")
        skip_unchanged = True
        report_skipped = True


class CourseResource(resources.ModelResource):
    class Meta:
        model = Course
        import_id_fields = ("club", "name")
        skip_unchanged = True
        report_skipped = True


class HoleInline(admin.TabularInline):
    model = Hole
    extra = 0
    ordering = ("hole_number",)


class TeeSetInline(admin.TabularInline):
    model = TeeSet
    extra = 0


class TeeSetHoleInline(admin.TabularInline):
    model = TeeSetHole
    extra = 0
    ordering = ("hole__hole_number",)


@admin.register(Club)
class ClubAdmin(ImportExportModelAdmin):
    resource_class = ClubResource
    list_display = ("name", "city", "region", "postcode", "country", "is_active")
    list_filter = ("country", "is_active")
    search_fields = ("name", "city", "region", "postcode")
    skip_admin_log = True


@admin.register(Course)
class CourseAdmin(ImportExportModelAdmin):
    resource_class = CourseResource
    list_display = ("name", "club", "holes", "par_total", "is_active")
    list_filter = ("club", "is_active", "holes")
    search_fields = ("name", "club__name")
    inlines = [HoleInline, TeeSetInline]
    skip_admin_log = True


@admin.register(Hole)
class HoleAdmin(admin.ModelAdmin):
    list_display = ("course", "hole_number", "default_par", "default_stroke_index")
    list_filter = ("course",)
    search_fields = ("course__name", "course__club__name")
    ordering = ("course", "hole_number")


@admin.register(TeeSet)
class TeeSetAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "course",
        "colour",
        "gender_category",
        "par_total",
        "course_rating",
        "slope_rating",
        "sss_value",
        "is_active",
    )
    list_filter = ("colour", "gender_category", "is_active", "course")
    search_fields = ("name", "course__name", "course__club__name")
    inlines = [TeeSetHoleInline]


@admin.register(TeeSetHole)
class TeeSetHoleAdmin(admin.ModelAdmin):
    list_display = ("tee_set", "hole", "yardage", "par", "stroke_index")
    list_filter = ("tee_set", "tee_set__course")
    search_fields = (
        "tee_set__name",
        "tee_set__course__name",
        "tee_set__course__club__name",
    )
    ordering = ("tee_set", "hole__hole_number")