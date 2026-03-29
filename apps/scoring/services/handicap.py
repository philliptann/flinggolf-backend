# backend/apps/scoring/services/handicap.py
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from apps.scoring.models import HandicapHistory, Round, RoundPlayer

def calculate_playing_handicap(exact_handicap: Decimal | None) -> int | None:
    if exact_handicap is None:
        return None
    return int(exact_handicap.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

def calculate_target_score(round_obj) -> int:
    if round_obj.sss_value_snapshot is not None:
        return int(round(round_obj.sss_value_snapshot))
    return int(round_obj.tee_par_total_snapshot or round_obj.course_par_total_snapshot or 0)

def calculate_adjustment(nett_differential: int, buffer_zone: int = 2) -> tuple[Decimal, str]:
    if nett_differential < 0:
        adjustment = Decimal(abs(nett_differential)) * Decimal("0.2")
        return (-adjustment, "decrease")

    if nett_differential <= buffer_zone:
        return (Decimal("0.0"), "no_change")

    return (Decimal("0.1"), "increase")
    
def all_scores_complete(round_player: RoundPlayer) -> bool:
    return not round_player.hole_scores.filter(is_complete=False).exists()


@transaction.atomic
def apply_handicap_updates_for_round(round_obj: Round, buffer_zone: int = 2) -> None:
    if not round_obj.is_qualifying:
        return

    if round_obj.handicap_applied:
        return

    players = list(round_obj.players.select_related("user").all())

    for round_player in players:
        if not round_player.user_id:
            continue

        if round_player.handicap_index_snapshot is None:
            continue

        if not all_scores_complete(round_player):
            continue

        if round_player.gross_total is None:
            continue

        old_exact = Decimal(round_player.handicap_index_snapshot)
        playing_handicap = (
            round_player.playing_handicap_snapshot
            if round_player.playing_handicap_snapshot is not None
            else calculate_playing_handicap(old_exact)
        )

        if playing_handicap is None:
            continue

        gross_score = int(round_player.gross_total)
        net_score = gross_score - int(playing_handicap)
        target_score = calculate_target_score(round_obj)
        nett_differential = net_score - target_score
        adjustment_delta, adjustment_type = calculate_adjustment(
            nett_differential, buffer_zone=buffer_zone
        )

        new_exact = old_exact + adjustment_delta

        HandicapHistory.objects.create(
            user=round_player.user,
            source_round=round_obj,
            old_exact_handicap=old_exact,
            new_exact_handicap=new_exact,
            playing_handicap_used=playing_handicap,
            gross_score=gross_score,
            net_score=net_score,
            target_score=target_score,
            buffer_zone_used=buffer_zone,
            nett_differential=nett_differential,
            adjustment_value=abs(adjustment_delta),
            adjustment_type=adjustment_type,
            is_qualifying=True,
            rule_version="legacy_v1",
            handicap_index=new_exact,
            effective_date=round_obj.date_played,
            source="round_complete",
            notes="Automatic handicap update from qualifying round.",
        )

    round_obj.handicap_applied = True
    round_obj.save(update_fields=["handicap_applied", "updated_at"])

