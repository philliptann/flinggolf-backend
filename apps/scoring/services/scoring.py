# backend/apps/scoring/services/scoring.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.courses.models import TeeSet, TeeSetHole
from apps.scoring.models import HandicapHistory, Round, RoundHoleScore, RoundPlayer

User = get_user_model()


@dataclass
class PlayerInput:
    display_name: str
    user_id: int | None = None
    is_primary_player: bool = False
    handicap_index: Decimal | None = None
    player_order: int | None = None


def calculate_gross_to_par(strokes: int, par: int) -> int:
    return strokes - par


def calculate_net_strokes(strokes: int, handicap_strokes_received: int) -> int:
    return strokes - handicap_strokes_received


def calculate_net_to_par(net_strokes: int, par: int) -> int:
    return net_strokes - par


def calculate_stableford_points(net_strokes: int, par: int) -> int:
    points = 2 + (par - net_strokes)
    return max(points, 0)


def calculate_handicap_strokes_for_hole(
    playing_handicap: int | None,
    stroke_index: int,
    holes_count: int = 18,
) -> int:
    if not playing_handicap or playing_handicap <= 0:
        return 0

    full_cycles = playing_handicap // holes_count
    remainder = playing_handicap % holes_count

    extra = 1 if stroke_index <= remainder and remainder > 0 else 0
    return full_cycles + extra


def get_latest_handicap_index_for_user(user: User | None) -> Decimal | None:
    if not user:
        return None

    latest = (
        HandicapHistory.objects.filter(user=user)
        .order_by("-effective_date", "-created_at")
        .first()
    )
    return latest.handicap_index if latest else None


def calculate_course_handicap(
    handicap_index: Decimal | None,
    slope_rating: int | None,
    course_rating: Decimal | None = None,
    par_total: int | None = None,
) -> int | None:
    """
    Simplified initial implementation.

    WHS full formula is often:
        Course Handicap = Handicap Index × (Slope Rating / 113) + (Course Rating - Par)

    For now this supports a practical version and includes CR-Par if both are present.
    """
    if handicap_index is None or slope_rating is None:
        return None

    base = Decimal(handicap_index) * Decimal(slope_rating) / Decimal(113)

    if course_rating is not None and par_total is not None:
        base += Decimal(course_rating) - Decimal(par_total)

    return int(round(base))


def calculate_playing_handicap(
    course_handicap: int | None,
    allowance_percent: int = 100,
) -> int | None:
    if course_handicap is None:
        return None
    return int(round(course_handicap * allowance_percent / 100))


@transaction.atomic
def create_round_with_players(
    *,
    created_by,
    course,
    tee_set: TeeSet,
    date_played: date,
    players: Iterable[PlayerInput],
    name: str = "",
    scoring_format: str = Round.SCORING_STABLEFORD,
    status: str = Round.STATUS_DRAFT,
    is_qualifying: bool = False,
    notes: str = "",
    allowance_percent: int = 100,
) -> Round:
    if tee_set.course_id != course.id:
        raise ValueError("Selected tee set does not belong to the selected course.")

    tee_holes = list(
        TeeSetHole.objects.filter(tee_set=tee_set)
        .select_related("hole")
        .order_by("hole__hole_number")
    )

    if not tee_holes:
        raise ValueError("Selected tee set has no tee hole data.")

    player_inputs = list(players)
    if not player_inputs:
        raise ValueError("At least one player is required.")

    round_obj = Round.objects.create(
        created_by=created_by,
        course=course,
        tee_set=tee_set,
        name=name,
        date_played=date_played,
        status=status,
        scoring_format=scoring_format,
        course_name_snapshot=course.name,
        club_name_snapshot=course.club.name if course.club_id else "",
        tee_set_name_snapshot=tee_set.name,
        tee_set_colour_snapshot=tee_set.colour,
        course_par_total_snapshot=course.par_total,
        tee_par_total_snapshot=tee_set.par_total,
        course_rating_snapshot=tee_set.course_rating,
        slope_rating_snapshot=tee_set.slope_rating,
        sss_value_snapshot=tee_set.sss_value,
        holes_count_snapshot=course.holes,
        notes=notes,
        is_qualifying=is_qualifying,
    )

    for idx, player_input in enumerate(player_inputs, start=1):
        linked_user = None
        if player_input.user_id:
            linked_user = User.objects.filter(id=player_input.user_id).first()
        elif created_by and idx == 1:
            linked_user = created_by
            
            

        handicap_index = (
            player_input.handicap_index
            if player_input.handicap_index is not None
            else get_latest_handicap_index_for_user(linked_user)
        )

        course_handicap = calculate_course_handicap(
            handicap_index=handicap_index,
            slope_rating=tee_set.slope_rating,
            course_rating=tee_set.course_rating,
            par_total=tee_set.par_total,
        )

        playing_handicap = calculate_playing_handicap(
            course_handicap=course_handicap,
            allowance_percent=allowance_percent,
        )

        round_player = RoundPlayer.objects.create(
            round=round_obj,
            user=linked_user,
            display_name=player_input.display_name,
            player_order=player_input.player_order if player_input.player_order is not None else idx,
            is_primary_player=player_input.is_primary_player if player_input.is_primary_player else (idx == 1),
            handicap_index_snapshot=handicap_index,
            course_handicap_snapshot=course_handicap,
            playing_handicap_snapshot=playing_handicap,
        )

        hole_scores = []
        for tee_hole in tee_holes:
            handicap_strokes = calculate_handicap_strokes_for_hole(
                playing_handicap=playing_handicap,
                stroke_index=tee_hole.stroke_index or tee_hole.hole.default_stroke_index,
                holes_count=round_obj.holes_count_snapshot or 18,
            )

            hole_scores.append(
                RoundHoleScore(
                    round_player=round_player,
                    hole_number=tee_hole.hole.hole_number,
                    yardage_snapshot=tee_hole.yardage,
                    par_snapshot=tee_hole.par or tee_hole.hole.default_par,
                    stroke_index_snapshot=tee_hole.stroke_index
                    or tee_hole.hole.default_stroke_index,
                    handicap_strokes_received=handicap_strokes,
                )
            )

        RoundHoleScore.objects.bulk_create(hole_scores)

    return round_obj


@transaction.atomic
def update_hole_score(
    *,
    round_hole_score: RoundHoleScore,
    strokes: int,
    adjusted_strokes: int | None = None,
    mark_complete: bool = True,
) -> RoundHoleScore:
    if strokes <= 0:
        raise ValueError("strokes must be greater than zero.")

    adjusted = adjusted_strokes if adjusted_strokes is not None else strokes

    net_strokes = calculate_net_strokes(
        strokes=adjusted,
        handicap_strokes_received=round_hole_score.handicap_strokes_received,
    )
    gross_to_par = calculate_gross_to_par(strokes=adjusted, par=round_hole_score.par_snapshot)
    net_to_par = calculate_net_to_par(net_strokes=net_strokes, par=round_hole_score.par_snapshot)
    stableford_points = calculate_stableford_points(
        net_strokes=net_strokes,
        par=round_hole_score.par_snapshot,
    )

    round_hole_score.strokes = strokes
    round_hole_score.adjusted_strokes = adjusted
    round_hole_score.gross_to_par = gross_to_par
    round_hole_score.net_strokes = net_strokes
    round_hole_score.net_to_par = net_to_par
    round_hole_score.stableford_points = stableford_points
    round_hole_score.is_complete = mark_complete
    round_hole_score.save()

    recompute_round_player_totals(round_hole_score.round_player)

    return round_hole_score


def recompute_round_player_totals(round_player: RoundPlayer) -> RoundPlayer:
    hole_scores = round_player.hole_scores.all()

    gross_total = 0
    net_total = 0
    stableford_total = 0

    for hs in hole_scores:
        if hs.adjusted_strokes is not None:
            gross_total += hs.adjusted_strokes
        if hs.net_strokes is not None:
            net_total += hs.net_strokes
        if hs.stableford_points is not None:
            stableford_total += hs.stableford_points

    round_player.gross_total = gross_total or None
    round_player.net_total = net_total or None
    round_player.stableford_total = stableford_total or None
    round_player.save(
        update_fields=[
            "gross_total",
            "net_total",
            "stableford_total",
        ]
    )
    return round_player
