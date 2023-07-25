from streamlit.connections import ExperimentalBaseConnection
from streamlit.runtime.caching import cache_data
import pandas as pd

import pandas as pd
from geopy.geocoders import Nominatim
from math import radians, sin, cos, sqrt, atan2


# Function to calculate the distance between two latitude-longitude coordinates
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371.0  # approximate radius of Earth in km

    lat1_rad, lon1_rad = radians(lat1), radians(lon1)
    lat2_rad, lon2_rad = radians(lat2), radians(lon2)

    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c
    return distance


# Function to geocode an address and get its latitude and longitude
def geocode_address(address):
    geolocator = Nominatim(user_agent="weather_station_locator")
    location = geolocator.geocode(address)
    if location:
        return location.latitude, location.longitude
    else:
        return None, None


# Function to find the closest weather station to the given address
def find_closest_weather_station(address):
    # Load the inventory data into a DataFrame
    url = "https://www.ncei.noaa.gov/pub/data/noaa/isd-inventory.txt"
    data = pd.read_fwf(url, skiprows=22)

    # Geocode the address
    address_lat, address_lon = geocode_address(address)
    if address_lat is None or address_lon is None:
        raise ValueError("Could not geocode the address.")

    # Calculate distances between the address and each weather station
    data["Distance"] = data.apply(lambda row: calculate_distance(address_lat, address_lon, row["LAT"], row["LON"]),
                                  axis=1)

    # Sort the weather stations by distance
    data = data.sort_values(by="Distance")

    return data


if __name__ == "__main__":
    # Example usage:
    address = "Your address goes here"
    closest_weather_stations = find_closest_weather_station(address)
    print(closest_weather_stations.head())

'''

class noaa_isd_connection(ExperimentalBaseConnection[]):
    """Basic st.experimental_connection implementation for accessing National Oceanographic Atmospheric Agency (NOAA)
    Integrated Surface Dataset (ISD) for historical weather  for a specific address"""

    def _connect(self, **kwargs) -> duckdb.DuckDBPyConnection:
        if 'database' in kwargs:
            db = kwargs.pop('database')
        else:
            db = self._secrets['database']
        return duckdb.connect(database=db, **kwargs)

    def get(self, address: str, start_date: ttl: int = 3600, **kwargs) -> pd.DataFrame:
        @cache_data(ttl=ttl)
        def _query(query: str, **kwargs) -> pd.DataFrame:
            cursor = self.cursor()
            cursor.execute(query, **kwargs)
            return cursor.df()

        return _query(query, **kwargs)
    
'''