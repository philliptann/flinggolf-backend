# backend/apps/courses/serializers.py
from rest_framework import serializers
from .models import Club, Course, Hole, TeeSet, TeeSetHole


# ---------------------------
# Basic / Nested Serializers
# ---------------------------

class ClubSerializer(serializers.ModelSerializer):
    class Meta:
        model = Club
        fields = ["id","name", "city","region","country","postcode", ]


class HoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hole
        fields = ["id","hole_number","default_par","default_stroke_index",]


class TeeSetHoleSerializer(serializers.ModelSerializer):
    hole_number = serializers.IntegerField(source="hole.hole_number")

    class Meta:
        model = TeeSetHole
        fields = [ "id","hole_number", "yardage", "par","stroke_index",]


class TeeSetSerializer(serializers.ModelSerializer):
    tee_holes = TeeSetHoleSerializer(source="hole_data",many=True, read_only=True)

    class Meta:
        model = TeeSet
        fields = [ "id","name","colour","gender_category", "par_total","course_rating", "slope_rating","sss_value","tee_holes", ]


# ---------------------------
# Main Serializers
# ---------------------------

class CourseListSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)
    city = serializers.CharField(source="club.city", read_only=True)
    region = serializers.CharField(source="club.region", read_only=True)
    country = serializers.CharField(source="club.country", read_only=True)
    postcode = serializers.CharField(source="club.postcode", read_only=True)
    external_booking_url = serializers.CharField(source="club.external_booking_url",read_only=True,allow_null=True,)
    
    class Meta:
        model = Course
        fields = [
            "id",
            "name",
            "club_name",
            "holes",
            "par_total",
            "city",
            "region",
            "country",
            "postcode",
            "external_booking_url",
        ]


class CourseDetailSerializer(serializers.ModelSerializer):
    club = ClubSerializer(read_only=True)
    course_holes = HoleSerializer(source="holes_data", many=True, read_only=True)
    tee_sets = TeeSetSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = [ "id", "name", "club","course_holes","tee_sets", "holes","par_total","created_at", "updated_at",]
