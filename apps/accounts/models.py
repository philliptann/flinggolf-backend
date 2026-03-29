# backend/apps/accounts/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone


class UserProfile(models.Model):
    """
    Sprint 1: keep Django's default User, add a 1:1 profile for:
    - role flags (player/admin)
    - country
    - GDPR consent + timestamp
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    # Basic profile
    display_name = models.CharField(max_length=120)
    country = models.CharField(max_length=2, blank=True, help_text="ISO 3166-1 alpha-2, e.g. GB, IE")

    # Roles (simple MVP approach)
    is_player = models.BooleanField(default=True)
    is_club_admin = models.BooleanField(default=False)
    is_platform_admin = models.BooleanField(default=False)

    # GDPR / compliance
    consent_accepted = models.BooleanField(default=False)
    consent_accepted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def accept_consent(self):
        """Convenience method for when you wire up registration."""
        self.consent_accepted = True
        self.consent_accepted_at = timezone.now()

    def __str__(self) -> str:
        return f"Profile<{self.user_id}>"
