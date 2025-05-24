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

from static_data.models import Driver, Schedule, Session, Constructor, ConstructorColor

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
        self._raw_driver_details = Driver.objects.values('id', 'abbreviation')
        self._raw_event_details = Schedule.objects.get(id=self.event_id)
        self._raw_session_details = Session.objects.get(id=self.session_id)
        self._raw_constructor = Constructor.objects.values()
        self._raw_constructor_color = ConstructorColor.objects.filter(season_year=self.year).values("constructor_name", "color_fastf1")
    
    def _process_data(self, remove_outliers: bool = True) -> None:
        """Process fetched data and make it a pandas dataframe"""
        pass
    
    