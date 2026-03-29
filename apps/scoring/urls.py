# backend/apps/scoring/urls.py
from django.urls import path

from .views import (
    RoundDetailView,
    RoundHoleScoreUpdateView,
    RoundListCreateView,
    RoundStatusActionView,
    HandicapHistoryListView,
)

urlpatterns = [
    path("rounds/", RoundListCreateView.as_view(), name="round-list-create"),
    path("rounds/<int:pk>/", RoundDetailView.as_view(), name="round-detail"),
    path("rounds/<int:pk>/start/", RoundStatusActionView.as_view(), {"action": "start"}, name="round-start"),
    path("rounds/<int:pk>/complete/", RoundStatusActionView.as_view(), {"action": "complete"}, name="round-complete"),
    path("rounds/<int:pk>/cancel/", RoundStatusActionView.as_view(), {"action": "cancel"}, name="round-cancel"),
    path("round-hole-scores/<int:pk>/", RoundHoleScoreUpdateView.as_view(), name="round-hole-score-update",  ),
    path("handicap-history/", HandicapHistoryListView.as_view(), name="handicap-history"),
]