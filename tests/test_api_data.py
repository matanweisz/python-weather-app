import pytest
from src.api_data import API


@pytest.fixture
def api():
    api_obj = API("berlin", 7)
    return api_obj

def test_api_init(api):
    assert api.location == "berlin"
    assert api.days_num == 7
    assert api.latitude is None
    assert api.longitude is None
    assert api.city is None
    assert api.country is None
    assert api.result is None

def test_get_geocode(api):
    api.get_geocode()
    assert api.latitude is not None
    assert api.longitude is not None
    assert api.city is not None
    assert api.country is not None

def test_get_weather(api):
    api.get_geocode()
    api.get_weather()
    assert api.result is not None

def test_get_city_name(api):
    assert api.get_city_name() == "Berlin"

def test_get_country_name(api):
    assert api.get_country_name() == "Germany"

def test_get_api_data(api):
    assert api.get_api_data() == api.result
