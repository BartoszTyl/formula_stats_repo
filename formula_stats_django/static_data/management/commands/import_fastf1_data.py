import fastf1 as ff1
from fastf1 import plotting
import pandas as pd
import pycountry
import logging
import time
from django.utils.timezone import make_aware
from datetime import datetime, timezone
from rapidfuzz import process
from fastf1.core import Session
# from fastf1.events import EventSchedule, Event

from static_data.models import (
    Season, Event, Constructor, ConstructorColor, Driver, DriverRacingNumber, TyreCompounds, Session, Lap,
    Telemetry, Result, Weather, RaceControlMessage, CarData, PositionData, Circuit
    )
from django.core.management.base import BaseCommand

# * python manage.py import_fastf1_data --year 2024 --event Australia

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Import F1 data into the database based on the FastF1 data."

    # Add arguments to the command
    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, required=True, help="Season year (e.g., 2025)")
        parser.add_argument("--event", type=str, required=True, help="Grand Prix name (e.g., 'Monza')")
       
        
    def handle(self, **kwargs):
        year = kwargs.get("year")
        event = kwargs.get("event")
        
        self.current_year = datetime.today().year
        # List of years for which data is available from FastF1
        self.years_available = list(range(2018, self.current_year + 1))
        # self.session_names = ['Practice 1', 'Practice 2', 'Practice 3', 'Sprint', 'Sprint Shootout', 'Sprint Qualifying', 'Qualifying', 'Race']
        # self.session_numbers = ["Session1", "Session2", "Session3", "Session4", "Session5"]
        
        # Dictionary with available session for each event of the year.
        # {'Pre-Season Testing': ['Practice 1', 'Practice 2', 'Practice 3', 'None', 'None']}
        # {'Australian Grand Prix': ['Practice 1', 'Practice 2', 'Practice 3', 'Qualifying', 'Race']}
        self.event_sessions = {}
        for _, row in ff1.get_event_schedule(year).iterrows():
            sessions = row[["Session1", "Session2", "Session3", "Session4", "Session5"]].tolist()
            sessions = [session for session in sessions if session != "None"]
            self.event_sessions[row["EventName"]] = sessions
        
        self.matched_event = process.extractOne(event, list(self.event_sessions.keys()))[0]
        
        self.stdout.write(self.style.NOTICE("Populating database..."))
        
        start_time = time.time()
        
        self.populate_data(year, event)
        
        end_time = time.time()  # End the timer
        elapsed_time = end_time - start_time  # Calculate elapsed time
        minutes = elapsed_time // 60  # Minutes
        seconds = elapsed_time % 60  # Seconds
        
        # Print out the time it took
        self.stdout.write(self.style.SUCCESS(f"Data import for {year} {event} completed in {int(minutes)} minutes and {int(seconds)} seconds."))


    def populate_data(self, year: int, event: str):
        self.populate_seasons(year)
        
        loaded_session = ff1.get_session(year, event, 1)
        loaded_session.load()
        
        # loaded_schedule = ff1.get_event_schedule(year)
        loaded_event = ff1.get_event(year, event)
        
        self.populate_circuit(loaded_session)
        self.populate_event(year, loaded_event)
        self.populate_tyre_compounds(year, loaded_session)
        self.populate_constructors(year, loaded_session)
        
        
        for i, sess in enumerate(self.event_sessions[self.matched_event], start=1):
            loaded_session = ff1.get_session(year, event, sess)
            loaded_session.load()
            self.populate_drivers(year, loaded_session)
            self.populate_sessions(year, loaded_session, loaded_event, i)
            self.populate_results(year, loaded_session)
            self.populate_weather(year, loaded_session)
            self.populate_laps(year, loaded_session)
            self.populate_race_control_messages(year, loaded_session)
            self.populate_pos_data(year, loaded_session)
            self.populate_car_data(year, loaded_session)
            self.populate_telemetry(year, loaded_session)
        
    
    # Populate season data
    def populate_seasons(self, year:int) -> Season:
        self.season_obj, _ = Season.objects.get_or_create(year=year)
        
        self.stdout.write(self.style.SUCCESS(f"Season {year} created successfully!"))
        
        return self.season_obj
    
    
    # Populate circuit data
    def populate_circuit(self, session: Session) -> Circuit:
        self.circuit_obj, _ = Circuit.objects.get_or_create(
            name = session.session_info['Meeting']['Circuit']['ShortName'],
            rotation = session.get_circuit_info().rotation,
            country = session.session_info['Meeting']['Country']['Code'],
            location = session.session_info['Meeting']['Location']
        )
        self.stdout.write(self.style.SUCCESS(f"Circuit data for {session.session_info['Meeting']['Circuit']['ShortName']} created successfully!"))
        return self.circuit_obj
    
    # Populate schedule
    def populate_event(self, year:int, event) -> Event:
        self.event_obj, _ = Event.objects.get_or_create(
            season_year = self.season_obj,
            round_number = event["RoundNumber"],
            defaults = {
                "date_utc" : event["EventDate"],
                "name" : event["EventName"],
                'circuit' : self.circuit_obj,
                "format" : event["EventFormat"].replace("_", " ").title()
            }
        )
        self.stdout.write(self.style.SUCCESS(f"Event data for {year} created successfully!"))
        
        return self.event_obj


    # Populate tyre compounds
    def populate_tyre_compounds(self, year: int, session: Session) -> TyreCompounds:
        # Populates tyre compounds available each season and their colors
        # season = Season.objects.get(year=year)
        
        for name, color in plotting.get_compound_mapping(session).items():
            self.tyre_compounds_obj, _ = TyreCompounds.objects.get_or_create(
                season_year = self.season_obj,
                color = color,
                name = name
            )
        self.stdout.write(self.style.SUCCESS(f"Tyre compounds data for {year} created successfully!"))
        
        return self.tyre_compounds_obj
    
    
    # Populate constructors and constructor colors
    def populate_constructors(self, year: int, session: Session) -> tuple[Constructor, ConstructorColor]:
        teams = plotting.list_team_names(session)
        
        for team in teams:
            self.constructor_obj, _ = Constructor.objects.get_or_create(name = team)
            
            self.constructor_colors_obj, _ = ConstructorColor.objects.get_or_create(
                constructor = self.constructor_obj,
                season_year = self.season_obj,
                defaults = {
                    "color_official" : plotting.get_team_color(team, session, colormap="official"),
                    "color_fastf1" : plotting.get_team_color(team, session, colormap="fastf1")
                }
            )
        self.stdout.write(self.style.SUCCESS(f"Constructor data for {year} created successfully!"))
        
        return self.constructor_obj, self.constructor_colors_obj 
        
    
    # Populate drivers and drivers numbers
    def populate_drivers(self, year: int, session: Session) -> tuple[Driver, DriverRacingNumber]:
        for _, row in session.results.iterrows():
            self.driver_obj, _ = Driver.objects.get_or_create(
                first_name = row["FirstName"].split()[0],
                last_name = row["LastName"],
                abbreviation = row["Abbreviation"]
            )
            
            self.driver_racing_number_obj, _ = DriverRacingNumber.objects.get_or_create(
                driver = self.driver_obj,
                season_year = Season.objects.get(year = year),
                defaults = {"racing_number" : row["DriverNumber"]}
            )
        
        self.stdout.write(self.style.SUCCESS(f"Driver data for {year} {session.session_info['Meeting']['Name']} {session.session_info['Name']} created successfully!"))
        
        return self.driver_obj, self.driver_racing_number_obj
      
      
    # Populate sessions
    def populate_sessions(self, year: int, session: Session, event: Event, i: int) -> Session:
        
        scheduled = make_aware((event[f"Session{i}DateUtc"]), timezone.utc)
        actual = make_aware(session.session_info["StartDate"] - session.session_info["GmtOffset"], timezone.utc)
        end = make_aware(session.session_info["EndDate"] - session.session_info["GmtOffset"], timezone.utc)

        self.session_obj, _ = Session.objects.get_or_create(
            event = Event.objects.get(season_year = year, name = event["EventName"]),
            type = event[f"Session{i}"],
            defaults = {
                "scheduled_start_timestamp_utc" : scheduled,
                "actual_start_timestamp_utc" : actual,
                "end_timestamp_utc" : end
            }
        )
        
        self.stdout.write(self.style.SUCCESS(f"Session data for {year} {session.session_info['Meeting']['Name']} {session.session_info['Name']} created successfully!"))
        
        return self.session_obj
    
    
    # Populate results
    def populate_results(self, year:int, session: Session) -> Result:
        for _, row in session.results.iterrows():
            self.result_obj, _ = Result.objects.get_or_create(
                session=self.session_obj,
                driver=Driver.objects.get(first_name = row["FirstName"].split()[0], last_name = row["LastName"]),
                constructor=Constructor.objects.get(name = row["TeamName"]),
                defaults={
                    "position": row["Position"] if pd.notna(row["Position"]) else None,
                    "classified_position": row["ClassifiedPosition"],
                    "grid_position": row["GridPosition"] if pd.notna(row["GridPosition"]) else None,
                    "q1": row["Q1"].total_seconds() * 1000 if pd.notna(row["Q1"]) else None,
                    "q2": row["Q2"].total_seconds() * 1000 if pd.notna(row["Q2"]) else None,
                    "q3": row["Q3"].total_seconds() * 1000 if pd.notna(row["Q3"]) else None,
                    "time": row["Time"].total_seconds() * 1000 if pd.notna(row["Time"]) else None,
                    "status": row["Status"] if pd.notna(row["Status"]) else None,
                    "points": row["Points"] if pd.notna(row["Points"]) else None
                }
            )
            
        self.stdout.write(self.style.SUCCESS(f"Results data for {year} {session.session_info['Meeting']['Name']} {session.session_info['Name']} created successfully!"))
        
        return self.result_obj
    
    
    # Populate weather
    def populate_weather(self, year:int,  session: Session) -> None:
        for _, row in session.weather_data.iterrows():
            self.weather_obj, _ = Weather.objects.get_or_create(
                session = self.session_obj,
                time_delta = row["Time"].total_seconds() * 1000,
                defaults = {
                    "air_temp" : row["AirTemp"],
                    "track_temp" : row["TrackTemp"],
                    "rainfall" : row["Rainfall"],
                    "humidity" : row["Humidity"],
                    "air_pressure" : row["Pressure"],
                    "wind_speed" : row["WindSpeed"],
                    "wind_direction" : row["WindDirection"]
                }
            )
            
        self.stdout.write(self.style.SUCCESS(f"Weather data for {year} {session.session_info['Meeting']['Name']} {session.session_info['Name']} created successfully!"))
        
    
    # Populate laps
    def populate_laps(self, year:int, session: Session) -> Lap:
        for _, row in session.laps.iterrows():
            driver_name = plotting.get_driver_name(row["Driver"], session).split()
            first_name, last_name = driver_name[0], driver_name[-1]
            
            driver = Driver.objects.get(
                first_name=first_name,
                last_name=last_name
            )

            Lap.objects.get_or_create(
                session=self.session_obj,
                driver=driver,
                lap_number=row["LapNumber"],
                defaults={
                    "lap_time": row["LapTime"].total_seconds() * 1000 if pd.notna(row["LapTime"]) else None,
                    "stint": row["Stint"] if pd.notna(row["Stint"]) else None,
                    "pit_out_time": row["PitOutTime"].total_seconds() * 1000 if pd.notna(row["PitOutTime"]) else None,
                    "pit_in_time": row["PitInTime"].total_seconds() * 1000 if pd.notna(row["PitInTime"]) else None,
                    "sector_1_time": row["Sector1Time"].total_seconds() * 1000 if pd.notna(row["Sector1Time"]) else None,
                    "sector_2_time": row["Sector2Time"].total_seconds() * 1000 if pd.notna(row["Sector2Time"]) else None,
                    "sector_3_time": row["Sector3Time"].total_seconds() * 1000 if pd.notna(row["Sector3Time"]) else None,
                    "sector_1_session_time": row["Sector1SessionTime"].total_seconds() * 1000 if pd.notna(row["Sector1SessionTime"]) else None,
                    "sector_2_session_time": row["Sector2SessionTime"].total_seconds() * 1000 if pd.notna(row["Sector2SessionTime"]) else None,
                    "sector_3_session_time": row["Sector3SessionTime"].total_seconds() * 1000 if pd.notna(row["Sector3SessionTime"]) else None,
                    "speed_i1": row["SpeedI1"] if pd.notna(row["SpeedI1"]) else None,
                    "speed_i2": row["SpeedI2"] if pd.notna(row["SpeedI2"]) else None,
                    "speed_fl": row["SpeedFL"] if pd.notna(row["SpeedFL"]) else None,
                    "speed_st": row["SpeedST"] if pd.notna(row["SpeedST"]) else None,
                    "is_personal_best": bool(row["IsPersonalBest"]) if pd.notna(row["IsPersonalBest"]) else False,
                    "compound": row["Compound"] if pd.notna(row["Compound"]) else None,
                    "tyre_life": row["TyreLife"] if pd.notna(row["TyreLife"]) else None,
                    "fresh_tyre": bool(row["FreshTyre"]) if pd.notna(row["FreshTyre"]) else False,
                    "track_status": row["TrackStatus"] if pd.notna(row["TrackStatus"]) else None,
                    "position": row["Position"] if pd.notna(row["Position"]) else None,
                    "deleted": bool(row["Deleted"]) if pd.notna(row["Deleted"]) else False,
                    "deleted_reason": row["DeletedReason"] if pd.notna(row["DeletedReason"]) else None,
                    "fastf1_generated": bool(row["FastF1Generated"]) if pd.notna(row["FastF1Generated"]) else False,
                    "is_accurate": bool(row["IsAccurate"]) if pd.notna(row["IsAccurate"]) else False,
                }

            )
        
        self.stdout.write(self.style.SUCCESS(f"Laps data for {year} {session.session_info['Meeting']['Name']} {session.session_info['Name']} created successfully!"))
              

    # Populate race control messages
    def populate_race_control_messages(self, year:int, session: Session) -> None:
        for _, row in session.race_control_messages.iterrows():
            RaceControlMessage.objects.get_or_create(
                session = self.session_obj,
                lap = row["Lap"],
                date_time = make_aware(row["Time"], timezone.utc),
                defaults = {
                    "driver_number" : DriverRacingNumber.objects.get(racing_number = row["RacingNumber"], season_year = year) if pd.notna(row["RacingNumber"]) else None,
                    "category" : row["Category"],
                    "message" : row["Message"],
                    "status" : row["Status"],
                    "flag" : row["Flag"], 
                    "scope" : row["Scope"],
                    "sector" : row["Sector"] if pd.notna(row["Sector"]) else None
                }
            )
        
        self.stdout.write(self.style.SUCCESS(f"Race control messages data for {year} {session.session_info['Meeting']['Name']} {session.session_info['Name']} created successfully!"))


    # Populate position data
    def populate_pos_data(self, year:int, session: Session) -> None:
        position_data_bulk = []

        for driver in session.drivers:
            driver_laps = session.laps.pick_drivers(driver)
            
            if not driver_laps["LapNumber"].notna().any():
                self.stdout.write(self.style.NOTICE(f"No valid laps found for driver {driver}, skipping..."))
                continue

            max_lap = int(driver_laps["LapNumber"].max())
            
            driver_obj = Driver.objects.get(
                first_name = session.results[session.results["DriverNumber"] == driver]["FirstName"].iloc[0].split()[0],
                last_name = session.results[session.results["DriverNumber"] == driver]["LastName"].iloc[0]
            )
            
            self.stdout.write(self.style.NOTICE(f"Creating positional data for driver number {driver}..."))
            
            for lap_number in range(1, max_lap + 1):
                lap_data = driver_laps.pick_laps(lap_number)
                lap_obj = Lap.objects.filter(session = self.session_obj, lap_number=lap_number, driver=driver_obj).first()

                try:
                    pos_data = lap_data.get_pos_data()
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Skipping pos data lap {lap_number} for driver {driver} due to error: {e}"))
                    logger.warning(f"Skipping pos data lap {lap_number} for driver {driver} due to error: {e}")
                    continue
                
                self.stdout.write(self.style.NOTICE(f"Creating positional data for lap number {lap_number}..."))
                
                for _, row in pos_data.iterrows():
                    date = row["Date"]
                    if date and date.tzinfo is None:
                        date = make_aware(date)

                    session_time = row["SessionTime"]
                    if pd.notna(session_time):
                        session_time = session_time.to_pytimedelta()
                    else:
                        session_time = None

                    time = row["Time"]
                    time = time.total_seconds() * 1000 if pd.notna(time) else None

                    position_data_bulk.append(PositionData(
                        lap=lap_obj,
                        date=date,
                        status=row["Status"],
                        x=row["X"],
                        y=row["Y"],
                        z=row["Z"],
                        source=row["Source"],
                        time=time,
                        session_time=session_time
                    ))

        self.stdout.write(self.style.NOTICE(f"Populating tables..."))
        PositionData.objects.bulk_create(
            position_data_bulk,
            batch_size=1000,
            update_conflicts=True,
            update_fields=["status", "x", "y", "z", "source", "time", "session_time"],
            unique_fields=["lap", "date"]
        )
        
        self.stdout.write(self.style.SUCCESS(f"Positional data for {year} {session.session_info['Meeting']['Name']} {session.session_info['Name']} created successfully!"))
    
    
    # Populate car data
    def populate_car_data(self, year:int, session: Session) -> None:
        car_data_bulk = []
        
        for driver in session.drivers:
            driver_laps = session.laps.pick_drivers(driver)
            
            if not driver_laps["LapNumber"].notna().any():
                self.stdout.write(self.style.NOTICE(f"No valid laps found for driver {driver}, skipping..."))
                continue

            max_lap = int(driver_laps["LapNumber"].max())
            
            driver_obj = Driver.objects.get(
                first_name = session.results[session.results["DriverNumber"] == driver]["FirstName"].iloc[0].split()[0],
                last_name = session.results[session.results["DriverNumber"] == driver]["LastName"].iloc[0]
            )
            
            self.stdout.write(self.style.NOTICE(f"Creating car data for driver number {driver}..."))
            
            for lap_number in range(1, max_lap + 1):
                lap_data = driver_laps.pick_laps(lap_number)
                lap_obj = Lap.objects.filter(session=self.session_obj, lap_number=lap_number, driver=driver_obj).first()
                
                try:
                    car_data = lap_data.get_car_data()
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Skipping car data lap {lap_number} for driver {driver} due to error: {e}"))
                    logger.warning(f"Skipping car data lap {lap_number} for driver {driver} due to error: {e}")
                    continue
                self.stdout.write(self.style.NOTICE(f"Creating car data for lap number {lap_number}..."))
                
                for _, row in car_data.iterrows():
                    date = row["Date"]
                    if date and date.tzinfo is None:
                        date = make_aware(date)
                        
                    session_time = row["SessionTime"]
                    if pd.notna(session_time):
                        session_time = session_time.to_pytimedelta()
                    else:
                        session_time = None
                        
                    time = row["Time"].total_seconds() * 1000 if pd.notna(row["Time"]) else None
                
                    car_data_bulk.append(CarData(
                        lap = lap_obj,
                        date = date,
                        speed = row["Speed"],
                        rpm = row["RPM"],
                        gear = row["nGear"],
                        throttle = row["Throttle"],
                        brake = row["Brake"],
                        drs = row["DRS"],
                        source = row["Source"],
                        time = time,
                        session_time = session_time,
                    ))
        
        self.stdout.write(self.style.NOTICE(f"Populating tables..."))
        CarData.objects.bulk_create(
            car_data_bulk,
            batch_size=1000,
            update_conflicts=True,
            update_fields=["speed", "rpm", "gear", "throttle", "brake", "drs", "source", "time", "session_time"],
            unique_fields=["lap", "date"]
        )
        
        self.stdout.write(self.style.SUCCESS(f"Car data for {year} {session.session_info['Meeting']['Name']} {session.session_info['Name']} created successfully!"))
        
    
    # Populate telemetry
    def populate_telemetry(self, year:int, session: Session) -> None:
        telemetry_data_bulk = []
        
        for driver in session.drivers:
            driver_laps = session.laps.pick_drivers(driver)
            
            if not driver_laps["LapNumber"].notna().any():
                self.stdout.write(self.style.NOTICE(f"No valid laps found for driver {driver}, skipping..."))
                continue

            max_lap = int(driver_laps["LapNumber"].max())
            
            driver_obj = Driver.objects.get(
                first_name = session.results[session.results["DriverNumber"] == driver]["FirstName"].iloc[0].split()[0],
                last_name = session.results[session.results["DriverNumber"] == driver]["LastName"].iloc[0]
            )
            
            self.stdout.write(self.style.NOTICE(f"Creating telemetry data for driver number {driver}..."))
            
            for lap_number in range(1, max_lap + 1):
                lap_data = driver_laps.pick_laps(lap_number)
                lap_obj = Lap.objects.filter(session=self.session_obj, lap_number=lap_number, driver=driver_obj).first()
                
                try:
                    telemetry_data = lap_data.get_telemetry().add_differential_distance().add_distance().add_driver_ahead().add_relative_distance()
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Skipping telemetry lap {lap_number} for driver {driver} due to error: {e}"))
                    logger.warning(f"Skipping telemetry lap {lap_number} for driver {driver} due to error: {e}")
                    continue
                self.stdout.write(self.style.NOTICE(f"Creating telemetry data for lap number {lap_number}..."))
                
                for _, row in telemetry_data.iterrows():
                    date = row["Date"]
                    if date and date.tzinfo is None:
                        date = make_aware(date)
                        
                    session_time = row["SessionTime"].to_pytimedelta() if pd.notna(row["SessionTime"]) else None
                    
                    time = row["Time"].total_seconds() * 1000 if pd.notna(row["Time"]) else None
                    
                    telemetry_data_bulk.append(Telemetry(
                        lap = lap_obj,
                        date = date,
                        session_time = session_time,
                        time = time,
                        rpm = row["RPM"],
                        speed = row["Speed"],
                        n_gear = row["nGear"],
                        throttle = row["Throttle"],
                        brake = row["Brake"],
                        drs = row["DRS"],
                        source = row["Source"],
                        status = row["Status"],
                        x = row["X"],
                        y = row["Y"],
                        z = row["Z"],
                        differential_distance = row["DifferentialDistance"],
                        distance = row["Distance"],
                        distance_to_driver_ahead = row["DistanceToDriverAhead"],
                        relative_distance = row["RelativeDistance"]
                    ))
        
        self.stdout.write(self.style.NOTICE(f"Populating tables..."))
        Telemetry.objects.bulk_create(
            telemetry_data_bulk,
            batch_size=1000,
            update_conflicts=True,
            update_fields=["session_time", "time", "rpm", "speed", "n_gear",
                           "throttle", "brake", "drs", "source", "status",
                           "x", "y", "z", "differential_distance", "distance", "distance_to_driver_ahead", "relative_distance"],
            unique_fields=["lap", "date"]
        )
        
        self.stdout.write(self.style.SUCCESS(f"Telemetry data for {year} {session.session_info['Meeting']['Name']} {session.session_info['Name']} created successfully!"))