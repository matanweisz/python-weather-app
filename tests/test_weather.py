import pytest
from weather_app.src.data_parser import Parser
from weather_app.src.weather import get_weather, WeatherData, DayWeather, make_data_ready

@pytest.fixture
def weather():
    weather_main = get_weather("haifa", 1)
    return weather_main

def test_get_weather(weather):
    assert weather is not None


@pytest.fixture
def parsed():
    parsed_data = Parser({'latitude': 32.8125, 'longitude': 35.0, 'generationtime_ms': 0.05555152893066406, 'utc_offset_seconds': 7200, 'timezone': 'Asia/Jerusalem', 'timezone_abbreviation': 'GMT+2', 'elevation': 32.0, 'hourly_units': {'time': 'iso8601', 'relative_humidity_2m': '%', 'cloud_cover': '%'}, 'hourly': {'time': ['2025-01-21T00:00', '2025-01-21T01:00', '2025-01-21T02:00', '2025-01-21T03:00', '2025-01-21T04:00', '2025-01-21T05:00', '2025-01-21T06:00', '2025-01-21T07:00', '2025-01-21T08:00', '2025-01-21T09:00', '2025-01-21T10:00', '2025-01-21T11:00', '2025-01-21T12:00', '2025-01-21T13:00', '2025-01-21T14:00', '2025-01-21T15:00', '2025-01-21T16:00', '2025-01-21T17:00', '2025-01-21T18:00', '2025-01-21T19:00', '2025-01-21T20:00', '2025-01-21T21:00', '2025-01-21T22:00', '2025-01-21T23:00'], 'relative_humidity_2m': [79, 84, 85, 85, 86, 86, 81, 78, 70, 57, 49, 42, 40, 38, 34, 35, 56, 63, 68, 69, 71, 72, 76, 60], 'cloud_cover': [42, 20, 6, 2, 98, 100, 44, 100, 100, 100, 100, 100, 100, 23, 0, 0, 0, 0, 0, 0, 11, 63, 100, 100]}, 'daily_units': {'time': 'iso8601', 'temperature_2m_max': '°C', 'temperature_2m_min': '°C', 'uv_index_max': ''}, 'daily': {'time': ['2025-01-21'], 'temperature_2m_max': [21.3], 'temperature_2m_min': [12.1], 'uv_index_max': [4.2]}})
    return parsed_data

@pytest.fixture
def weather_data(parsed):
    weather_data_class = WeatherData(1, parsed)
    return weather_data_class

def test_weather_data_init(weather_data):
    
    assert weather_data.days_num == 1
    assert weather_data.time == ['2025-01-21']
    assert weather_data.uv_index == [4.2]
    assert weather_data.cloud_cover == [42, 20, 6, 2, 98, 100, 44, 100, 100, 100, 100, 100, 100, 23, 0, 0, 0, 0, 0, 0, 11, 63, 100, 100]
    assert weather_data.max_temp == [21.3]
    assert weather_data.min_temp == [12.1]
    assert weather_data.humiditys == [79, 84, 85, 85, 86, 86, 81, 78, 70, 57, 49, 42, 40, 38, 34, 35, 56, 63, 68, 69, 71, 72, 76, 60]
    assert weather_data.days_list == []

def test_calc_total_humidity(weather_data):
    assert weather_data.calc_total_humidity() is not None

def test_create_days_list(weather_data):
    assert weather_data.create_days_list() is not None
    assert weather_data.days_list != []


@pytest.fixture
def day_weather():
    day_weather_obj = DayWeather()
    return day_weather_obj

def test_day_weather_init(day_weather):
    assert day_weather.max_temp is None
    assert day_weather.min_temp is None
    assert day_weather.total_humidity is None
    assert day_weather.uv_index is None
    assert day_weather.time is None
    assert day_weather.cloud_cover is None

def test_day_weather_get(day_weather):
    assert day_weather.get_total_humidity() == day_weather.total_humidity


def test_make_data_ready():
    assert make_data_ready([], "Israel", "Haifa") is not None
