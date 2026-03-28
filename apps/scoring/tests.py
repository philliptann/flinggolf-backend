# backend/apps/scoring/tests.py
# sudo docker compose -f docker-compose.prod.yml up -d --build
#sudo docker compose -f docker-compose.prod.yml exec backend python manage.py test apps.scoring


from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.courses.models import Club, Course, Hole, TeeSet, TeeSetHole
from apps.scoring.models import Round, RoundHoleScore


User = get_user_model()


class ScoringAPITests(APITestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            username="usera",
            email="usera@example.com",
            password="StrongPass123!",
        )
        self.user_b = User.objects.create_user(
            username="userb",
            email="userb@example.com",
            password="StrongPass123!",
        )

        self.club = Club.objects.create(
            name="Beamish FlingGolf",
            is_active=True,
        )
        self.course = Course.objects.create(
            club=self.club,
            name="Beamish golf",
            holes=18,
            par_total=72,
            is_active=True,
        )
        self.tee_set = TeeSet.objects.create(
            course=self.course,
            name="White",
            colour=TeeSet.COLOUR_WHITE,
            par_total=72,
            course_rating=Decimal("70.6"),
            slope_rating=134,
            is_active=True,
        )

        for hole_number in range(1, 19):
            default_par = 4
            if hole_number in [3, 7, 12, 16]:
                default_par = 3
            elif hole_number in [1, 5, 10, 17]:
                default_par = 5

            hole = Hole.objects.create(
                course=self.course,
                hole_number=hole_number,
                default_par=default_par,
                default_stroke_index=hole_number,
            )

            TeeSetHole.objects.create(
                tee_set=self.tee_set,
                hole=hole,
                yardage=300 + hole_number,
                par=default_par,
                stroke_index=hole_number,
            )

        self.rounds_url = reverse("round-list-create")

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def create_round_for_user_a(self):
        self.authenticate(self.user_a)
        payload = {
            "course_id": self.course.id,
            "tee_set_id": self.tee_set.id,
            "date_played": "2026-03-25",
            "name": "User A Test Round",
            "players": [
                {
                    "display_name": "User A",
                    "is_primary_player": True,
                    "handicap_index": "18.2",
                    "player_order": 1,
                }
            ],
        }
        response = self.client.post(self.rounds_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return Round.objects.get(id=response.data["id"])

    def test_rounds_list_requires_auth(self):
        response = self.client.get(self.rounds_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_round_defaults_to_draft(self):
        self.authenticate(self.user_a)
        payload = {
            "course_id": self.course.id,
            "tee_set_id": self.tee_set.id,
            "date_played": "2026-03-25",
            "name": "Draft Round",
            "players": [
                {
                    "display_name": "User A",
                    "is_primary_player": True,
                    "handicap_index": "18.2",
                    "player_order": 1,
                }
            ],
        }
        response = self.client.post(self.rounds_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], Round.STATUS_DRAFT)

    def test_user_can_retrieve_own_round(self):
        round_a = self.create_round_for_user_a()
        self.authenticate(self.user_a)

        url = reverse("round-detail", kwargs={"pk": round_a.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], round_a.id)

    def test_other_user_cannot_retrieve_round(self):
        round_a = self.create_round_for_user_a()
        self.authenticate(self.user_b)

        url = reverse("round-detail", kwargs={"pk": round_a.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_can_patch_own_hole_score(self):
        round_a = self.create_round_for_user_a()
        score = RoundHoleScore.objects.filter(
            round_player__round=round_a
        ).order_by("hole_number").first()

        self.authenticate(self.user_a)
        url = reverse("round-hole-score-update", kwargs={"pk": score.id})
        payload = {
            "strokes": 5,
            "is_complete": True,
        }
        response = self.client.patch(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        score.refresh_from_db()
        self.assertEqual(score.strokes, 5)
        self.assertTrue(score.is_complete)

    def test_other_user_cannot_patch_hole_score(self):
        round_a = self.create_round_for_user_a()
        score = RoundHoleScore.objects.filter(
            round_player__round=round_a
        ).order_by("hole_number").first()

        self.authenticate(self.user_b)
        url = reverse("round-hole-score-update", kwargs={"pk": score.id})
        payload = {
            "strokes": 6,
            "is_complete": True,
        }
        response = self.client.patch(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_completed_round_rejects_hole_score_update(self):
        round_a = self.create_round_for_user_a()
        round_a.status = Round.STATUS_COMPLETED
        round_a.save()

        score = RoundHoleScore.objects.filter(
            round_player__round=round_a
        ).order_by("hole_number").first()

        self.authenticate(self.user_a)
        url = reverse("round-hole-score-update", kwargs={"pk": score.id})
        payload = {
            "strokes": 4,
            "is_complete": True,
        }
        response = self.client.patch(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_round_start_action(self):
        round_a = self.create_round_for_user_a()
        self.authenticate(self.user_a)

        url = reverse("round-start", kwargs={"pk": round_a.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        round_a.refresh_from_db()
        self.assertEqual(round_a.status, Round.STATUS_IN_PROGRESS)
        self.assertIsNotNone(round_a.started_at)

    def test_round_complete_action(self):
        round_a = self.create_round_for_user_a()
        round_a.status = Round.STATUS_IN_PROGRESS
        round_a.save()

        self.authenticate(self.user_a)
        url = reverse("round-complete", kwargs={"pk": round_a.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        round_a.refresh_from_db()
        self.assertEqual(round_a.status, Round.STATUS_COMPLETED)
        self.assertIsNotNone(round_a.completed_at)

    def test_round_cancel_action(self):
        round_a = self.create_round_for_user_a()
        self.authenticate(self.user_a)

        url = reverse("round-cancel", kwargs={"pk": round_a.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        round_a.refresh_from_db()
        self.assertEqual(round_a.status, Round.STATUS_CANCELLED)
        self.assertIsNotNone(round_a.cancelled_at)

    def test_other_user_cannot_start_round(self):
        round_a = self.create_round_for_user_a()
        self.authenticate(self.user_b)

        url = reverse("round-start", kwargs={"pk": round_a.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_complete_draft_round(self):
        round_a = self.create_round_for_user_a()
        self.authenticate(self.user_a)

        url = reverse("round-complete", kwargs={"pk": round_a.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_only_sees_own_rounds_in_list(self):
        round_a = self.create_round_for_user_a()

        self.authenticate(self.user_b)
        response = self.client.get(self.rounds_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = [item["id"] for item in response.data["results"]]
        self.assertNotIn(round_a.id, returned_ids)

    def test_round_list_includes_summary_fields(self):
        self.create_round_for_user_a()
        self.authenticate(self.user_a)

        response = self.client.get(self.rounds_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data["results"][0]
        self.assertIn("players_count", item)
        self.assertIn("holes_completed", item)
        self.assertIn("completion_percent", item)
        self.assertIn("total_holes", item)

    def test_round_list_is_paginated(self):
        self.create_round_for_user_a()
        self.authenticate(self.user_a)

        response = self.client.get(self.rounds_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertIn("count", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)

    def test_round_list_supports_multi_status_filter(self):
        round_a = self.create_round_for_user_a()
        round_a.status = Round.STATUS_IN_PROGRESS
        round_a.save(update_fields=["status"])

        self.authenticate(self.user_a)
        response = self.client.get(f"{self.rounds_url}?status=draft,in_progress")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)

    def test_round_list_supports_search(self):
        self.create_round_for_user_a()
        self.authenticate(self.user_a)

        response = self.client.get(f"{self.rounds_url}?search=beamish")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)

    def test_round_detail_mobile_shape_contains_holes(self):
        round_a = self.create_round_for_user_a()
        self.authenticate(self.user_a)

        url = reverse("round-detail", kwargs={"pk": round_a.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("holes", response.data)
        self.assertIn("players", response.data)
        self.assertIn("summary", response.data)
    
    def test_hole_score_patch_returns_player_totals_and_round_summary(self):
        round_a = self.create_round_for_user_a()
        round_a.status = Round.STATUS_IN_PROGRESS
        round_a.save(update_fields=["status"])

        score = RoundHoleScore.objects.filter(
            round_player__round=round_a
        ).order_by("hole_number").first()

        self.authenticate(self.user_a)
        url = reverse("round-hole-score-update", kwargs={"pk": score.id})
        payload = {
            "strokes": 5,
            "is_complete": True,
        }
        response = self.client.patch(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("score", response.data)
        self.assertIn("player_totals", response.data)
        self.assertIn("round_summary", response.data)

    def test_hole_score_patch_updates_round_summary_counts(self):
        round_a = self.create_round_for_user_a()
        round_a.status = Round.STATUS_IN_PROGRESS
        round_a.save(update_fields=["status"])

        score = RoundHoleScore.objects.filter(
            round_player__round=round_a
        ).order_by("hole_number").first()

        self.authenticate(self.user_a)
        url = reverse("round-hole-score-update", kwargs={"pk": score.id})
        payload = {
            "strokes": 5,
            "is_complete": True,
        }
        response = self.client.patch(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["round_summary"]["holes_completed"], 1)
    
    def create_two_player_round_for_user_a(self, scoring_format=Round.SCORING_STABLEFORD):
        self.authenticate(self.user_a)
        payload = {
            "course_id": self.course.id,
            "tee_set_id": self.tee_set.id,
            "date_played": "2026-03-25",
            "name": "Two Player Round",
            "scoring_format": scoring_format,
            "players": [
                {
                    "display_name": "User A",
                    "is_primary_player": True,
                    "handicap_index": "18.2",
                    "player_order": 1,
                },
                {
                    "display_name": "Guest",
                    "is_primary_player": False,
                    "handicap_index": "10.0",
                    "player_order": 2,
                },
            ],
        }
        response = self.client.post(self.rounds_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return Round.objects.get(id=response.data["id"])
    
    def test_round_detail_includes_leaderboard_block(self):
        round_a = self.create_two_player_round_for_user_a()
        self.authenticate(self.user_a)

        url = reverse("round-detail", kwargs={"pk": round_a.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("leaderboard", response.data)
        self.assertIn("metric", response.data["leaderboard"])
        self.assertIn("leader_name", response.data["leaderboard"])
        self.assertIn("tied_leaders", response.data["leaderboard"])

    def test_round_list_includes_leader_fields(self):
        self.create_two_player_round_for_user_a()
        self.authenticate(self.user_a)

        response = self.client.get(self.rounds_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data["results"][0]
        self.assertIn("leader_name", item)
        self.assertIn("leader_value", item)
        self.assertIn("tied_leaders", item)
        self.assertIn("leaderboard_metric", item)

    def test_stableford_leader_updates_after_score_patch(self):
        round_a = self.create_two_player_round_for_user_a()
        round_a.status = Round.STATUS_IN_PROGRESS
        round_a.save(update_fields=["status"])

        players = list(round_a.players.order_by("player_order"))
        player_1 = players[0]
        player_2 = players[1]

        score_1 = RoundHoleScore.objects.filter(round_player=player_1, hole_number=1).first()
        score_2 = RoundHoleScore.objects.filter(round_player=player_2, hole_number=1).first()

        self.authenticate(self.user_a)

        url_1 = reverse("round-hole-score-update", kwargs={"pk": score_1.id})
        self.client.patch(url_1, {"strokes": 7, "is_complete": True}, format="json")

        url_2 = reverse("round-hole-score-update", kwargs={"pk": score_2.id})
        response = self.client.patch(url_2, {"strokes": 3, "is_complete": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["round_summary"]["leaderboard_metric"], "stableford")
        self.assertEqual(response.data["round_summary"]["leader_name"], "Guest")