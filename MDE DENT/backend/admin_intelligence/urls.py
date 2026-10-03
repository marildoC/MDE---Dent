from django.urls import path

from .views import AdminIntelligenceQueryView, AdminIntelligenceSuggestionsView


urlpatterns = [
    path("query/", AdminIntelligenceQueryView.as_view(), name="admin-intelligence-query"),
    path(
        "suggestions/",
        AdminIntelligenceSuggestionsView.as_view(),
        name="admin-intelligence-suggestions",
    ),
]
