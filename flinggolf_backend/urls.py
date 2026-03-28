#flinggolf/backend/flinggolf_backend/urls.py
from django.contrib import admin
from django.urls import path
from django.urls import path, include
#from drf_spectacular.views import (
   # SpectacularAPIView,
   # SpectacularSwaggerView,
   # SpectacularRedocView,
#)
from apps.core.views import index

urlpatterns = [
    path("admin/", admin.site.urls),
    
    path("", index, name="index"),

    #path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    #path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    #path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    path("api/", include("apps.core.urls")),
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.content.urls")),
    path("api/", include("apps.courses.urls")),
    path("api/", include("apps.scoring.urls")),
]
