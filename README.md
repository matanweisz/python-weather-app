# Python Weather App

A simple Flask web application that provides weather forecasts for any location, using the [Open-Meteo API](https://open-meteo.com/).

## Features

- Search weather by city or country.
- Select a forecast for 1, 3, or 7 days.
- View temperature, humidity, UV index, and cloud cover.
- Download query history as a JSON file.

## Running Locally

### With Python Virtual Environment
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

### With Docker
```bash
# Build the container image
docker build -t weather-app .

# Run the container
docker run -p 5000:5000 weather-app
```
After starting, access the application at [http://localhost:5000](http://localhost:5000).

## Technical Details

- **API Endpoints**:
    - `GET, POST /`: Main page for searching and viewing weather.
    - `GET /health`: Health check endpoint for Kubernetes probes (returns `200 OK`).
    - `GET /history`: Downloads the weather search history.
- **Environment Variables**:
    - `PORT`: Port the application runs on (default: `5000`).
    - `LOG_DIR`: Directory for log files (default: `/app/logs`).
    - `BG_COLOR`: Sets the UI background color (default: `#A6CDC6`).
- **Production Runtime**:
    - The container runs the app using **Gunicorn** with 2 workers and 4 threads.
    - The container runs as a **non-root user** (`appuser`) for improved security.
    - A `HEALTHCHECK` instruction is included in the Dockerfile for container orchestration platforms.
