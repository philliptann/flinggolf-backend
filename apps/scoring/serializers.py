# backend/apps/scoring/serializers.py
from decimal import Decimal
from rest_framework import serializers

from apps.courses.models import Course, TeeSet
from apps.scoring.services.scoring import ( PlayerInput, create_round_with_players,  update_hole_score,)
from apps.scoring.models import Round, RoundHoleScore, RoundPlayer, HandicapHistory, Tournament

class RoundSummaryMixin:
    def _players(self, obj):
        return list(obj.players.all())

    def _hole_scores(self, obj):
        scores = []
        for player in self._players(obj):
            scores.extend(list(player.hole_scores.all()))
        return scores

    def get_players_count(self, obj):
        return len(self._players(obj))

    def get_total_holes(self, obj):
        return len(self._hole_scores(obj))

    def get_holes_completed(self, obj):
        return sum(1 for hs in self._hole_scores(obj) if hs.is_complete)

    def get_completion_percent(self, obj):
        total_holes = self.get_total_holes(obj)
        if total_holes == 0:
            return 0
        completed = self.get_holes_completed(obj)
        return round((completed / total_holes) * 100, 1)
    

    def _leader_metric_key(self, obj):
        scoring_format = obj.scoring_format
        if scoring_format == Round.SCORING_STABLEFORD:
            return "stableford_total"
        if scoring_format == Round.SCORING_STROKEPLAY:
            return "gross_total"
        if scoring_format == Round.SCORING_MATCHPLAY:
            return "gross_total"
        return "gross_total"

    def _leader_metric_label(self, obj):
        scoring_format = obj.scoring_format
        if scoring_format == Round.SCORING_STABLEFORD:
            return "stableford"
        if scoring_format == Round.SCORING_STROKEPLAY:
            return "gross"
        if scoring_format == Round.SCORING_MATCHPLAY:
            return "gross"
        return "gross"

    def _is_higher_better(self, obj):
        return obj.scoring_format == Round.SCORING_STABLEFORD

    def _ordered_players(self, obj):
        players = self._players(obj)
        metric_key = self._leader_metric_key(obj)
        higher_better = self._is_higher_better(obj)

        if higher_better:
            players.sort(
                key=lambda p: (
                    -(getattr(p, metric_key) or 0),
                    p.player_order,
                    p.id,
                )
            )
        else:
            players.sort(
                key=lambda p: (
                    (getattr(p, metric_key) or 0),
                    p.player_order,
                    p.id,
                )
            )
        return players

    def _player_positions(self, obj):
        ordered = self._ordered_players(obj)
        metric_key = self._leader_metric_key(obj)

        positions = {}
        current_position = 0
        last_value = None

        for index, player in enumerate(ordered, start=1):
            value = getattr(player, metric_key) or 0
            if last_value is None or value != last_value:
                current_position = index
                last_value = value
            positions[player.id] = current_position

        return positions

    def get_leader_name(self, obj):
        ordered = self._ordered_players(obj)
        if not ordered:
            return None
        return ordered[0].display_name

    def get_tied_leaders(self, obj):
        ordered = self._ordered_players(obj)
        if not ordered:
            return []

        metric_key = self._leader_metric_key(obj)
        best_value = getattr(ordered[0], metric_key) or 0

        return [
            player.display_name
            for player in ordered
            if (getattr(player, metric_key) or 0) == best_value
        ]

    def get_leader_value(self, obj):
        ordered = self._ordered_players(obj)
        if not ordered:
            return 0
        metric_key = self._leader_metric_key(obj)
        return getattr(ordered[0], metric_key) or 0

    def get_leaderboard(self, obj):
        metric_key = self._leader_metric_label(obj)
        ordered = self._ordered_players(obj)
        positions = self._player_positions(obj)

        return {
            "metric": metric_key,
            "leader_name": self.get_leader_name(obj),
            "leader_value": self.get_leader_value(obj),
            "tied_leaders": self.get_tied_leaders(obj),
            "players": [
                {
                    "id": player.id,
                    "display_name": player.display_name,
                    "position": positions[player.id],
                    "gross_total": player.gross_total,
                    "net_total": player.net_total,
                    "stableford_total": player.stableford_total,
                }
                for player in ordered
            ],
        }

class RoundHoleScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoundHoleScore
        fields = [
            "id",
            "hole_number",
            "yardage_snapshot",
            "par_snapshot",
            "stroke_index_snapshot",
            "handicap_strokes_received",
            "strokes",
            "adjusted_strokes",
            "gross_to_par",
            "net_strokes",
            "net_to_par",
            "stableford_points",
            "is_complete",
            "notes",
            "created_at",
            "updated_at",
        ]

class RoundPlayerSerializer(serializers.ModelSerializer):
    hole_scores = RoundHoleScoreSerializer(many=True, read_only=True)

    class Meta:
        model = RoundPlayer
        fields = [
            "id",
            "display_name",
            "player_order",
            "is_primary_player",
            "handicap_index_snapshot",
            "course_handicap_snapshot",
            "playing_handicap_snapshot",
            "gross_total",
            "net_total",
            "stableford_total",
            "hole_scores",
        ]

class RoundDetailSerializer(RoundSummaryMixin, serializers.ModelSerializer):
    players = RoundPlayerSerializer(many=True, read_only=True)
    players_count = serializers.SerializerMethodField()
    holes_completed = serializers.SerializerMethodField()
    completion_percent = serializers.SerializerMethodField()
    total_holes = serializers.SerializerMethodField()

    class Meta:
        model = Round
        fields = [
            "id",
            "name",
            "date_played",
            "status",
            "scoring_format",
            "course",
            "tee_set",
            "course_name_snapshot",
            "club_name_snapshot",
            "tee_set_name_snapshot",
            "tee_set_colour_snapshot",
            "course_par_total_snapshot",
            "tee_par_total_snapshot",
            "course_rating_snapshot",
            "slope_rating_snapshot",
            "sss_value_snapshot",
            "holes_count_snapshot",
            "notes",
            "players_count",
            "holes_completed",
            "completion_percent",
            "total_holes",
            "players",
            "created_at",
            "updated_at",
        ]

class RoundListSerializer(RoundSummaryMixin, serializers.ModelSerializer):
    players_count = serializers.SerializerMethodField()
    holes_completed = serializers.SerializerMethodField()
    completion_percent = serializers.SerializerMethodField()
    total_holes = serializers.SerializerMethodField()
    leader_name = serializers.SerializerMethodField()
    leader_value = serializers.SerializerMethodField()
    tied_leaders = serializers.SerializerMethodField()
    leaderboard_metric = serializers.SerializerMethodField()

    class Meta:
        model = Round
        fields = [
            "id",
            "name",
            "date_played",
            "status",
            "scoring_format",
            "course_name_snapshot",
            "tee_set_name_snapshot",
            "players_count",
            "holes_completed",
            "completion_percent",
            "total_holes",
            "leader_name",
            "leader_value",
            "tied_leaders",
            "leaderboard_metric",
            "created_at",
        ]

    def get_leader_name(self, obj):
        return super().get_leader_name(obj)

    def get_leader_value(self, obj):
        return super().get_leader_value(obj)

    def get_tied_leaders(self, obj):
        return super().get_tied_leaders(obj)

    def get_leaderboard_metric(self, obj):
        return self._leader_metric_label(obj)

class RoundDetailMobileSerializer(RoundSummaryMixin, serializers.ModelSerializer):
    course = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()
    leaderboard = serializers.SerializerMethodField()
    players = serializers.SerializerMethodField()
    holes = serializers.SerializerMethodField()
    timestamps = serializers.SerializerMethodField()
    tournament = serializers.SerializerMethodField()

    class Meta:
        model = Round
        fields = [
            "id",
            "name",
            "date_played",
            "status",
            "scoring_format",
            "notes",
            "course",
            "summary",
            "leaderboard",
            "players",
            "holes",
            "timestamps",
            "tournament",
        ]

    def get_course(self, obj):
        return {
            "id": obj.course_id,
            "name": obj.course_name_snapshot,
            "club_name": obj.club_name_snapshot,
            "tee_set_id": obj.tee_set_id,
            "tee_set_name": obj.tee_set_name_snapshot,
            "tee_set_colour": obj.tee_set_colour_snapshot,
            "course_par_total": obj.course_par_total_snapshot,
            "tee_par_total": obj.tee_par_total_snapshot,
            "course_rating": obj.course_rating_snapshot,
            "slope_rating": obj.slope_rating_snapshot,
            "sss_value": obj.sss_value_snapshot,
            "holes_count": obj.holes_count_snapshot,
        }

    def get_summary(self, obj):
        return {
            "players_count": self.get_players_count(obj),
            "holes_completed": self.get_holes_completed(obj),
            "completion_percent": self.get_completion_percent(obj),
            "total_holes": self.get_total_holes(obj),
        }
    
    def get_leaderboard(self, obj):
        return super().get_leaderboard(obj)

    def get_players(self, obj):
        players = list(obj.players.all())
        players.sort(key=lambda p: p.player_order)
        positions = self._player_positions(obj)

        return [
            {
                "id": p.id,
                "display_name": p.display_name,
                "player_order": p.player_order,
                "position": positions[p.id],
                "is_primary_player": p.is_primary_player,
                "handicap_index": p.handicap_index_snapshot,
                "course_handicap": p.course_handicap_snapshot,
                "playing_handicap": p.playing_handicap_snapshot,
                "totals": {
                    "gross": p.gross_total,
                    "net": p.net_total,
                    "stableford": p.stableford_total,
                },
            }
            for p in players
        ]

    def get_holes(self, obj):
        players = list(obj.players.all())
        players.sort(key=lambda p: p.player_order)

        scores_by_hole = {}

        for player in players:
            for hs in player.hole_scores.all():
                hole_number = hs.hole_number
                if hole_number not in scores_by_hole:
                    scores_by_hole[hole_number] = {
                        "number": hole_number,
                        "yardage": hs.yardage_snapshot,
                        "par": hs.par_snapshot,
                        "stroke_index": hs.stroke_index_snapshot,
                        "scores": [],
                    }

                scores_by_hole[hole_number]["scores"].append(
                    {
                        "round_hole_score_id": hs.id,
                        "round_player_id": player.id,
                        "player_name": player.display_name,
                        "player_order": player.player_order,
                        "handicap_strokes_received": hs.handicap_strokes_received,
                        "strokes": hs.strokes,
                        "adjusted_strokes": hs.adjusted_strokes,
                        "gross_to_par": hs.gross_to_par,
                        "net_strokes": hs.net_strokes,
                        "net_to_par": hs.net_to_par,
                        "stableford_points": hs.stableford_points,
                        "is_complete": hs.is_complete,
                        "notes": hs.notes,
                    }
                )

        holes = list(scores_by_hole.values())
        holes.sort(key=lambda h: h["number"])
        return holes
    
    def get_tournament(self, obj):
        if not obj.tournament_id:
            return None

        return {
            "id": obj.tournament_id,
            "name": obj.tournament.name,
            "join_code": obj.tournament.join_code,
            "status": obj.tournament.status,
        }

    def get_timestamps(self, obj):
        return {
            "created_at": obj.created_at,
            "updated_at": obj.updated_at,
            "started_at": obj.started_at,
            "completed_at": obj.completed_at,
            "cancelled_at": obj.cancelled_at,
        }

class RoundPlayerTotalsSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoundPlayer
        fields = [
            "id",
            "display_name",
            "gross_total",
            "net_total",
            "stableford_total",
        ]

class RoundSummaryResponseSerializer(RoundSummaryMixin, serializers.ModelSerializer):
    players_count = serializers.SerializerMethodField()
    holes_completed = serializers.SerializerMethodField()
    completion_percent = serializers.SerializerMethodField()
    total_holes = serializers.SerializerMethodField()
    leader_name = serializers.SerializerMethodField()
    leader_value = serializers.SerializerMethodField()
    tied_leaders = serializers.SerializerMethodField()
    leaderboard_metric = serializers.SerializerMethodField()

    class Meta:
        model = Round
        fields = [
            "id",
            "status",
            "players_count",
            "holes_completed",
            "completion_percent",
            "total_holes",
            "leader_name",
            "leader_value",
            "tied_leaders",
            "leaderboard_metric",
        ]

    def get_leader_name(self, obj):
        return super().get_leader_name(obj)

    def get_leader_value(self, obj):
        return super().get_leader_value(obj)

    def get_tied_leaders(self, obj):
        return super().get_tied_leaders(obj)

    def get_leaderboard_metric(self, obj):
        return self._leader_metric_label(obj)

class RoundHoleScoreUpdateResponseSerializer(serializers.Serializer):
    score = RoundHoleScoreSerializer()
    player_totals = RoundPlayerTotalsSerializer()
    round_summary = RoundSummaryResponseSerializer()

class RoundCreatePlayerSerializer(serializers.Serializer):
    display_name = serializers.CharField(max_length=120)
    user_id = serializers.IntegerField(required=False, allow_null=True)
    is_primary_player = serializers.BooleanField(required=False, default=False)
    handicap_index = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    player_order = serializers.IntegerField(required=False, allow_null=True)

class RoundCreateSerializer(serializers.Serializer):
    course_id = serializers.IntegerField()
    tee_set_id = serializers.IntegerField()
    date_played = serializers.DateField()
    name = serializers.CharField(required=False, allow_blank=True, max_length=200)
    scoring_format = serializers.ChoiceField(
        choices=Round.SCORING_FORMAT_CHOICES,
        required=False,
        default=Round.SCORING_STABLEFORD,
    )
    is_qualifying = serializers.BooleanField(required=False, default=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    allowance_percent = serializers.IntegerField(required=False, default=100)
    players = RoundCreatePlayerSerializer(many=True)

    def validate(self, attrs):
        course_id = attrs["course_id"]
        tee_set_id = attrs["tee_set_id"]
        allowance_percent = attrs.get("allowance_percent", 100)
        players = attrs.get("players", [])

        try:
            course = Course.objects.get(id=course_id, is_active=True)
        except Course.DoesNotExist:
            raise serializers.ValidationError({"course_id": "Invalid course."})

        try:
            tee_set = TeeSet.objects.get(id=tee_set_id, is_active=True)
        except TeeSet.DoesNotExist:
            raise serializers.ValidationError({"tee_set_id": "Invalid tee set."})

        if tee_set.course_id != course.id:
            raise serializers.ValidationError(
                {"tee_set_id": "Selected tee set does not belong to the selected course."}
            )

        if not players:
            raise serializers.ValidationError({"players": "At least one player is required."})

        primary_count = sum(1 for p in players if p.get("is_primary_player"))
        if primary_count > 1:
            raise serializers.ValidationError(
                {"players": "Only one player can be marked as primary."}
            )

        if allowance_percent < 0 or allowance_percent > 100:
            raise serializers.ValidationError(
                {"allowance_percent": "Allowance percent must be between 0 and 100."}
            )

        attrs["course"] = course
        attrs["tee_set"] = tee_set
        return attrs

    def create(self, validated_data):
        course = validated_data["course"]
        tee_set = validated_data["tee_set"]
        players_data = validated_data["players"]

        player_inputs = [
            PlayerInput(
                display_name=p["display_name"],
                user_id=p.get("user_id"),
                is_primary_player=p.get("is_primary_player", False),
                handicap_index=(
                    Decimal(str(p["handicap_index"]))
                    if p.get("handicap_index") is not None
                    else None
                ),
                player_order=p.get("player_order"),
            )
            for p in players_data
        ]

        request = self.context.get("request")
        created_by = getattr(request, "user", None)
        if created_by and not created_by.is_authenticated:
            created_by = None

        return create_round_with_players(
            created_by=created_by,
            course=course,
            tee_set=tee_set,
            date_played=validated_data["date_played"],
            players=player_inputs,
            name=validated_data.get("name", ""),
            scoring_format=validated_data.get("scoring_format", Round.SCORING_STABLEFORD),
            status=Round.STATUS_DRAFT,
            is_qualifying=validated_data.get("is_qualifying", False),
            notes=validated_data.get("notes", ""),
            allowance_percent=validated_data.get("allowance_percent", 100),
        )

class RoundHoleScoreUpdateSerializer(serializers.Serializer):
    strokes = serializers.IntegerField(min_value=1)
    adjusted_strokes = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    is_complete = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        round_obj = self.instance.round_player.round
        if round_obj.status in [Round.STATUS_COMPLETED, Round.STATUS_CANCELLED]:
            raise serializers.ValidationError(
                "Scores cannot be edited for completed or cancelled rounds."
            )
        return attrs

    def update(self, instance, validated_data):
        return update_hole_score(
            round_hole_score=instance,
            strokes=validated_data["strokes"],
            adjusted_strokes=validated_data.get("adjusted_strokes"),
            mark_complete=validated_data.get("is_complete", True),
        )

class HandicapHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = HandicapHistory
        fields = [
            "id",
            "handicap_index",
            "effective_date",
            "source",
            "notes",
            "old_exact_handicap",
            "new_exact_handicap",
            "playing_handicap_used",
            "gross_score",
            "net_score",
            "target_score",
            "buffer_zone_used",
            "nett_differential",
            "adjustment_value",
            "adjustment_type",
            "is_qualifying",
            "rule_version",
            "source_round",
            "created_at",
        ]
    
class TournamentCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    course_id = serializers.IntegerField()
    tee_set_id = serializers.IntegerField()
    scoring_format = serializers.ChoiceField(choices=[(Round.SCORING_STROKEPLAY, "Strokeplay"),(Round.SCORING_STABLEFORD, "Stableford"),]
)
    date_played = serializers.DateField()
    is_qualifying = serializers.BooleanField(default=False)

    def validate(self, attrs):
        course_id = attrs["course_id"]
        tee_set_id = attrs["tee_set_id"]

        try:
            course = Course.objects.get(id=course_id, is_active=True)
        except Course.DoesNotExist:
            raise serializers.ValidationError({"course_id": "Invalid course."})

        try:
            tee_set = TeeSet.objects.get(id=tee_set_id, is_active=True)
        except TeeSet.DoesNotExist:
            raise serializers.ValidationError({"tee_set_id": "Invalid tee set."})

        if tee_set.course_id != course.id:
            raise serializers.ValidationError(
                {"tee_set_id": "Selected tee set does not belong to the selected course."}
            )

        attrs["course"] = course
        attrs["tee_set"] = tee_set
        return attrs

class TournamentJoinSerializer(serializers.Serializer):
    join_code = serializers.CharField(max_length=40)

    def validate_join_code(self, value):
        value = value.strip().lower()
        if not value:
            raise serializers.ValidationError("Join code is required.")
        return value

class TournamentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tournament
        fields = [
            "id",
            "name",
            "join_code",
            "date_played",
            "status",
            "scoring_format",
            "is_qualifying",
            "created_at",
            "updated_at",
        ]

class TournamentLeaderboardRowSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    display_name = serializers.CharField()
    round_id = serializers.IntegerField()
    round_status = serializers.CharField()
    total_score = serializers.IntegerField(allow_null=True)
    total_points = serializers.IntegerField(allow_null=True)
    holes_completed = serializers.IntegerField()