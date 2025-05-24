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

from static_data.models import Lap, TyreCompounds, Session, Schedule

def plot_name(name):
    def decorator(func):
        func.plot_name = name
        return func
    return decorator


class TyreVisuals:
    PLOT_METHODS = ['track_tyre_evolution']
    def __init__(self, year: int, event_id: int, session_id: int):
        # Initialise basic parameters
        self.year = year
        self.event_id = event_id
        self.session_id = session_id
        
        # Load, process data and set general plot properties
        self._load_data()
        self._process_data()
        
    def _load_data(self) -> None:
        """Fetch all necessary raw data from the database"""
        self._raw_laps = Lap.objects.filter(session=self.session_id).values('lap_number', "lap_time", "compound")
        self._raw_tyre_compounds = TyreCompounds.objects.filter(season_year=self.year).values('name', 'color')
        self._raw_event_details = Schedule.objects.get(id=self.event_id)
        self._raw_session_details = Session.objects.get(id=self.session_id)
    
    def _process_data(self, remove_outliers: bool = True) -> None:
        """Process fetched data and make it a pandas dataframe"""
        # Tyre colors dict
        self.tyre_colors_dict = {entry['name']: entry['color'] for entry in self._raw_tyre_compounds}
        
        laps_df = pd.DataFrame(self._raw_laps)
        
        # Remove outliers
        if remove_outliers:
            Q1 = laps_df["lap_time"].quantile(0.25)
            Q3 = laps_df["lap_time"].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            laps_df = laps_df[(laps_df["lap_time"] >= lower_bound) & (laps_df["lap_time"] <= upper_bound)]
            
        self.laps_df = laps_df
        
    
    
    @plot_name('track_tyre_evolution')
    def track_tyre_evolution(self):
        fig, ax = plt.subplots(figsize=(12.8, 8), dpi=300)

        grouped = self.laps_df.groupby(["compound", "lap_number"])["lap_time"].median().reset_index()

        for compound in grouped["compound"].unique():
            compound_data = grouped[grouped["compound"] == compound]
            color = self.tyre_colors_dict.get(compound, "black")  # fallback to black if compound not found
            ax.plot(compound_data["lap_number"], compound_data["lap_time"], label=compound, color=color)

        # X-axis customization
        ax.set_xlim(left=0)
        ax.set_xticks(range(0, grouped['lap_number'].max(), 5))
        ax.set_xlabel("Lap Number")

        # Y-axis customization
        ax.set_ylabel("Lap Time (s)", fontsize=10)
        plt.gca().yaxis.set_major_formatter(FuncFormatter(lambda x, _: int(x / 1000)))
        plt.yticks(fontsize=10)
        
        # Title and subtitle
        ax.set_title("Tyre Compound Avg Pace Per Lap", fontsize=20, color='white', fontweight='bold', y=1.04)
        ax.text(0.5, 1.017, f"{self._raw_session_details.actual_start_timestamp_utc.date()} | {self._raw_event_details.name} | {self._raw_session_details.type}",
                ha='center', fontsize=10, color='white', transform=ax.transAxes)
        
        ax.legend(title="Tyre Compound")
        ax.grid(True, alpha=0.5)
        fig.tight_layout()
        
        
        
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