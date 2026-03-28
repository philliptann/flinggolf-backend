# backend/apps/courses/urls.py
from django.urls import path
from .views import CourseListView, CourseDetailView

urlpatterns = [
    path("courses/", CourseListView.as_view(), name="course-list"),
    path("courses/<int:id>/", CourseDetailView.as_view(), name="course-detail"),
]
