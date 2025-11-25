"""
Weather App - Main Flask Application

A web application that provides weather forecasts for any location using the Open-Meteo API.
Features include multi-day forecasts, query history tracking, and health monitoring for Kubernetes.
"""

import json
import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

from flask import Flask, render_template, request, send_file

from src.weather import get_weather

app = Flask(__name__)

# Configure logging directory (environment variable or default)
log_dir = os.getenv("LOG_DIR", "/app/logs")
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(log_dir, "weather_app.log")
HISTORY_FILE = os.path.join(log_dir, "weather_history.json")

# Dual logging: file (for persistence) and stdout (for container logs)
file_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
)

logging.basicConfig(level=logging.DEBUG, handlers=[file_handler, stdout_handler])


@app.route("/", methods=["GET", "POST"])
def index():
    """Main page - displays weather search form and results"""
    data = None

    if request.method == "POST":
        location = request.form["location"]
        days_num = request.form.get("days_num")

        try:
            data = get_weather(location, days_num)
            save_to_history(location, data)
            app.logger.info(
                f"Successfully received weather data for the location: {location}"
            )

        except Exception as e:
            app.logger.error(f"Unexpected Error: {e}, for the location: {location}")
            bg_color = os.getenv("BG_COLOR", "#f8f9fa")
            return render_template("index.html", error="Invalid location. Please try again.", bg_color=bg_color)

    # Allow background color customization via environment variable
    bg_color = os.getenv("BG_COLOR", "#f8f9fa")

    return render_template("index.html", data=data, bg_color=bg_color)


def save_to_history(location, data):
    """Save weather query to history file for tracking and analytics"""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    log_entry = {"timestamp": timestamp, "location": location, "data": data}

    try:
        # Load existing history or create new list
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        else:
            history = []

        history.append(log_entry)

        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4)

    except Exception as e:
        app.logger.error(f"Failed to save to history: {e}")


@app.route("/health")
def health_check():
    """
    Health check endpoint for Kubernetes liveness and readiness probes.
    Returns 200 OK if the application is running properly.
    """
    if all_required_services_are_running():
        return "OK", 200
    else:
        return "Service Unavailable", 500


def all_required_services_are_running():
    """Check if all required services are operational"""
    # Currently returns True as we don't have external service dependencies
    # In production, you might check database connections, cache availability, etc.
    return True


@app.route("/history", methods=["GET"])
def download_history():
    """Download query history as JSON file"""
    if os.path.exists(HISTORY_FILE):
        return send_file(HISTORY_FILE, as_attachment=True)
    else:
        return "No history found.", 404


if __name__ == "__main__":
    # Allow port customization via environment variable
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
