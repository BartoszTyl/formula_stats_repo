from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="dashboard_app"),
    path("analysis/", views.analysis, name="analysis"),
    path("drivers/", views.drivers, name="drivers"),
    path("about/", views.about, name="about"),
    path("get-events/<int:year>/", views.get_events, name="get_events"),
    path("get-sessions/<int:event_id>/", views.get_sessions, name="get_sessions"),
    path("ajax/get-drivers/<int:session_id>/", views.get_drivers, name="get_drivers"),
    path("ajax/get-laps/<int:session_id>/<int:driver_id>/", views.get_laps, name="get_laps"),

]