# backend/apps/scoring/urls.py
from django.urls import path

from .views import (
    HandicapHistoryListView, RoundDetailView, RoundHoleScoreUpdateView, RoundListCreateView,
    RoundStatusActionView, TournamentCreateView, TournamentDetailView, TournamentJoinView,
    TournamentLeaderboardView,)

urlpatterns = [
    path("rounds/", RoundListCreateView.as_view(), name="round-list-create"),
    path("rounds/<int:pk>/", RoundDetailView.as_view(), name="round-detail"),
    path("rounds/<int:pk>/start/", RoundStatusActionView.as_view(), {"action": "start"}, name="round-start"),
    path("rounds/<int:pk>/complete/", RoundStatusActionView.as_view(), {"action": "complete"}, name="round-complete"),
    path("rounds/<int:pk>/cancel/", RoundStatusActionView.as_view(), {"action": "cancel"}, name="round-cancel"),
    path("round-hole-scores/<int:pk>/", RoundHoleScoreUpdateView.as_view(), name="round-hole-score-update",  ),
    path("handicap-history/", HandicapHistoryListView.as_view(), name="handicap-history"),
    path("tournaments/", TournamentCreateView.as_view(), name="tournament-create"),
    path("tournaments/join/", TournamentJoinView.as_view(), name="tournament-join"),
    path("tournaments/<int:pk>/", TournamentDetailView.as_view(), name="tournament-detail"),
    path("tournaments/<int:pk>/leaderboard/", TournamentLeaderboardView.as_view(), name="tournament-leaderboard"),
]