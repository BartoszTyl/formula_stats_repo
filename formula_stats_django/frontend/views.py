from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from static_data.models import Season, Schedule, Session, Driver, Lap

from static_visuals.plotting.team_pace_lap_times import TeamLapVisuals
from static_visuals.plotting.weather import WeatherVisuals
from static_visuals.plotting.driver_pace_lap_times import DriverLapVisuals
from static_visuals.plotting.tyres import TyreVisuals


def home(request):
    return render(request, "home.html")



def drivers(request):
    available_drivers = Driver.objects.all()
    context = {
        "available_drivers": available_drivers,
    }
    return render(request, "drivers.html", context)



def about(request):
    return render(request, "about.html")



def analysis(request):
    available_years = Season.objects.values_list("year", flat=True).distinct().order_by("-year")
    available_visuals = ["Team Pace/Lap Times", "Drivers Pace/Lap Times", "Weather Data", "Telemetry", "Tyres"]

    selected_year = None
    selected_event_id = None
    selected_session_id = None
    selected_visual = None
    selected_driver_id = None
    selected_lap_number = None
    event_name = None
    session_type = None
    plots = []
    selected_visual_names = []

    available_events = []
    available_sessions = []
    available_drivers = []
    available_laps = []

    if request.method == "POST":
        selected_year = request.POST.get("year")
        selected_event_id = request.POST.get("event_id")
        selected_session_id = request.POST.get("session_id")
        selected_visual = request.POST.get("visual")
        selected_driver_id = request.POST.get("driver")
        selected_lap_number = request.POST.get("lap")

        if selected_year:
            event_ids_with_sessions = Session.objects.values_list("event_id", flat=True).distinct()
            available_events = Schedule.objects.filter(
                season_year=selected_year, id__in=event_ids_with_sessions
            ).values("id", "name")

        if selected_event_id:
            available_sessions = Session.objects.filter(event=selected_event_id).values("id", "type")

        if selected_event_id and selected_session_id:
            event_name = Schedule.objects.get(id=selected_event_id).name.lower().replace(" ", "_")
            session_type = Session.objects.get(id=selected_session_id).type.lower()
            available_drivers = (
                Driver.objects.filter(lap__session_id=selected_session_id)
                .distinct()
                .values("id", "abbreviation")
            )
            # Get available laps for a selected driver
            if selected_driver_id:
                available_laps = (
                    Lap.objects.filter(session_id=selected_session_id, driver_id=selected_driver_id)
                    .order_by("lap_number")
                    .values("lap_number")
                    .distinct()
                )
                
            try:
                if selected_visual == "Team Pace/Lap Times":
                    plotter = TeamLapVisuals(selected_year, selected_event_id, selected_session_id)
                elif selected_visual == "Drivers Pace/Lap Times":
                    plotter = DriverLapVisuals(selected_year, selected_event_id, selected_session_id)
                elif selected_visual == "Weather Data":
                    plotter = WeatherVisuals(selected_year, selected_event_id, selected_session_id)
                elif selected_visual == "Tyres":
                    plotter = TyreVisuals(selected_year, selected_event_id, selected_session_id)
                else:
                    plotter = None

                if plotter:
                    for method_name in plotter.PLOT_METHODS:
                        method = getattr(plotter, method_name)
                        plot = method()
                        plots.append(plot)
                        selected_visual_names.append(method.plot_name)

            except Exception as e:
                print(f"Error while generating plots: {e}")
    else:
        # Handle GET with filtering
        selected_year = request.GET.get("year")
        if selected_year:
            event_ids_with_sessions = Session.objects.values_list("event_id", flat=True).distinct()
            available_events = Schedule.objects.filter(
                season_year=selected_year, id__in=event_ids_with_sessions
            ).values("id", "name")

    context = {
        "available_years": available_years,
        "available_visuals": available_visuals,
        "selected_year": selected_year,
        "selected_event_id": selected_event_id,
        "selected_session_id": selected_session_id,
        "selected_visual": selected_visual,
        "available_events": available_events,
        "available_sessions": available_sessions,
        "event_name": event_name,
        "session_type": session_type,
        "plots": plots,
        "selected_visual_names": selected_visual_names,
        "selected_driver_id": selected_driver_id,
        "selected_lap_number": selected_lap_number,
        "available_drivers": available_drivers,
        "available_laps": available_laps,
    }

    return render(request, "analysis.html", context)

@require_GET
def get_events(request, year):
    event_ids_with_sessions = Session.objects.values_list("event_id", flat=True).distinct()
    filtered_events = Schedule.objects.filter(season_year=year, id__in=event_ids_with_sessions).values("id", "name")

    return JsonResponse({"events": list(filtered_events)})

@require_GET
def get_sessions(request, event_id):
    sessions = Session.objects.filter(event=event_id).values("id", "type", "event")
    return JsonResponse({"sessions": list(sessions)})

@require_GET
def get_drivers(request, session_id):
    drivers_ids = Lap.objects.filter(session_id=session_id).values("driver").distinct()
    drivers = Driver.objects.filter(id__in=drivers_ids).values('id', 'abbreviation')
    return JsonResponse({"drivers": list(drivers)})

@require_GET
def get_laps(request, session_id, driver_id):
    laps = Lap.objects.filter(session_id=session_id, driver_id=driver_id).values("lap_number").order_by("lap_number").distinct()
    return JsonResponse({"laps": list(laps)})