from . import format_lap_time, add_watermark, drs_to_boolean

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import matplotlib.patches as mpatches
import seaborn as sns

import pandas as pd
import numpy as np

import io
import base64

from static_data.models import Driver, Schedule, Session, Constructor, ConstructorColor, Telemetry, Result, Lap

def plot_name(name):
    def decorator(func):
        func.plot_name = name
        return func
    return decorator



class TelemetryVisuals:
    """
    Generate visualizations of lap time performance by constructor.
    
    Attributes:
        year (int): Season year.
        event_id (int): ID of the event.
        session_id (int): ID of the session.
        
    """
    
    PLOT_METHODS = ['telemetry_plot']
    
    def __init__(self, year: int, event_id: int, session_id: int, driver_id: int, lap_id: int):
        # Initialise basic parameters
        self.year = year
        self.event_id = event_id
        self.session_id = session_id
        self.driver_id = driver_id
        self.lap_id = lap_id
        
        # Load, process data and set general plot properties
        self._load_data()
        self._process_data()
        # self._set_general_plot_properties()
        
    def _load_data(self) -> None:
        """Fetch all necessary raw data from the database"""
        self._raw_driver_details = Driver.objects.filter(id=self.driver_id).values('id', 'abbreviation')
        self._raw_event_details = Schedule.objects.get(id=self.event_id)
        self._raw_session_details = Session.objects.get(id=self.session_id)
        self._raw_results = Result.objects.filter(session=self.session_id, driver=self.driver_id).values('constructor')
        self._raw_constructor = Constructor.objects.values()
        self._raw_telemetry = Telemetry.objects.filter(lap=self.lap_id).values(
            'time', 'rpm', 'speed', 'n_gear', 'throttle', 'brake', 'drs', 'distance')
    
    def _process_data(self, remove_outliers: bool = True) -> None:
        """Process fetched data and make it a pandas dataframe"""
        telemetry_df = pd.DataFrame(self._raw_telemetry)
        telemetry_df['drs'] = telemetry_df['drs'].apply(drs_to_boolean)
    
        constructor_id = self._raw_results[0]['constructor']
        
        self.lap_number = Lap.objects.filter(id=self.lap_id).values_list('lap_number', flat=True)[0]
        self.constructor_color = ConstructorColor.objects.filter(constructor=constructor_id).values_list('color_fastf1', flat=True)[0]

        self.driver_abbreviation = self._raw_driver_details[0]['abbreviation']

        self.telemetry_df = telemetry_df
        
        
    # TODO change the way driver names is added to the title of the plot make it a name instead of a abbreviation
    @plot_name("telemetry_plot")
    def telemetry_plot(self) -> str:
        label = self.driver_abbreviation
        color = self.constructor_color
        fig, ax = plt.subplots(6, figsize = [10,12], dpi=300, gridspec_kw={'height_ratios': [4, 2, 1, 1, 3, 1]}, constrained_layout=False)
        # Speed trace
        ax[0].plot(self.telemetry_df["distance"], self.telemetry_df["speed"], label=label, color=color)
        ax[0].set_ylabel('Speed (km/h)', color='white')
        ax[0].set_yticks([350, 300, 250, 200, 150, 100, 50, 0])
        ax[0].yaxis.grid(color='#3E4041', linestyle='--', linewidth=1)
        
        # Throttle Trace
        ax[1].plot(self.telemetry_df["distance"], self.telemetry_df["throttle"], label=label, color=color)
        ax[1].set_ylabel('Throttle (%)', color='white')

        # Brake Trace
        ax[2].plot(self.telemetry_df["distance"], self.telemetry_df["brake"], label=label, color=color)
        ax[2].set_ylabel('Brake', color='white')
        ax[2].set_yticks([0, 1])
        ax[2].set_yticklabels(['OFF', 'ON'])

        # Gear Trace
        ax[3].plot(self.telemetry_df["distance"], self.telemetry_df["n_gear"], label=label, color=color)
        ax[3].set_ylabel('Gear', color='white')
        ax[3].set_yticks([2, 4, 6, 8])
        ax[3].set_ylim([1, 9])
        ax[3].yaxis.grid(color='#3E4041', linestyle='--', linewidth=1)

        # RPM Trace
        ax[4].plot(self.telemetry_df["distance"], self.telemetry_df["rpm"], label=label, color=color)
        ax[4].set_ylabel('RPM', color='white')

        # DRS Trace
        ax[5].plot(self.telemetry_df["distance"], self.telemetry_df["drs"], label=label, color=color)
        ax[5].set_ylabel('DRS', color='white')
        ax[5].set_xlabel('Lap distance (meters)', color='white')
        ax[5].set_yticks([False, True])
        ax[5].set_yticklabels(['OFF', 'ON'])
        
        # Title and subtitle
        ax[0].set_title("Telemetry Data", fontsize=20, color='white', fontweight='bold', y=1.07)
        ax[0].text(0.5, 1.03, f"{self._raw_session_details.actual_start_timestamp_utc.date()} | {self._raw_event_details.name} | {self._raw_session_details.type} | {label} | Lap: {self.lap_number}",
                ha='center', fontsize=10, color='white', transform=ax[0].transAxes)
        
        for axis in ax:
            axis.set_xlim(left=0)
    
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