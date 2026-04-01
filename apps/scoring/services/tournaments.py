# apps/scoring/services/tournaments.py
import secrets
from django.db import transaction

from apps.scoring.models import Tournament, TournamentEntry
from apps.scoring.services.scoring import PlayerInput, create_round_with_players

JOIN_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ2346789"

def generate_join_code(length: int = 6) -> str:
    return "".join(secrets.choice(JOIN_CODE_ALPHABET) for _ in range(length))

def generate_unique_join_code(length: int = 6) -> str:
    from apps.scoring.models import Tournament

    while True:
        code = generate_join_code(length)
        if not Tournament.objects.filter(join_code=code).exists():
            return code
        

@transaction.atomic
def create_tournament_with_host_round(
    *,
    user,
    tournament_name,
    course,
    tee_set,
    scoring_format,
    date_played,
    is_qualifying=False,
):
    join_code = generate_unique_join_code()

    tournament = Tournament.objects.create(
        name=tournament_name,
        join_code=join_code,
        created_by=user,
        course=course,
        tee_set=tee_set,
        date_played=date_played,
        scoring_format=scoring_format,
        is_qualifying=is_qualifying,
        status=Tournament.STATUS_OPEN,
    )

    profile = getattr(user, "profile", None)
    display_name = profile.display_name if profile and profile.display_name else user.username

    round_obj = create_round_with_players(
        created_by=user,
        course=course,
        tee_set=tee_set,
        date_played=date_played,
        players=[
            PlayerInput(
                display_name=display_name,
                user_id=user.id,
                is_primary_player=True,
                handicap_index=None,
                player_order=1,
            )
        ],
        name=tournament_name,
        scoring_format=scoring_format,
        status="draft",
        is_qualifying=is_qualifying,
    )

    round_obj.tournament = tournament
    round_obj.save(update_fields=["tournament"])

    TournamentEntry.objects.create(
        tournament=tournament,
        user=user,
        round=round_obj,
        display_name_snapshot=display_name,
    )

    return tournament, round_obj

@transaction.atomic
def join_tournament_and_create_round(*, user, join_code, date_played=None):
    tournament = Tournament.objects.select_related("course", "tee_set").get(
        join_code=join_code.upper()
    )

    if tournament.status in [Tournament.STATUS_COMPLETED, Tournament.STATUS_CANCELLED]:
        raise ValueError("This tournament is no longer open.")

    if TournamentEntry.objects.filter(tournament=tournament, user=user).exists():
        raise ValueError("You have already joined this tournament.")

    profile = getattr(user, "profile", None)
    display_name = profile.display_name if profile and profile.display_name else user.username

    round_obj = create_round_with_players(
        created_by=user,
        course=tournament.course,
        tee_set=tournament.tee_set,
        date_played=tournament.date_played,
        players=[
            PlayerInput(
                display_name=display_name,
                user_id=user.id,
                is_primary_player=True,
                handicap_index=None,
                player_order=1,
            )
        ],
        name=tournament.name,
        scoring_format=tournament.scoring_format,
        status="draft",
        is_qualifying=tournament.is_qualifying,
    )

    round_obj.tournament = tournament
    round_obj.save(update_fields=["tournament"])

    TournamentEntry.objects.create(
        tournament=tournament,
        user=user,
        round=round_obj,
        display_name_snapshot=display_name,
    )

    return tournament, round_obj

def get_tournament_leaderboard(tournament):
    entries = (
        tournament.entries
        .select_related("round", "user")
        .prefetch_related("round__players__hole_scores")
    )

    rows = []

    for entry in entries:
        primary_player = next(
            (p for p in entry.round.players.all() if p.is_primary_player),
            None,
        )

        if primary_player is None:
            continue

        holes_completed = sum(
            1 for hs in primary_player.hole_scores.all() if hs.is_complete
        )

        rows.append({
            "user_id": entry.user_id,
            "display_name": entry.display_name_snapshot,
            "round_id": entry.round_id,
            "round_status": entry.round.status,
            "total_score": primary_player.gross_total,
            "total_points": primary_player.stableford_total,
            "holes_completed": holes_completed,
        })

    if tournament.scoring_format == "stableford":
        rows.sort(
            key=lambda x: (
                -(x["total_points"] or 0),
                -(x["holes_completed"] or 0),
            )
        )
    else:
        rows.sort(
            key=lambda x: (
                (x["total_score"] or 9999),
                -(x["holes_completed"] or 0),
            )
        )

    return rows