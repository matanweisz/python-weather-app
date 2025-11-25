"""
Weather Module - Core business logic for weather data processing

This module orchestrates the weather data retrieval and processing workflow:
- Fetch geocoding and weather data from Open-Meteo API
- Parse raw API responses into structured data
- Aggregate hourly data into daily summaries
- Format data for template rendering
"""

from .api_data import API
from .data_parser import Parser


class DayWeather:
    """Represents weather data for a single day"""
    def __init__(self):
        self.max_temp = None
        self.min_temp = None
        self.total_humidity = None
        self.uv_index = None
        self.time = None
        self.cloud_cover = None

    def get_max_temp(self):
        return self.max_temp

    def get_min_temp(self):
        return self.min_temp

    def get_total_humidity(self):
        return self.total_humidity

    def get_uv_index(self):
        return self.uv_index

    def get_time(self):
        return self.time

    def get_cloud_cover(self):
        return self.cloud_cover


class WeatherData:
    """Processes and aggregates weather data for multiple days"""

    def __init__(self, days_num, parsed_data):
        self.days_num = int(days_num)
        self.time = parsed_data.get_time()
        self.uv_index = parsed_data.get_uv_index()
        self.cloud_cover = parsed_data.get_cloud_cover()
        self.max_temp = parsed_data.get_max_temp()
        self.min_temp = parsed_data.get_min_temp()
        self.humiditys = parsed_data.get_humidity()
        self.days_list = []

    def calc_total_humidity(self):
        """Calculate average humidity from hourly data (24 values)"""
        total_humidity_avg = 0
        for hour in range(24):
            total_humidity_avg += self.humiditys[hour]

        return float("{:.2f}".format(total_humidity_avg / 24))

    def create_days_list(self):
        """Create list of DayWeather objects from parsed API data"""
        for i in range(self.days_num):
            new_day = DayWeather()
            new_day.max_temp = self.max_temp[i]
            new_day.min_temp = self.min_temp[i]
            new_day.time = self.time[i]
            new_day.uv_index = self.uv_index[i]
            new_day.cloud_cover = self.cloud_cover[i]
            new_day.total_humidity = self.calc_total_humidity()

            self.days_list.append(new_day)

            # Move to next day's hourly data (24 hours per day)
            self.humiditys = self.humiditys[24::]

        return self.days_list

def make_data_ready(days_list, country, city):
    """Convert DayWeather objects to dictionary format for template rendering"""
    data = []

    for day in days_list:
        day_element = {
            "country": country,
            "city": city,
            "time": day.get_time(),
            "max_temp": day.get_max_temp(),
            "min_temp": day.get_min_temp(),
            "humidity": day.get_total_humidity(),
            "uv_index": day.get_uv_index(),
            "cloud_cover": day.get_cloud_cover()
        }

        data.append(day_element)

    return data


def get_weather(location, days_num):
    """
    Main entry point for weather data retrieval.

    Args:
        location: City or country name
        days_num: Number of forecast days (1-7)

    Returns:
        List of dictionaries containing weather data for each day
    """
    api_obj = API(location, days_num)
    parsed_data = Parser(api_obj.get_api_data())
    get_weather_data = WeatherData(days_num, parsed_data)
    days_list = get_weather_data.create_days_list()

    return make_data_ready(days_list, api_obj.get_country_name(), api_obj.get_city_name())


if __name__ == "__main__":
    location = "canada"
    days_num = 3

    print(get_weather(location, days_num))
