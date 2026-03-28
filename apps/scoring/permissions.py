#backend/apps/scoring/permissions.py

from rest_framework.permissions import BasePermission


class IsRoundOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.created_by == request.user


class IsRoundHoleScoreOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.round_player.round.created_by == request.user
    