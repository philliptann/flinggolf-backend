# backend/apps/scoring/views.py

from django.db.models import Prefetch, Q
from django.utils import timezone
from rest_framework import generics, status, permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import Http404

from apps.scoring.models import Round, RoundHoleScore, RoundPlayer
from apps.scoring.pagination import RoundPagination
from apps.scoring.permissions import IsRoundOwner, IsRoundHoleScoreOwner

from apps.scoring.serializers import (
    RoundCreateSerializer,
    RoundDetailSerializer,
    RoundDetailMobileSerializer,
    RoundHoleScoreSerializer,
    RoundHoleScoreUpdateSerializer,
    RoundHoleScoreUpdateResponseSerializer,
    RoundListSerializer,
)


class RoundListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = RoundPagination

    def get_queryset(self):
        queryset = (
            Round.objects.filter(created_by=self.request.user)
            .prefetch_related(
                Prefetch(
                    "players",
                    queryset=RoundPlayer.objects.prefetch_related(
                        Prefetch(
                            "hole_scores",
                            queryset=RoundHoleScore.objects.order_by("hole_number"),
                        )
                    ).order_by("player_order"),
                )
            )
            .order_by("-date_played", "-created_at")
        )

        status_value = self.request.query_params.get("status")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        recent_only = self.request.query_params.get("recent")
        search_value = self.request.query_params.get("search")
        ordering_value = self.request.query_params.get("ordering")

        if status_value:
            allowed_statuses = {
                Round.STATUS_DRAFT,
                Round.STATUS_IN_PROGRESS,
                Round.STATUS_COMPLETED,
                Round.STATUS_CANCELLED,
            }
            requested_statuses = [s.strip() for s in status_value.split(",") if s.strip()]
            invalid_statuses = [s for s in requested_statuses if s not in allowed_statuses]

            if invalid_statuses:
                raise ValidationError(
                    {
                        "status": (
                            "Invalid status. Use draft, in_progress, completed, "
                            "or cancelled. Multiple values may be comma-separated."
                        )
                    }
                )

            queryset = queryset.filter(status__in=requested_statuses)

        if date_from:
            queryset = queryset.filter(date_played__gte=date_from)

        if date_to:
            queryset = queryset.filter(date_played__lte=date_to)

        if search_value:
            queryset = queryset.filter(
                Q(name__icontains=search_value)
                | Q(course_name_snapshot__icontains=search_value)
                | Q(tee_set_name_snapshot__icontains=search_value)
                | Q(club_name_snapshot__icontains=search_value)
            )

        allowed_ordering = {
            "date_played",
            "-date_played",
            "created_at",
            "-created_at",
            "name",
            "-name",
            "status",
            "-status",
        }

        if ordering_value:
            ordering_fields = [
                field.strip()
                for field in ordering_value.split(",")
                if field.strip() in allowed_ordering
            ]
            if ordering_fields:
                queryset = queryset.order_by(*ordering_fields)

        if recent_only in {"1", "true", "True"}:
            queryset = queryset[:10]

        return queryset

    def get_serializer_class(self):
        if self.request.method == "POST":
            return RoundCreateSerializer
        return RoundListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        round_obj = serializer.save()

        round_obj = (
            Round.objects.filter(pk=round_obj.pk, created_by=request.user)
            .prefetch_related(
                Prefetch(
                    "players",
                    queryset=RoundPlayer.objects.prefetch_related(
                        Prefetch(
                            "hole_scores",
                            queryset=RoundHoleScore.objects.order_by("hole_number"),
                        )
                    ).order_by("player_order"),
                )
            )
            .get()
        )

        response_serializer = RoundDetailMobileSerializer(
            round_obj,
            context={"request": request},
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class RoundDetailView(generics.RetrieveAPIView):
    serializer_class = RoundDetailMobileSerializer
    permission_classes = [permissions.IsAuthenticated, IsRoundOwner]

    def get_queryset(self):
        return (
            Round.objects.filter(created_by=self.request.user)
            .prefetch_related(
                Prefetch(
                    "players",
                    queryset=RoundPlayer.objects.prefetch_related(
                        Prefetch(
                            "hole_scores",
                            queryset=RoundHoleScore.objects.order_by("hole_number"),
                        )
                    ).order_by("player_order"),
                )
            )
        )


class RoundHoleScoreUpdateView(generics.UpdateAPIView):
    serializer_class = RoundHoleScoreUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsRoundHoleScoreOwner]
    http_method_names = ["patch", "put"]

    def get_queryset(self):
        return (
            RoundHoleScore.objects.filter(
                round_player__round__created_by=self.request.user
            ).select_related("round_player", "round_player__round")
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", True)
        instance = self.get_object()

        round_obj = instance.round_player.round
        if round_obj.status in [Round.STATUS_COMPLETED, Round.STATUS_CANCELLED]:
            raise PermissionDenied("Scores cannot be edited for completed or cancelled rounds.")

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated_score = serializer.save()

        updated_score = (
            RoundHoleScore.objects.select_related("round_player", "round_player__round")
            .get(pk=updated_score.pk)
        )

        round_player = updated_score.round_player
        round_obj = round_player.round

        round_obj = (
            Round.objects.filter(pk=round_obj.pk, created_by=request.user)
            .prefetch_related(
                Prefetch(
                    "players",
                    queryset=RoundPlayer.objects.prefetch_related(
                        Prefetch(
                            "hole_scores",
                            queryset=RoundHoleScore.objects.order_by("hole_number"),
                        )
                    ).order_by("player_order"),
                )
            )
            .get()
        )

        round_player = next(
            player for player in round_obj.players.all()
            if player.id == updated_score.round_player_id
        )

        response_payload = {
            "score": updated_score,
            "player_totals": round_player,
            "round_summary": round_obj,
        }

        response_serializer = RoundHoleScoreUpdateResponseSerializer(
            response_payload,
            context={"request": request},
        )
        return Response(response_serializer.data)


class RoundStatusActionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, action):
        try:
            round_obj = Round.objects.get(pk=pk, created_by=request.user)
        except Round.DoesNotExist:
            raise Http404("Round not found.")

        now = timezone.now()

        if action == "start":
            if round_obj.status != Round.STATUS_DRAFT:
                raise ValidationError("Only draft rounds can be started.")
            round_obj.status = Round.STATUS_IN_PROGRESS
            if not round_obj.started_at:
                round_obj.started_at = now

        elif action == "complete":
            if round_obj.status != Round.STATUS_IN_PROGRESS:
                raise ValidationError("Only in-progress rounds can be completed.")
            round_obj.status = Round.STATUS_COMPLETED
            if not round_obj.started_at:
                round_obj.started_at = now
            round_obj.completed_at = now

        elif action == "cancel":
            if round_obj.status not in [Round.STATUS_DRAFT, Round.STATUS_IN_PROGRESS]:
                raise ValidationError("Only draft or in-progress rounds can be cancelled.")
            round_obj.status = Round.STATUS_CANCELLED
            round_obj.cancelled_at = now

        else:
            raise ValidationError("Invalid action.")

        round_obj.save(
            update_fields=[
                "status",
                "started_at",
                "completed_at",
                "cancelled_at",
                "updated_at",
            ]
        )

        round_obj = (
            Round.objects.filter(pk=round_obj.pk, created_by=request.user)
            .prefetch_related(
                Prefetch(
                    "players",
                    queryset=RoundPlayer.objects.prefetch_related(
                        Prefetch(
                            "hole_scores",
                            queryset=RoundHoleScore.objects.order_by("hole_number"),
                        )
                    ).order_by("player_order"),
                )
            )
            .get()
        )

        response_serializer = RoundDetailMobileSerializer(
            round_obj,
            context={"request": request},
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)