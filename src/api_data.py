"""
API Data Module - Handles external API communication

Interfaces with Open-Meteo API for geocoding and weather data.
No API key required - free tier supports all our use cases.
"""

import requests


class API:
    """
    Client for Open-Meteo geocoding and weather forecast APIs.

    Two-step process:
    1. Convert location name to coordinates (geocoding)
    2. Fetch weather forecast using coordinates
    """

    def __init__(self, location, days_num):
        self.location = location
        self.days_num = days_num
        self.latitude = None
        self.longitude = None
        self.city = None
        self.country = None
        self.result = None

    def get_geocode(self):
        """Convert location name to coordinates and location details"""
        geo_api_url = "https://geocoding-api.open-meteo.com/v1/search"

        geo_params = {
            "name": self.location,
            "count": 1,
            "language": "en",
            "format": "json"
        }

        try:
            res = requests.get(geo_api_url, params=geo_params).json()
            geo_data = res.get('results')[0]

            self.city = geo_data.get('name')
            self.country = geo_data.get('country')
            self.latitude = geo_data.get('latitude')
            self.longitude = geo_data.get('longitude')
        except Exception as e:
            # Re-raise to be handled by Flask error handling
            raise ValueError(f"Location not found: {self.location}") from e


    def get_weather(self):
        """Fetch weather forecast using coordinates from geocoding"""
        weather_api_url = "https://api.open-meteo.com/v1/forecast"

        weather_params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "hourly": "relative_humidity_2m,cloud_cover",
            "daily": "temperature_2m_max,temperature_2m_min,uv_index_max",
            "timezone": "auto",
            "forecast_days": self.days_num
        }

        try:
            self.result = requests.get(weather_api_url, params=weather_params).json()
        except Exception as e:
            raise ConnectionError(f"Failed to fetch weather data: {e}") from e

    def get_city_name(self):
        """Get city name from geocoding (ensures geocoding is called first)"""
        self.get_geocode()
        return self.city

    def get_country_name(self):
        """Get country name from geocoding (ensures geocoding is called first)"""
        self.get_geocode()
        return self.country

    def get_api_data(self):
        """
        Main method to retrieve all weather data.
        Coordinates geocoding and weather API calls.
        """
        self.get_geocode()
        self.get_weather()
        return self.result
