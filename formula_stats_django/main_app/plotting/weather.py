from . import format_lap_time, add_watermark

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import pandas as pd

import io
import base64

from main_app.models import Schedule, Session, Weather



# Decorator to add name to the plots
def plot_name(name):
    def decorator(func):
        func.plot_name = name
        return func
    return decorator



class WeatherVisuals:
    """
    Generate weather visuals to chosen sesion
    
    Attributes:
        year (int): Season year.
        event_id (int): ID of the event.
        session_id (int): ID of the session.
    """
    PLOT_METHODS = ['plot_weather_data']
    
    def __init__(self, year: int, event_id: int, session_id: int):
    
        self.year = year
        self.event_id = event_id
        self.session_id = session_id
        
        # Load, process data and set general plot properties
        self._load_data()
        self._process_data()
        self._set_general_plot_properties()
        
    def _load_data(self):
        """Fetch all necessary raw data from the database"""
        self._raw_weather = Weather.objects.filter(session=self.session_id).values()
        self._raw_event_details = Schedule.objects.get(id=self.event_id)
        self._raw_session_details = Session.objects.get(id=self.session_id)
    
    def _process_data(self):
        """Process fetched data and make it a pandas dataframe"""
        self.weather_df = pd.DataFrame(self._raw_weather)
        self.weather_df['time_m'] = self.weather_df['time_delta'] // 60000
    
    def _set_general_plot_properties(self):
        """Set general plot properties for all plots in Team Lap Visuals"""
        # Set plots to dark background
        plt.style.use('dark_background')
    
    
    
    @plot_name('weather_data')
    def plot_weather_data(self):
        elements_to_plot = ["Air Temp", "Track Temp", "Rainfall", "Wind Speed", "Wind Direction", "Air Pressure", "Relative Humidity"]
        
        plot_data = {
        "Air Temp": {"data": self.weather_df["air_temp"], "ylabel": "Air Temp (°C)", "title": "Air Temperature", "color": 'r'},
        "Track Temp": {"data": self.weather_df["track_temp"], "ylabel": "Track Temp (°C)", "title": "Track Temperature", "color": 'm'},
        "Rainfall": {"data": self.weather_df["rainfall"], "ylabel": "Rainfall", "title": "Rainfall", "color": 'c', "yticks": [0, 1], "yticklabels": ["No", "Yes"]},
        "Wind Direction": {"data": self.weather_df["wind_direction"], "ylabel": "Wind Direction (°)", "title": "Wind Direction", "color": 'y'},
        "Wind Speed": {"data": self.weather_df["wind_speed"], "ylabel": "Wind Speed (m/s)", "title": "Wind Speed", "color": 'orange'},
        "Air Pressure": {"data": self.weather_df["air_pressure"], "ylabel": "Air Press (mbar)", "title": "Air Pressure", "color": 'g'},
        "Relative Humidity": {"data": self.weather_df["humidity"], "ylabel": "Rel Humid (%)", "title": "Humidity", "color": 'b'}
        }

        num_plots = len(elements_to_plot)
        
        if num_plots > 2:
            height_ratios = [
                1.5 if elem in ["Air Temp", "Track Temp", "Wind Speed"] else 
                0.5 if elem in ["Rainfall"] else
                1 if elem in ["Air Pressure", "Relative Humidity"] else
                1 for elem in elements_to_plot
            ]
        else:
            height_ratios = [
                1.5 for elem in elements_to_plot
            ]

        # Adjust number of rows based on selected elements
        fig, ax = plt.subplots(num_plots, gridspec_kw={'height_ratios': height_ratios}, constrained_layout=True, figsize=(12, 2 * num_plots), dpi=300)

        for i, element in enumerate(elements_to_plot):
            data = plot_data[element]
            ax[i].plot(self.weather_df["time_m"], data["data"], color=data["color"], linewidth=2)
            ax[i].set_ylabel(data["ylabel"], color='white', fontsize=12)
            
            # Custom ticks for Rainfall
            if element == "Rainfall":
                ax[i].set_yticks(data["yticks"])
                ax[i].set_yticklabels(data["yticklabels"], fontsize=12)
            
            ax[i].grid(True, linestyle='--', alpha=0.6)
            ax[i].tick_params(axis='both', labelsize=10)

        # Title and subtitle
        ax[0].set_title("Weather Data", fontsize=20, color='white', fontweight='bold', y=1.18)
        ax[0].text(0.5, 1.08, f"{self._raw_session_details.actual_start_timestamp_utc.date()} | {self._raw_event_details.name} | {self._raw_session_details.type}",
                ha='center', fontsize=10, color='white', transform=ax[0].transAxes)
        
        # General settings
        # plt.grid(color='darkgray', linestyle='dashed', linewidth=0.5, axis='y')
        plt.tight_layout()

        # Add the watermark
        add_watermark(fig, alpha=0.35)

        # Save plot to BytesIO
        img_io = io.BytesIO()
        plt.savefig(img_io, format='png')
        img_io.seek(0)

        # Convert to base64
        plot_data = base64.b64encode(img_io.getvalue()).decode("utf-8")
        plt.close(fig)

        return plot_data