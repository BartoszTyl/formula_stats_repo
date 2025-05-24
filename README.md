# 🏎️ Formula Stats

A Django-based web application for exploring Formula 1 data. Making F1 data analytics simple and acccessible.

## 🚀 Features

- Visualise Formula 1 data and telemetry
- Organised Django structure for scalability
- Future plans: machine learning insights, race strategy simulation

## 🔮 Roadmap
- Predictive race modeling
- Driver/team comparison tool
- Advanced statistics, graphics and more!

## 🛠 Tech Stack

- Python 3.x
- Django
- Django-Tailwind
- PostgreSQL
- Django-HTML
- JS

## 🧱 Project Structure
```
├── formula_stats_django # Main
    └── formula_stats
        └── __init__.py
        └── asgi.py
        └── settings.py
        └── urls.py
        └── wsgi.py
    └── main_app
        └── management/commands
            └── import_fastf1_data.py
        └── migrations
        └── plotting
            └── __init__.py
            └── driver_pace_lap_times.py
            └── team_pace_lap_times.py
            └── telemetry.py
            └── tyres.py
            └── weather.py
        └── static/main_app
            └── style.css
        └── templates
            └── about.html
            └── analysis.html
            └── base.html
            └── drivers.html
            └── home.html
        └── templatetags
            └── __init__.py
            └── custom_filters.py
        └── __init__.py
        └── admin.py
        └── apps.py
        └── forms.py
        └── models.py
        └── tests.py
        └── urls.py
        └── views.py
    └── manage.py
├── .gitignore
├── requirements.txt
└── README.md
```
