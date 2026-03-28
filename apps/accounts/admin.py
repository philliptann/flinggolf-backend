from django.contrib import admin
from .models import UserProfile
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "country", "is_player", "is_club_admin", "is_platform_admin", "consent_accepted")
    list_filter = ("country", "is_player", "is_club_admin", "is_platform_admin", "consent_accepted")
    search_fields = ("user__email", "user__username", "display_name")


User = get_user_model()

# Unregister the default User admin (only if it’s already registered)
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    # Append display name to the default columns
    list_display = DjangoUserAdmin.list_display + ("get_display_name",)

    # Optional: make it searchable via username/email as usual
    search_fields = DjangoUserAdmin.search_fields + ("profile__display_name",)

    def get_display_name(self, obj):
        # Safe if profile exists via signals; fallback prevents admin errors
        return getattr(getattr(obj, "profile", None), "display_name", "")
    get_display_name.short_description = "Display name"
