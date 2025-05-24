from django import forms
from .models import Season, Schedule, Session

class AnalysisForm(forms.Form):
    year = forms.ChoiceField(choices=[])
    event_id = forms.ChoiceField(choices=[])
    session_id = forms.ChoiceField(choices=[])
    visual = forms.ChoiceField(choices=[("Team Lap Times", "Team Lap Times"), ("Drivers Lap Times", "Drivers Lap Times")])

    def __init__(self, *args, **kwargs):
        available_years = kwargs.pop("available_years", [])
        available_events = kwargs.pop("available_events", [])
        available_sessions = kwargs.pop("available_sessions", [])
        
        super().__init__(*args, **kwargs)
        
        # Set dynamic choices for year, event, and session
        self.fields["year"].choices = [(year, year) for year in available_years]
        self.fields["event_id"].choices = [(event.id, event.name) for event in available_events]
        self.fields["session_id"].choices = [(session.id, session.type) for session in available_sessions]
