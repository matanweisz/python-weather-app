"""
Data Parser Module - Extracts weather data from API responses

Provides a clean interface to access structured data from Open-Meteo API responses.
Separates hourly metrics (humidity, cloud cover) from daily summaries (temperature, UV index).
"""


class Parser:
    """Extracts and provides access to weather data from API response"""

    def __init__(self, api_data):
        self.hourly_data = api_data.get('hourly')
        self.daily_data = api_data.get('daily')

    def get_humidity(self):
        return self.hourly_data.get('relative_humidity_2m')

    def get_cloud_cover(self):
        return self.hourly_data.get('cloud_cover')

    def get_time(self):
        return self.daily_data.get('time')

    def get_max_temp(self):
        return self.daily_data.get('temperature_2m_max')

    def get_min_temp(self):
        return self.daily_data.get('temperature_2m_min')

    def get_uv_index(self):
        return self.daily_data.get('uv_index_max')
