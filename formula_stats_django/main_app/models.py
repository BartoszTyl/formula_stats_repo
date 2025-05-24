from django.db import models
"""
Order in which the models need to populated with the data to ensure proper functionality
of the foreign keys.

1. Season: No dependencies, so it should be first.
2. Schedule: Depends on Season.
3. TyreCompounds: Depends on Season, so insert after Season.
4. Constructor: No dependencies, can be inserted after Season.
5. ConstructorColor: Depends on Constructor and Season, so insert after both. 
6. Driver: No dependencies, can be inserted after Constructor.
7. DriverRacingNumber: Depends on Driver and Season, so insert after both.
8. Session: Depends on Event, so insert after Event.
9. Result: Depends on Session, Driver, and Constructor, so insert after all three.
10. Weather: Depends on Session, so insert after Session.
11. Lap: Depends on Session and Driver, so insert after both.
12. Telemetry: Depends on Lap, so insert after Lap.
13. RaceControlMessage: Depends on Lap, so insert after Lap.
14. CarData: Depends on Lap, so insert after Lap.
15. PositionData: Depends on Lap, so insert after Lap.

"""

# TODO Change the 'constructor_name' in ConstructorColor model to 'constructor'
# TODO Add error logging when importing
# TODO Change the format in the Schedule model from charfield to integer or bool (0 - convetional, 1 - sprint)
# TODO Change the name of the column in Constructor model from constructor_name to constructor (it shows id not the name)


class Season(models.Model):
    year = models.IntegerField(primary_key=True)  # Year
    
    class Meta:
        db_table = "seasons"


class Schedule(models.Model):
    season_year = models.ForeignKey(Season,  on_delete=models.CASCADE)
    round_number = models.IntegerField()
    country = models.CharField(max_length=3, null=True)
    location = models.CharField(max_length=60)
    date_utc = models.DateField()
    name = models.CharField()
    format = models.CharField()
    
    class Meta:
        db_table = "schedules"
    
        
class TyreCompounds(models.Model):
    name = models.CharField(max_length=25)
    color = models.CharField(max_length=7, help_text="Hexadecimal color code")
    season_year = models.ForeignKey(Season, on_delete=models.CASCADE)

    class Meta:
        db_table = "tyre_compounds"


class Constructor(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        db_table = "constructors"


class ConstructorColor(models.Model):
    constructor_name = models.ForeignKey(Constructor, on_delete=models.CASCADE)
    season_year = models.ForeignKey(Season, on_delete=models.CASCADE)
    color_official = models.CharField(max_length=7, help_text="Hexadecimal color code")
    color_fastf1 = models.CharField(max_length=7, help_text="Hexadecimal color code")

    class Meta:
        db_table = "constructors_color"


class Driver(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    abbreviation = models.CharField(max_length=3, help_text="Official abbreviation")

    class Meta:
        db_table = "drivers"
        

class DriverRacingNumber(models.Model):
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    racing_number = models.IntegerField()
    season_year = models.ForeignKey(Season, on_delete=models.CASCADE)

    class Meta:
        db_table = "driver_racing_numbers"
        unique_together = ('driver', 'season_year')


class Session(models.Model):
    event = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    type = models.CharField(max_length=50)
    scheduled_start_timestamp_utc = models.DateTimeField()
    actual_start_timestamp_utc = models.DateTimeField()
    end_timestamp_utc = models.DateTimeField()
    
    class Meta:
        db_table = "sessions"


class Lap(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    driver = models.ForeignKey(Driver, on_delete=models.PROTECT)
    lap_number = models.IntegerField()
    lap_time = models.IntegerField(help_text="Milliseconds", null=True)
    stint = models.IntegerField(null=True)
    pit_out_time = models.IntegerField(null=True)
    pit_in_time = models.IntegerField(null=True)
    sector_1_time = models.IntegerField(null=True)
    sector_2_time = models.IntegerField(null=True)
    sector_3_time = models.IntegerField(null=True)
    sector_1_session_time = models.IntegerField(null=True)
    sector_2_session_time = models.IntegerField(null=True)
    sector_3_session_time = models.IntegerField(null=True)
    speed_i1 = models.FloatField(null=True)
    speed_i2 = models.FloatField(null=True)
    speed_fl = models.FloatField(null=True)
    speed_st = models.FloatField(null=True)
    is_personal_best = models.BooleanField()
    compound = models.CharField(max_length=50)
    tyre_life = models.IntegerField(null=True)
    fresh_tyre = models.BooleanField()
    track_status = models.CharField(max_length=255)
    position = models.IntegerField(null=True)
    deleted = models.BooleanField(default=False)
    deleted_reason = models.TextField(null=True, blank=True)
    fastf1_generated = models.BooleanField()
    is_accurate = models.BooleanField()
    
    class Meta:
        db_table = "laps"


class Telemetry(models.Model):
    lap = models.ForeignKey(Lap, on_delete=models.CASCADE)
    date = models.DateTimeField(null=True)
    session_time = models.DurationField(null=True)
    time = models.IntegerField(null=True)
    rpm = models.FloatField(null=True)
    speed = models.FloatField(null=True)
    n_gear = models.IntegerField(null=True)
    throttle = models.FloatField(null=True)
    brake = models.BooleanField(null=True)
    drs = models.CharField(null=True)
    source = models.CharField(max_length=100, null=True)
    status = models.CharField(null=True)
    x = models.FloatField(null=True)
    y = models.FloatField(null=True)
    z = models.FloatField(null=True)
    differential_distance = models.FloatField(null=True)
    distance = models.FloatField(null=True)
    driver_ahead = models.IntegerField(null=True)
    distance_to_driver_ahead = models.FloatField(null=True)
    relative_distance = models.FloatField(null=True)
    
    class Meta:
        db_table = "telemetry"
        constraints = [
        models.UniqueConstraint(fields=["lap", "date"], name="unique_lap_datetime_telemetry_data")
        ]
        indexes = [
            models.Index(fields=["lap"], name="idx_telemetry_lap")
        ]


class Result(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    driver = models.ForeignKey(Driver, on_delete=models.PROTECT)
    constructor = models.ForeignKey(Constructor, on_delete=models.PROTECT)
    position = models.IntegerField(null=True)
    classified_position = models.CharField(max_length=2, null=True)
    grid_position = models.IntegerField(null=True)
    q1 = models.IntegerField(null=True, blank=True)
    q2 = models.IntegerField(null=True, blank=True)
    q3 = models.IntegerField(null=True, blank=True)
    time = models.IntegerField(null=True)
    status = models.CharField(null=True)
    points = models.FloatField(null=True)
    
    class Meta:
        db_table = "results"


class Weather(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    time_delta = models.IntegerField()
    air_temp = models.FloatField()
    track_temp = models.FloatField()
    rainfall = models.BooleanField()
    humidity = models.FloatField()
    air_pressure = models.FloatField()
    wind_speed = models.FloatField()
    wind_direction = models.FloatField()
    
    class Meta:
        db_table = "weather"


class RaceControlMessage(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, null=True)
    driver_number = models.ForeignKey(DriverRacingNumber, on_delete=models.CASCADE, null=True)
    lap = models.IntegerField(null=True)
    date_time = models.DateTimeField()
    category = models.CharField(max_length=100)
    message = models.TextField()
    status = models.CharField(max_length=100, null=True)
    flag = models.CharField(max_length=50, null=True)
    scope = models.CharField(max_length=100, null=True)
    sector = models.IntegerField(null=True)

    class Meta:
        db_table = "race_control_msgs"


class CarData(models.Model):
    lap = models.ForeignKey(Lap, on_delete=models.CASCADE)
    date = models.DateTimeField()
    speed = models.IntegerField()
    rpm = models.IntegerField()
    gear = models.IntegerField()
    throttle = models.IntegerField()
    brake = models.BooleanField()
    drs = models.IntegerField()
    source = models.CharField(max_length=100, null=True)
    time = models.IntegerField(null=True)
    session_time = models.DurationField(null=True)
    
    class Meta:
        db_table = "car_data"
        constraints = [
        models.UniqueConstraint(fields=["lap", "date"], name="unique_lap_datetime_car_data")
        ]
        indexes = [
            models.Index(fields=["lap"], name="idx_car_data_lap")
        ]


class PositionData(models.Model):
    lap = models.ForeignKey(Lap, on_delete=models.CASCADE)
    date = models.DateTimeField()
    status = models.CharField(max_length=20)
    x = models.IntegerField()
    y = models.IntegerField()
    z = models.IntegerField()
    source = models.CharField(max_length=100, null=True)
    time = models.IntegerField(null=True)
    session_time = models.DurationField(null=True)
    
    class Meta:
        db_table = "pos_data"
        constraints = [
        models.UniqueConstraint(fields=["lap", "date"], name="unique_lap_datetime_pos_data")
        ]
        indexes = [
            models.Index(fields=["lap"], name="idx_pos_data_lap")
        ]
