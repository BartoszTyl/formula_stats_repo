from . import add_watermark

from collections import defaultdict

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

import io
import base64

from static_data.models import Event, Session, Telemetry, Constructor, ConstructorColor, Lap, Result

def plot_name(name):
    def decorator(func):
        func.plot_name = name
        return func
    return decorator


class PerformanceVisuals:
    PLOT_METHODS = [
    'team_speed_comparison'
    ]
    
    def __init__(self, year: int, event_id: int, session_id: int):
        # Initialise basic parameters
        self.year = year
        self.event_id = event_id
        self.session_id = session_id
        
        
        self._load_data()
        self._process_data()
        
        
    def _load_data(self) -> None:
        """Fetch all necessary raw data from the database"""
        lap_ids = Lap.objects.filter(session=self.session_id).values_list('id', flat=True).distinct()
        laps_raw = Lap.objects.filter(id__in=lap_ids).values('driver')

        self._raw_telemetry = Telemetry.objects.filter(lap__in=lap_ids).values('speed', 'lap')
        self._raw_constructor_color = ConstructorColor.objects.filter(season_year=self.year).values("constructor", "color_fastf1")
        self._raw_results = Result.objects.filter(session=self.session_id).values("id", "constructor", "driver")
        self._raw_constructor = Constructor.objects.values("id", "name")
        self._raw_event_details = Event.objects.get(id=self.event_id)
        self._raw_session_details = Session.objects.get(id=self.session_id)

        
        
    def _process_data(self) -> None:
        """Process fetched data and make it a dataframe"""
        # telemetry_df = pd.DataFrame(self._raw_telemetry)
        # self.telemetry_df = telemetry_df
        
        # Dictionary {"id": "team name"}
        team_names_dict = {entry["id"]: entry["name"] for entry in self._raw_constructor}
        
        # Dictionary {"team name": "team color"}
        team_colors_dict = {team_names_dict.get(
            entry["constructor"], entry["constructor"]): entry["color_fastf1"] for entry in self._raw_constructor_color}
        
        # Dictionary {"driver": "team name"}
        driver_constructor_dict = {entry["driver"]: entry["constructor"] for entry in self._raw_results}
        
        # Build the dictionary: constructor_id -> list of lap_ids
        constructor_lap_ids = defaultdict(list)

        # Get all laps with 'id' and 'driver'
        laps_raw = Lap.objects.filter(session=self.session_id).values("id", "driver")

        for lap in laps_raw:
            lap_id = lap["id"]
            driver_id = lap["driver"]
            constructor_id = driver_constructor_dict.get(driver_id)

            if constructor_id is not None:
                constructor_lap_ids[constructor_id].append(lap_id)

        self.constructor_lap_ids = dict(constructor_lap_ids)
        print(self.constructor_lap_ids)
       
        # Build a reverse mapping: lap_id -> constructor_id
        lap_to_constructor = {
            lap_id: constructor_id
            for constructor_id, lap_ids in self.constructor_lap_ids.items()
            for lap_id in lap_ids
        }

        # Create DataFrame from telemetry
        telemetry_df = pd.DataFrame(self._raw_telemetry)

        # Skip if telemetry is empty
        if telemetry_df.empty:
            self.team_speed_df = pd.DataFrame()
            return

        # Assuming telemetry contains 'lap' and 'speed'
        telemetry_df["constructor_id"] = telemetry_df["lap"].map(lap_to_constructor)

        # Drop rows with no matching constructor
        telemetry_df = telemetry_df.dropna(subset=["constructor_id"])

        # Convert constructor_id to integer (optional but useful for grouping)
        telemetry_df["constructor_id"] = telemetry_df["constructor_id"].astype(int)

        # Group and calculate mean and max
        team_speed_summary = telemetry_df.groupby("constructor_id")["speed"].agg(["mean", "max"]).reset_index()

        self.team_speed_df = team_speed_summary
        print(self.team_speed_df)
        

    @plot_name('team_speed_comparison')
    def team_speed_comparison(self) -> str:
        """
        Generates a scatter plot comparing mean vs. max speed for each F1 team.

        Teams are represented by color-coded dots, with a legend identifying each team.
        The final plot is returned as a base64 encoded PNG image.

        Returns:
            str: A base64 encoded string of the plot image.
        """
        if self.team_speed_df.empty:
            print("No speed data available to generate plot.")
            return ""

        # Map constructor IDs to names and colors
        team_names = {entry["id"]: entry["name"] for entry in self._raw_constructor}
        team_colors = {
            team_names.get(entry["constructor"], entry["constructor"]): entry["color_fastf1"]
            for entry in self._raw_constructor_color
        }

        df = self.team_speed_df.copy()
        df["team_name"] = df["constructor_id"].map(team_names)
        df["color"] = df["team_name"].map(team_colors)

        fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
        ax.grid(True, linestyle='--', alpha=0.4)
        # Plot all points
        for _, row in df.iterrows():
            ax.scatter(
                x=row["mean"],
                y=row["max"],
                color=row["color"],
                s=150,
                edgecolors="black",
                label=row["team_name"]
            )

        # Remove duplicate labels in legend
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(
            by_label.values(),
            by_label.keys(),
            title="Teams",
            loc="best",
            fontsize=8,
            title_fontsize=9
        )

        # Title and subtitle
        fig.suptitle("Max vs Mean Speed - Team", fontsize=20, color='white', fontweight='bold', y=1.01)

        subtitle = (
            f"{self._raw_session_details.actual_start_timestamp_utc.date()} | "
            f"{self._raw_event_details.name} | {self._raw_session_details.type} "
        )
        fig.text(0.5, 0.93, subtitle, ha="center", fontsize=10, color="white")
        
        ax.set_xlabel("Mean Speed (km/h)")
        ax.set_ylabel("Max Speed (km/h)")
        
        plt.tight_layout()

        add_watermark(fig, alpha=0.35)

        img_io = io.BytesIO()
        plt.savefig(img_io, format='png', bbox_inches='tight')
        plt.close(fig)
        img_io.seek(0)

        return base64.b64encode(img_io.getvalue()).decode("utf-8")
        