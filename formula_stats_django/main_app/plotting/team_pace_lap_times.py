from . import format_lap_time, add_watermark, SNS_BOXPLOT_STYLE

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import seaborn as sns

import pandas as pd
import numpy as np

import io
import base64

from main_app.models import Result, Lap, ConstructorColor, Constructor, Schedule, Session, TyreCompounds

def plot_name(name):
    def decorator(func):
        func.plot_name = name
        return func
    return decorator


class TeamLapVisuals:
    """
    Generate visualizations of lap time performance by constructor.
    
    Attributes:
        year (int): Season year.
        event_id (int): ID of the event.
        session_id (int): ID of the session.
        
    """
    
    PLOT_METHODS = ['lap_time_distribution',
                    'avg_lap_pace_comparison',
                    'fast_lap_pace_comparison']
    
    def __init__(self, year: int, event_id: int, session_id: int):
        # Initialise basic parameters
        self.year = year
        self.event_id = event_id
        self.session_id = session_id
        
        # Load, process data and set general plot properties
        self._load_data()
        self._process_data()
        self._set_general_plot_properties()
        
    def _load_data(self) -> None:
        """Fetch all necessary raw data from the database"""
        self._raw_laps = Lap.objects.filter(session=self.session_id).values("lap_time", "driver", "compound")
        self._raw_results = Result.objects.filter(session=self.session_id).values("id", "position","classified_position", "constructor", "driver")
        self._raw_event_details = Schedule.objects.get(id=self.event_id)
        self._raw_session_details = Session.objects.get(id=self.session_id)
        self._raw_constructor = Constructor.objects.values("id", "name")
        self._raw_constructor_color = ConstructorColor.objects.filter(season_year=self.year).values("constructor_name", "color_fastf1")
        

    def _process_data(self, remove_outliers: bool = True) -> None:
        """Process fetched data and make it a pandas dataframe"""
        # Dictionary {"id": "team name"}
        team_names_dict = {entry["id"]: entry["name"] for entry in self._raw_constructor}
        
        # Dictionary {"team name": "team color"}
        team_colors_dict = {team_names_dict.get(
            entry["constructor_name"], entry["constructor_name"]): entry["color_fastf1"] for entry in self._raw_constructor_color}
        
        # Dictionary {"driver": "team name"}
        driver_constructor_dict = {entry["driver"]: entry["constructor"] for entry in self._raw_results}
        
        
        # DataFrame with laps data
        lap_data = []
        for lap in self._raw_laps:
            driver = lap["driver"]
            constructor = driver_constructor_dict.get(driver)
            if constructor:
                lap_data.append({
                    "constructor": constructor,
                    "lap_time": lap["lap_time"] if isinstance(lap["lap_time"], int) else lap["lap_time"],
                })
        
        laps_df = pd.DataFrame(lap_data)
        laps_df["constructor"] = laps_df["constructor"].map(team_names_dict)

        
        # Remove outliers
        if remove_outliers:
            Q1 = laps_df["lap_time"].quantile(0.25)
            Q3 = laps_df["lap_time"].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            laps_df = laps_df[(laps_df["lap_time"] >= lower_bound) & (laps_df["lap_time"] <= upper_bound)]
        
        # Calculate team median, fast, slow laps and team order based on the median laps
        self.team_medians = laps_df.groupby("constructor")["lap_time"].median().sort_values()
        self.team_mins = laps_df.groupby("constructor")["lap_time"].min().sort_values()
        self.team_maxs = laps_df.groupby("constructor")["lap_time"].max().sort_values()
        self.team_order = self.team_medians.index
    
        # Create results_df DataFrame
        results_df = pd.DataFrame(list(self._raw_results))
        
        # Create additional columns in results_df (constructor_name, constructor_color, constructor_avg_lap, constructor_fast_lap)
        results_df["constructor_name"] = results_df["constructor"].map(team_names_dict)
        results_df["constructor_color"] = results_df["constructor_name"].map(team_colors_dict)
        results_df["constructor_avg_lap"] = results_df["constructor_name"].map(self.team_medians)
        results_df["constructor_fast_lap"] = results_df["constructor_name"].map(self.team_mins)
        # Calculate percentage difference for avg lap
        results_df["perc_diff_avg_lap"] = (
            ((results_df["constructor_avg_lap"] - results_df["constructor_avg_lap"].min()) / results_df["constructor_avg_lap"]) * 100).round(2)
        # Calculate percentage difference for fast lap
        results_df["perc_diff_fast_lap"] = (
            ((results_df["constructor_fast_lap"] - results_df["constructor_fast_lap"].min()) / results_df["constructor_fast_lap"]) * 100).round(2)
        
        
        
        # Make dataframes and dicts accessible by the rest of the class
        self.laps_df = laps_df
        self.team_colors_dict = team_colors_dict
        self.results_df = results_df
        
        
        
    def _set_general_plot_properties(self):
        """Set general plot properties for all plots in Team Lap Visuals"""
        # Set plots to dark background
        plt.style.use('dark_background')
        
        
        
    @plot_name("team_lap_times_distribution")
    def lap_time_distribution(self) -> str:
        # Create the plot
        fig, ax = plt.subplots(figsize=(12.8, 9), dpi=300)
        sns.boxplot(
            data=self.laps_df,
            x="constructor",
            y="lap_time",
            hue="constructor",
            order=self.team_order,
            palette=self.team_colors_dict,
            **SNS_BOXPLOT_STYLE
            )
        
        # X-axis customization
        avg_lap_times = self.team_medians.reindex(self.team_order).dropna()
        tick_labels = [f"{team} \n {format_lap_time(avg_lap_time)}" for team, avg_lap_time in zip(avg_lap_times.index, avg_lap_times)]
        
        ax.set_xlabel("Team & Median Time (s)", fontsize=10)
        ax.set_xticks(ticks=np.arange(len(tick_labels)), labels=tick_labels, rotation=25, fontsize=10)
        
        # Y-axis customization
        ax.set_ylabel("Lap Time (s)", fontsize=10)
        plt.gca().yaxis.set_major_formatter(FuncFormatter(lambda x, _: int(x / 1000)))
        plt.yticks(fontsize=10)
        
        # Title and subtitle
        ax.set_title("Teams Lap Time Distribution", fontsize=20, color='white', fontweight='bold', y=1.05)
        ax.text(0.5, 1.02, f"{self._raw_session_details.actual_start_timestamp_utc.date()} | {self._raw_event_details.name} | {self._raw_session_details.type}",
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
    
    
    
    @plot_name("team_avg_pace_comparison")
    def avg_lap_pace_comparison(self) -> str:
        results_df = self.results_df.groupby("constructor_name").agg({
                "perc_diff_avg_lap": 'first',
                "constructor_avg_lap": 'first',
                "constructor_color": 'first'
            }).reset_index()
        
        results_df = results_df.sort_values(by="perc_diff_avg_lap")
        
        fig, ax = plt.subplots(figsize=(12.8, 7.2), dpi=300)
        
        ax.bar(results_df["constructor_name"],
               results_df["perc_diff_avg_lap"],
               color=results_df["constructor_color"]
        )
        
        tick_labels = [
        f"{team}\n{format_lap_time(lap_time)}"
            for team, lap_time in zip(
            results_df["constructor_name"],
            results_df["constructor_avg_lap"]
            )
        ]
        
        for index, value in enumerate(results_df["perc_diff_avg_lap"]):
            ax.text(index, value + 0.06, f"+{value:.2f}%", ha='center', va='top')
        
        ax.set_xticks(np.arange(len(results_df["constructor_name"])))
        ax.set_xticklabels(tick_labels, rotation=25)
    
        ax.set_ylim(results_df["perc_diff_avg_lap"].max() + 1, 0)
        
        ax.set_ylabel('Pace Difference (%)')
        ax.set_xlabel('Team & Median Time (s)')
        ax.set_title("Team Avg Pace Comparison", fontsize=20, color='white', fontweight='bold', y=1.05)
        ax.text(0.5, 1.02, f"{self._raw_session_details.actual_start_timestamp_utc.date()} | {self._raw_event_details.name} | {self._raw_session_details.type}",
                ha='center', fontsize=10, color='white', transform=ax.transAxes)
    
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
    
    
    @plot_name("team_fast_pace_comparison")
    def fast_lap_pace_comparison(self) -> str:
        results_df = self.results_df.groupby("constructor_name").agg({
                "perc_diff_fast_lap": 'first',
                "constructor_fast_lap": 'first',
                "constructor_color": 'first'
            }).reset_index()
        
        results_df = results_df.sort_values(by="perc_diff_fast_lap")
        
        fig, ax = plt.subplots(figsize=(12.8, 7.2), dpi=300)
        
        ax.bar(results_df["constructor_name"],
               results_df["perc_diff_fast_lap"],
               color=results_df["constructor_color"]
        )
        
        tick_labels = [
        f"{team}\n{format_lap_time(lap_time)}"
            for team, lap_time in zip(
            results_df["constructor_name"],
            results_df["constructor_fast_lap"]
            )
        ]
        
        
        for index, value in enumerate(results_df["perc_diff_fast_lap"]):
            ax.text(index, value + 0.06, f"+{value:.2f}%", ha='center', va='top')
        
        ax.set_xticks(np.arange(len(results_df["constructor_name"])))
        ax.set_xticklabels(tick_labels, rotation=25)
    
        ax.set_ylim(results_df["perc_diff_fast_lap"].max() + 1, 0)
        
        ax.set_ylabel('Pace Difference (%)')
        ax.set_xlabel('Team & Fastest Time (s)')
        ax.set_title("Team Fast Pace Comparison", fontsize=20, color='white', fontweight='bold', y=1.05)
        ax.text(0.5, 1.02, f"{self._raw_session_details.actual_start_timestamp_utc.date()} | {self._raw_event_details.name} | {self._raw_session_details.type}",
                ha='center', fontsize=10, color='white', transform=ax.transAxes)
    
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