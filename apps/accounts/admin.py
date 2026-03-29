# backend/apps/accounts/admin.py
from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import UserProfile

User = get_user_model()


class UserAdminForm(forms.ModelForm):
    display_name = forms.CharField(max_length=120, required=True)
    country = forms.CharField(max_length=2, required=False)

    class Meta:
        model = User
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        profile = getattr(self.instance, "profile", None)
        if profile:
            self.fields["display_name"].initial = profile.display_name
            self.fields["country"].initial = profile.country

    def save(self, commit=True):
        user = super().save(commit=commit)

        profile = getattr(user, "profile", None)
        if profile is not None:
            profile.display_name = self.cleaned_data["display_name"]
            profile.country = self.cleaned_data.get("country", "")
            profile.save()

        return user


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "display_name",
        "country",
        "is_player",
        "is_club_admin",
        "is_platform_admin",
        "consent_accepted",
    )
    list_filter = (
        "country",
        "is_player",
        "is_club_admin",
        "is_platform_admin",
        "consent_accepted",
    )
    search_fields = ("user__email", "user__username", "display_name")


try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    form = UserAdminForm

    list_display = DjangoUserAdmin.list_display + ("get_display_name",)
    search_fields = DjangoUserAdmin.search_fields + ("profile__display_name",)

    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            "Profile",
            {
                "fields": ("display_name", "country"),
            },
        ),
    )

    def get_display_name(self, obj):
        return getattr(getattr(obj, "profile", None), "display_name", "")

    get_display_name.short_description = "Display name"