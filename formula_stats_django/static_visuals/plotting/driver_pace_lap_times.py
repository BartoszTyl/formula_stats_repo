from . import format_lap_time, add_watermark, SNS_BOXPLOT_STYLE

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

from static_data.models import Result, Lap, ConstructorColor, Constructor, Schedule, Session, TyreCompounds, Driver

def plot_name(name):
    def decorator(func):
        func.plot_name = name
        return func
    return decorator


class DriverLapVisuals:
    """
    Generate visualizations of lap time performance by constructor.
    
    Attributes:
        year (int): Season year.
        event_id (int): ID of the event.
        session_id (int): ID of the session.
        
    """
    
    PLOT_METHODS = ['lap_time_distribution']
    
    def __init__(self, year: int, event_id: int, session_id: int):
        # Initialise basic parameters
        self.year = year
        self.event_id = event_id
        self.session_id = session_id
        
        # Load, process data and set general plot properties
        self._load_data()
        self._process_data()
        # self._set_general_plot_properties()
        
    def _load_data(self) -> None:
        """Fetch all necessary raw data from the database"""
        self._raw_laps = Lap.objects.filter(session=self.session_id).values("lap_time", "driver")
        self._raw_results = Result.objects.filter(session=self.session_id).values("id", "position","classified_position", "constructor", "driver")
        self._raw_driver_details = Driver.objects.values('id', 'abbreviation')
        self._raw_event_details = Schedule.objects.get(id=self.event_id)
        self._raw_session_details = Session.objects.get(id=self.session_id)
        self._raw_constructor = Constructor.objects.values()
        self._raw_constructor_color = ConstructorColor.objects.filter(season_year=self.year).values("constructor", "color_fastf1")
        self._raw_tyre_compounds = TyreCompounds.objects.filter(season_year=self.year).values('name', 'color')

    def _process_data(self, remove_outliers: bool = True) -> None:
        """Process fetched data and make it a pandas dataframe"""
        # Dictionary {'constructor_id': 'constructor_name'}
        team_name_dict = {entry['id']: entry['name'] for entry in self._raw_constructor}
        
         # Dictionary {"team name": "team color"}
        team_colors_dict = {team_name_dict.get(
            entry["constructor"], entry["constructor"]): entry["color_fastf1"] for entry in self._raw_constructor_color}
        
        # Dictionary {"driver": "team name"}
        driver_constructor_dict = {entry["driver"]: entry["constructor"] for entry in self._raw_results}
        
        # Dictionary {'driver_id': 'abbreviation'}
        driver_id_abbreviation_dict = {entry['id']: entry['abbreviation'] for entry in self._raw_driver_details}
        
        # DataFrame with laps data
        lap_data = []
        for lap in self._raw_laps:
            driver = lap["driver"]
            constructor = driver_constructor_dict.get(driver)
            constructor_name = team_name_dict.get(constructor)
            if constructor:
                lap_data.append({
                    "constructor": constructor,
                    'constructor_name': constructor_name,
                    'driver': driver,
                    "lap_time": lap["lap_time"] if isinstance(lap["lap_time"], int) else lap["lap_time"],
                })
        
        laps_df = pd.DataFrame(lap_data)
        
        # Remove outliers
        if remove_outliers:
            Q1 = laps_df["lap_time"].quantile(0.25)
            Q3 = laps_df["lap_time"].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            laps_df = laps_df[(laps_df["lap_time"] >= lower_bound) & (laps_df["lap_time"] <= upper_bound)]
        
        # Calculate driver median, fast, slow laps and team order based on the median laps
        self.driver_medians = laps_df.groupby("driver")["lap_time"].median().sort_values()
        self.driver_mins = laps_df.groupby("driver")["lap_time"].min().sort_values()
        self.driver_maxs = laps_df.groupby("driver")["lap_time"].max().sort_values()
        self.driver_order = self.driver_medians.index
        
        # Create results_df DataFrame
        results_df = pd.DataFrame(list(self._raw_results))
        
        # Make dataframes and dicts accessible by the rest of the class
        self.laps_df = laps_df
        self.results_df = results_df
        
        self.team_colors_dict = team_colors_dict
        self.driver_id_abbreviation_dict = driver_id_abbreviation_dict
        self.driver_constructor_dict = driver_constructor_dict
        
        
        
    @plot_name('driver_lap_time_distribution')
    def lap_time_distribution(self) -> str:
        fig, ax = plt.subplots(figsize=(12.8, 8), dpi=300)
        sns.boxplot(
            data=self.laps_df,
            x='driver',
            y='lap_time',
            hue='constructor_name',
            order=self.driver_order,
            palette=self.team_colors_dict,
            **SNS_BOXPLOT_STYLE
        )
        
        # X-axis customization
        # avg_lap_times = self.driver_medians.reindex(self.driver_order).dropna()
        tick_labels = [
                f"{self.driver_id_abbreviation_dict[driver]}\n{format_lap_time(self.driver_medians[driver])}"
                for driver in self.driver_order
            ]
        
        ax.set_xlabel("Driver & Median Time (s)", fontsize=8)
        ax.set_xticks(ticks=np.arange(len(tick_labels)), labels=tick_labels, rotation=45, fontsize=10)
        
        
        # Y-axis customization
        ax.set_ylabel("Lap Time (s)", fontsize=10)
        plt.gca().yaxis.set_major_formatter(FuncFormatter(lambda x, _: int(x / 1000)))
        plt.yticks(fontsize=10)


        # Create a team-based legend
        unique_teams = self.laps_df[['constructor_name']].drop_duplicates().sort_values(by="constructor_name")

        team_legend = [
            mpatches.Patch(
                facecolor=self.team_colors_dict.get(team, "#FFFFFF"),
                label=team
            )
            for team in unique_teams["constructor_name"]
        ]

        ax.legend(handles=team_legend, title="Teams", loc='upper left', fontsize=9, title_fontsize=10)


        # Title and subtitle
        ax.set_title("Drivers Lap Time Distribution", fontsize=20, color='white', fontweight='bold', y=1.04)
        ax.text(0.5, 1.017, f"{self._raw_session_details.actual_start_timestamp_utc.date()} | {self._raw_event_details.name} | {self._raw_session_details.type}",
                ha='center', fontsize=10, color='white', transform=ax.transAxes)
        
        
        # General settings
        plt.grid(color='darkgray', linestyle='dashed', linewidth=0.5, axis='y')
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