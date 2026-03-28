from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    # Keep flexible: allow username OR email-based login later
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(min_length=8, write_only=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    # Sprint 1 / MVP fields
    display_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    country = serializers.CharField(max_length=2, required=False, allow_blank=True)

    consent_accepted = serializers.BooleanField()

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Username is already taken.")
        return value

    def validate_email(self, value):
        if value and User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email is already registered.")
        return value

    def validate_consent_accepted(self, value):
        if value is not True:
            raise serializers.ValidationError("Consent must be accepted to register.")
        return value


    def create(self, validated_data):
        password = validated_data.pop("password")
        consent_accepted = validated_data.pop("consent_accepted", False)

        username = validated_data.get("username")
        email = validated_data.get("email", "")
        first_name = validated_data.pop("first_name", "")
        last_name = validated_data.pop("last_name", "")


        user = User.objects.create_user(username=username, email=email, password=password)
        user.first_name = first_name
        user.last_name = last_name

        # profile is created by your signals.py; update it
        profile = user.profile
        profile.display_name = validated_data.get("display_name", "")
        profile.country = validated_data.get("country", "")
        if consent_accepted:
            profile.accept_consent()
        profile.save()

        return user


class MeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField(allow_blank=True)
    first_name = serializers.CharField(allow_blank=True)
    last_name = serializers.CharField(allow_blank=True)

    profile = serializers.DictField()

    @staticmethod
    def from_user(user):
        p = getattr(user, "profile", None)
        if p is None:
            # create one if missing (rare)
            from apps.accounts.models import UserProfile
            p = UserProfile.objects.create(user=user)
        return {
            "id": user.id,
            "username": user.get_username(),
            "email": getattr(user, "email", "") or "",
            "first_name": getattr(user, "first_name", "") or "",
            "last_name": getattr(user, "last_name", "") or "",
            "profile": {
                "display_name": getattr(p, "display_name", "") if p else "",
                "country": getattr(p, "country", "") if p else "",
                "is_player": getattr(p, "is_player", True) if p else True,
                "is_club_admin": getattr(p, "is_club_admin", False) if p else False,
                "is_platform_admin": getattr(p, "is_platform_admin", False) if p else False,
                "consent_accepted": getattr(p, "consent_accepted", False) if p else False,
                "consent_accepted_at": (getattr(p, "consent_accepted_at", None).isoformat() if getattr(p, "consent_accepted_at", None) else None) if p else None,
            },
        }

class UpdateMeSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)

    display_name = serializers.CharField(required=False, allow_blank=True, max_length=120)
    country = serializers.CharField(required=False, allow_blank=True, max_length=2)

    def validate_country(self, value: str):
        v = (value or "").strip().upper()
        if v and len(v) != 2:
            raise serializers.ValidationError("Country must be a 2-letter code (e.g. GB).")
        return v

    def update(self, instance, validated_data):
        """
        instance is request.user
        """
        # --- User model fields ---
        if "email" in validated_data:
            instance.email = validated_data.get("email", "") or ""
        if "first_name" in validated_data:
            instance.first_name = validated_data.get("first_name", "") or ""
        if "last_name" in validated_data:
            instance.last_name = validated_data.get("last_name", "") or ""

        instance.save()

        # --- Profile fields ---
        profile = getattr(instance, "profile", None)
        if profile is not None:
            if "display_name" in validated_data:
                profile.display_name = validated_data.get("display_name", "") or ""
            if "country" in validated_data:
                profile.country = validated_data.get("country", "") or ""
            profile.save()

        return instance
