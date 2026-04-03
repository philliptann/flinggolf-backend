# backend/apps/scoring/views.py

from django.db.models import Prefetch, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, render,redirect
from django.utils import timezone
from django.views import View

from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

#from apps.courses.models import Course, TeeSet
from apps.scoring.models import HandicapHistory, Round, RoundHoleScore, RoundPlayer, Tournament
from apps.scoring.pagination import RoundPagination
from apps.scoring.permissions import IsRoundHoleScoreOwner, IsRoundOwner
from apps.scoring.serializers import (  HandicapHistorySerializer,  RoundCreateSerializer, RoundDetailMobileSerializer,
    RoundHoleScoreUpdateResponseSerializer, RoundHoleScoreUpdateSerializer, RoundListSerializer,
    TournamentCreateSerializer, TournamentJoinSerializer, TournamentSerializer,)
from apps.scoring.services.handicap import apply_handicap_updates_for_round
from apps.scoring.services.tournaments import (
    create_tournament_with_host_round,  get_tournament_leaderboard,
    join_tournament_and_create_round,)

from datetime import timedelta



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
        if action == "complete" and round_obj.is_qualifying and not round_obj.handicap_applied:
            apply_handicap_updates_for_round(round_obj)

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

class HandicapHistoryListView(generics.ListAPIView):
    serializer_class = HandicapHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return HandicapHistory.objects.filter(user=self.request.user).order_by(
            "-effective_date", "-created_at"
        )

class TournamentCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TournamentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        tournament, round_obj = create_tournament_with_host_round(
            user=request.user,
            tournament_name=data["name"],
            course=data["course"],
            tee_set=data["tee_set"],
            scoring_format=data["scoring_format"],
            date_played=data["date_played"],
            is_qualifying=data["is_qualifying"],
        )

        return Response({
            "tournament": TournamentSerializer(tournament).data,
            "round_id": round_obj.id,
        }, status=status.HTTP_201_CREATED)

class TournamentJoinView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TournamentJoinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            tournament, round_obj = join_tournament_and_create_round(
                user=request.user,
                join_code=serializer.validated_data["join_code"],
            )
        except Tournament.DoesNotExist:
            return Response({"detail": "Tournament not found."}, status=404)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)

        return Response({
            "tournament": TournamentSerializer(tournament).data,
            "round_id": round_obj.id,
        }, status=201)

class TournamentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        tournament = get_object_or_404(Tournament, pk=pk)

        if not (
            tournament.created_by_id == request.user.id
            or tournament.entries.filter(user=request.user).exists()
        ):
            raise PermissionDenied("You do not have access to this tournament.")

        return Response(TournamentSerializer(tournament).data)

class TournamentLeaderboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        tournament = get_object_or_404(Tournament, pk=pk)

        if not (
            tournament.created_by_id == request.user.id
            or tournament.entries.filter(user=request.user).exists()
        ):
            raise PermissionDenied("You do not have access to this tournament.")

        rows = get_tournament_leaderboard(tournament)
        return Response(rows)

class TournamentLandingPageView(View):
    MAX_ATTEMPTS = 10
    LOCKOUT_MINUTES = 2
    SESSION_ATTEMPTS_KEY = "tournament_lookup_attempts"
    SESSION_LOCKED_UNTIL_KEY = "tournament_lookup_locked_until"

    def get(self, request):
        locked_message = self._get_lock_message(request)
        error = request.session.pop("tournament_lookup_error", None)

        return render(
            request,
            "tournament_landing.html",
            {
                "error": error,
                "locked_message": locked_message,
            },
        )

    def post(self, request):
        locked_message = self._get_lock_message(request)
        if locked_message:
            return render(
                request,
                "tournament_landing.html",
                {
                    "locked_message": locked_message,
                },
            )

        join_code = (request.POST.get("join_code") or "").strip().lower()

        if not join_code:
            return render(request,"tournament_landing.html", {"error": "Please enter a tournament code.", }, )

        if Tournament.objects.filter(join_code=join_code).exists():
            self._reset_attempts(request)
            return redirect("tournament-public-root-page", join_code=join_code)

        attempts = request.session.get(self.SESSION_ATTEMPTS_KEY, 0) + 1
        request.session[self.SESSION_ATTEMPTS_KEY] = attempts

        if attempts >= self.MAX_ATTEMPTS:
            locked_until = timezone.now() + timedelta(minutes=self.LOCKOUT_MINUTES)
            request.session[self.SESSION_LOCKED_UNTIL_KEY] = locked_until.isoformat()
            request.session["tournament_lookup_error"] = (
                "Too many incorrect attempts. Please wait 2 minutes and try again."
            )
        else:
            remaining = self.MAX_ATTEMPTS - attempts
            request.session["tournament_lookup_error"] = (
                f"Incorrect tournament code. {remaining} attempt(s) remaining."
            )

        return redirect("tournament-landing-page")

    def _get_lock_message(self, request):
        locked_until_raw = request.session.get(self.SESSION_LOCKED_UNTIL_KEY)
        if not locked_until_raw:
            return None

        try:
            locked_until = timezone.datetime.fromisoformat(locked_until_raw)
            if timezone.is_naive(locked_until):
                locked_until = timezone.make_aware(locked_until, timezone.get_current_timezone())
        except Exception:
            self._reset_attempts(request)
            return None

        now = timezone.now()
        if now >= locked_until:
            self._reset_attempts(request)
            return None

        seconds_left = int((locked_until - now).total_seconds())
        minutes = seconds_left // 60
        seconds = seconds_left % 60
        return f"Too many incorrect attempts. Try again in {minutes}:{seconds:02d}."

    def _reset_attempts(self, request):
        request.session.pop(self.SESSION_ATTEMPTS_KEY, None)
        request.session.pop(self.SESSION_LOCKED_UNTIL_KEY, None)


class TournamentPublicPageView(View):
    def get(self, request, join_code):
        tournament = Tournament.objects.filter(join_code=join_code.lower()).first()

        if not tournament:
            request.session["tournament_lookup_error"] = "Incorrect tournament code."
            return redirect("tournament-landing-page")

        leaderboard = get_tournament_leaderboard(tournament)

        rows = []
        for index, row in enumerate(leaderboard, start=1):
            rows.append(
                {
                    "position": index,
                    "round_status_label": str(row.get("round_status", "")).replace("_", " ").title(),
                    **row,
                }
            )

        return render(
            request,
            "tournament_public.html",
            {
                "tournament": tournament,
                "leaderboard": rows,
            },
        )