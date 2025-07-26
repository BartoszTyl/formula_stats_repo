import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

# Import your Django models
from static_data.models import Lap, Weather, Session, Driver

class FastestLapPredictor:
    """
    A class to predict the fastest lap for each driver in a given F1 race event.

    This predictor fetches historical lap data, weather conditions, and session
    information to train a machine learning model and make predictions.

    Attributes:
        year (int): The season year for the prediction.
        event_id (int): The ID of the event (race) for the prediction.
        model: The trained machine learning model (e.g., RandomForestRegressor).
    """

    def __init__(self, year, event_id):
        """
        Initializes the predictor with the specified year and event.

        Args:
            year (int or str): The season year.
            event_id (int or str): The unique identifier for the event.
        """
        if not year or not event_id:
            raise ValueError("Year and Event ID cannot be None.")
        
        self.year = int(year)
        self.event_id = int(event_id)
        self.model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        self.feature_names = []

    