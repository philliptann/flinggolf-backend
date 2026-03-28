from django.urls import path
from .views import PageListView, PageDetailView, RuleSectionListView

urlpatterns = [
    path("pages/", PageListView.as_view(), name="page-list"),
    path("pages/<slug:slug>/", PageDetailView.as_view(), name="page-detail"),
    path("rules/", RuleSectionListView.as_view(), name="rules-list"),
]
