from . import format_lap_time, add_watermark, drs_to_boolean

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import matplotlib.patches as mpatches
import seaborn as sns
from matplotlib import colormaps
# from matplotlib.patches import Patch
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from matplotlib.collections import LineCollection

import pandas as pd
import numpy as np

import io
import base64

from static_data.models import Driver, Event, Session, Constructor, ConstructorColor, Telemetry, Result, Lap

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
    
    PLOT_METHODS = [
        'telemetry_plot',
        'gear_changes',
        'speed_plot',
        'combined_telemetry'
        ]
    
    def __init__(self, year: int, event_id: int, session_id: int, driver_id: int, lap_id: int):
        # Initialise basic parameters
        self.year = year
        self.event_id = event_id
        self.session_id = session_id
        self.driver_id = driver_id
        self.lap_id = lap_id
        
        # Load, process data
        self._load_data()
        self._process_data()
        
    def _load_data(self) -> None:
        """Fetch all necessary raw data from the database"""
        self._raw_driver_details = Driver.objects.filter(id=self.driver_id).values('id', 'abbreviation')
        self._raw_event_details = Event.objects.get(id=self.event_id)
        self._raw_session_details = Session.objects.get(id=self.session_id)
        self._raw_results = Result.objects.filter(session=self.session_id, driver=self.driver_id).values('constructor')
        self._raw_constructor = Constructor.objects.values()
        self._raw_telemetry = Telemetry.objects.filter(lap=self.lap_id).values(
            'time', 'rpm', 'speed', 'n_gear', 'throttle', 'brake', 'drs', 'distance', 'x', 'y')
    
    def _process_data(self) -> None:
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
    
    
    @plot_name('gear_changes')
    def gear_changes(self) -> str:
        
        x = np.array(self.telemetry_df['x'].values)
        y = np.array(self.telemetry_df['y'].values)
        
        points = np.array([x, y]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        gear = self.telemetry_df['n_gear'].to_numpy().astype(float)
        
        # Rotation matrix for counter-clockwise rotation
        angle_rad = np.deg2rad(-self._raw_event_details.circuit.rotation)
        rotation_matrix = np.array([[np.cos(angle_rad), -np.sin(angle_rad)], 
                                [np.sin(angle_rad), np.cos(angle_rad)]])
        
        # Apply the rotation to the points in the track
        rotated_segments = []
        for segment in segments:
            rotated_segment = np.dot(segment.reshape(-1, 2), rotation_matrix)
            rotated_segments.append(rotated_segment)
        rotated_segments = np.array(rotated_segments)
        
        cmap = colormaps['Paired']
        lc_comp = LineCollection(rotated_segments, norm=plt.Normalize(1, cmap.N+1), cmap=cmap)
        lc_comp.set_array(gear)
        lc_comp.set_linewidth(6)
        
        fig, ax = plt.subplots(figsize=(10, 8), dpi=300)

        plt.gca().add_collection(lc_comp)
        plt.axis('equal')
        plt.tick_params(labelleft=False, left=False, labelbottom=False, bottom=False)

        cbar = plt.colorbar(mappable=lc_comp, label="Gear",
                        boundaries=np.arange(1, 10))
        cbar.set_ticks(np.arange(1.5, 9.5))
        cbar.set_ticklabels(np.arange(1, 9))
        
        # Title and subtitle
        fig.suptitle("Gear Changes", fontsize=20, color='white', fontweight='bold', y=0.99)

        subtitle = (
            f"{self._raw_session_details.actual_start_timestamp_utc.date()} | "
            f"{self._raw_event_details.name} | {self._raw_session_details.type} | "
            f"{self.driver_abbreviation} | Lap {self.lap_number}"
        )
        fig.text(0.5, 0.936, subtitle, ha="center", fontsize=10, color="white")
        
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
    
    
    @plot_name('speed_plot')
    def speed_plot(self) -> str:
        
        x = np.array(self.telemetry_df['x'].values)
        y = np.array(self.telemetry_df['y'].values)
        
        points = np.array([x, y]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        gear = self.telemetry_df['speed'].to_numpy().astype(float)
        
        # Rotation matrix for counter-clockwise rotation
        angle_rad = np.deg2rad(-self._raw_event_details.circuit.rotation)
        rotation_matrix = np.array([[np.cos(angle_rad), -np.sin(angle_rad)], 
                                [np.sin(angle_rad), np.cos(angle_rad)]])
        
        # Apply the rotation to the points in the track
        rotated_segments = []
        for segment in segments:
            rotated_segment = np.dot(segment.reshape(-1, 2), rotation_matrix)
            rotated_segments.append(rotated_segment)
        rotated_segments = np.array(rotated_segments)
        
        cmap = colormaps['viridis']
        lc_comp = LineCollection(rotated_segments, cmap=cmap)
        lc_comp.set_array(gear)
        lc_comp.set_linewidth(6)
        
        fig, ax = plt.subplots(figsize=(10, 8), dpi=300)

        plt.gca().add_collection(lc_comp)
        plt.axis('equal')
        plt.tick_params(labelleft=False, left=False, labelbottom=False, bottom=False)

        cbar = plt.colorbar(lc_comp, ax=ax, label="Speed (km/h)", boundaries=np.linspace(50, 350))
        cbar.set_ticks(np.arange(50, 351, 50))
    
        # Title and subtitle
        fig.suptitle("Speed Data", fontsize=20, color='white', fontweight='bold', y=0.99)

        subtitle = (
            f"{self._raw_session_details.actual_start_timestamp_utc.date()} | "
            f"{self._raw_event_details.name} | {self._raw_session_details.type} | "
            f"{self.driver_abbreviation} | Lap {self.lap_number}"
        )
        fig.text(0.5, 0.936, subtitle, ha="center", fontsize=10, color="white")
        
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


    @plot_name("combined_telemetry")
    def combined_telemetry(self) -> str:
        x = np.array(self.telemetry_df["x"].values)
        y = np.array(self.telemetry_df["y"].values)
        points = np.array([x, y]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)

        # Rotate the track
        angle_rad = np.deg2rad(-self._raw_event_details.circuit.rotation)
        rotation_matrix = np.array([
            [np.cos(angle_rad), -np.sin(angle_rad)],
            [np.sin(angle_rad), np.cos(angle_rad)]
        ])

        rotated_segments = []
        for segment in segments:
            rotated_segment = np.dot(segment.reshape(-1, 2), rotation_matrix)
            rotated_segments.append(rotated_segment)
        rotated_segments = np.array(rotated_segments)

        gear = self.telemetry_df["n_gear"].to_numpy().astype(float)
        speed = self.telemetry_df["speed"].to_numpy().astype(float)

        fig, axes = plt.subplots(ncols=2, figsize=(16, 8), dpi=300)

        # GEAR PLOT
        cmap_gear = colormaps["Paired"]
        norm_gear = plt.Normalize(1, cmap_gear.N + 1)
        lc_gear = LineCollection(rotated_segments, cmap=cmap_gear, norm=norm_gear, linewidth=6)
        lc_gear.set_array(gear)
        axes[0].add_collection(lc_gear)
        axes[0].set_title("Gear Changes")
        axes[0].axis("equal")
        axes[0].axis("off")

        # SPEED PLOT
        cmap_speed = colormaps["viridis"]
        lc_speed = LineCollection(rotated_segments, cmap=cmap_speed, linewidth=6)
        lc_speed.set_array(speed)
        axes[1].add_collection(lc_speed)
        axes[1].set_title("Speed (km/h)")
        axes[1].axis("equal")
        axes[1].axis("off")

        # COLORBAR BELOW - GEAR
        cax_gear = inset_axes(axes[0], width="90%", height="5%", loc="lower center", borderpad=3)
        cbar_gear = fig.colorbar(lc_gear, cax=cax_gear, orientation="horizontal", boundaries=np.arange(1, 10))
        cbar_gear.set_ticks(np.arange(1.5, 9.5))
        cbar_gear.set_ticklabels(np.arange(1, 9))
        cbar_gear.set_label("Gear")

        # COLORBAR BELOW - SPEED
        cax_speed = inset_axes(axes[1], width="90%", height="5%", loc="lower center", borderpad=3)
        cbar_speed = fig.colorbar(lc_speed, cax=cax_speed, orientation="horizontal", boundaries=np.linspace(50, 350, 31))
        cbar_speed.set_ticks(np.arange(50, 351, 50))
        cbar_speed.set_label("Speed (km/h)")

        # Title and subtitle
        fig.suptitle("Gear Changes & Speed Data", fontsize=20, color='white', fontweight='bold', y=0.99)

        subtitle = (
            f"{self._raw_session_details.actual_start_timestamp_utc.date()} | "
            f"{self._raw_event_details.name} | {self._raw_session_details.type} | "
            f"{self.driver_abbreviation} | Lap {self.lap_number}"
        )
        fig.text(0.5, 0.94, subtitle, ha="center", fontsize=10, color="white")

        plt.tight_layout()
        add_watermark(fig, alpha=0.35)

        img_io = io.BytesIO()
        plt.savefig(img_io, format="png")
        img_io.seek(0)
        plot_data = base64.b64encode(img_io.getvalue()).decode("utf-8")
        plt.close(fig)

        return plot_data

