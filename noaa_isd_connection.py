from streamlit.connections import ExperimentalBaseConnection
from streamlit.runtime.caching import cache_data, cache_resource

import pandas as pd
import numpy as np
import geocoder
import requests
import os
import gzip
import io


class NOAAisdWeatherDataConnection(ExperimentalBaseConnection):
    """Basic st.experimental_connection implementation for NOAA ISD lite weather data"""

    def _connect(self, **kwargs):
        self.address = kwargs.pop('address', 'Montreal')  # Default value of "Montreal" for address
        self.year = kwargs.pop('year', 2023)  # Default value of 2023 for year
        self.base_url = "https://www.ncei.noaa.gov/pub/data/noaa/isd-lite/"
        self.inventory_url = "https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv"

    def _geocode_address(self):
        g = geocoder.arcgis(self.address)
        if g.ok:
            return g.lat, g.lng
        else:
            return None, None

    def _get_closest_weather_stations(self):
        inventory_df = pd.read_csv(self.inventory_url)
        address_lat, address_lng = self._geocode_address()
        if address_lat is None or address_lng is None:
            print("Address geocoding failed.")
            return pd.DataFrame()

        inventory_df['LAT'] = pd.to_numeric(inventory_df['LAT'], errors='coerce')
        inventory_df['LON'] = pd.to_numeric(inventory_df['LON'], errors='coerce')

        inventory_df.dropna(subset=['LAT', 'LON'], inplace=True)

        inventory_df['DISTANCE'] = ((inventory_df['LAT'] - address_lat) ** 2 + (
                inventory_df['LON'] - address_lng) ** 2) ** 0.5

        sorted_inventory_df = inventory_df.sort_values(by='DISTANCE')

        return sorted_inventory_df

    def _download_weather_data(self, station_id):
        filename = f"{self.year}/{station_id}-{self.year}.gz"
        file_url = os.path.join(self.base_url, filename)
        response = requests.get(file_url)
        if response.status_code == 200:
            return io.BytesIO(response.content)
        else:
            print(f"Failed to download data for {station_id}-{self.year}.")
            print(f"Status Code: {response.status_code}")
            return None

    def _extract_weather_data(self, file_content):
        columns = ['YEAR', 'MONTH', 'DAY', 'HOUR', 'Air Temperature, Celcius', 'Dew Point Temperature, Celcius',
                   'Sea Level Pressure, kPa', 'Wind Direction, degrees', 'Wind Speed Rate, m/s',
                   'Sky Condition Total Coverage Code', 'Liquid Precipitation Depth Dimension 1hr, mm',
                   'Liquid Precipitation Depth Dimension 6hrs, mm']
        multipliers = [1, 1, 1, 1, 0.1, 0.1, 0.01, 1, 0.1, 1, 0.1, 0.1]  # Multipliers for respective columns
        weather_data = []

        with gzip.open(file_content, 'rt') as f:
            for line in f:
                line_data = line.strip().split()
                # Replace -9999 values with NaN
                line_data = [val if val != '-9999' else np.nan for val in line_data]
                # Apply multipliers to appropriate columns and add units to column names
                for i in range(len(columns)):
                    line_data[i] = float(line_data[i]) * multipliers[i]
                    # line_data[i] = f"{line_data[i]} {columns[i].split(' ')[-1]}"  # Append units to the column name
                weather_data.append(line_data)
        weather_df = pd.DataFrame(weather_data, columns=columns)
        # Combine 'YEAR', 'MONTH', 'DAY', 'HOUR' columns to create the timestamp
        weather_df['TIMESTAMP'] = pd.to_datetime(weather_df[['YEAR', 'MONTH', 'DAY', 'HOUR']])
        # Set the timestamp column as the index
        weather_df.set_index('TIMESTAMP', inplace=True)
        return weather_df

    def get(self, year: int = 2023, ttl: int = 3600, **kwargs) -> dict:
        self.year = year
        self.closest_stations_df = self._get_closest_weather_stations()
        @cache_data(ttl=ttl)
        def _get_weather_data(_self) -> dict:
            result = {
                "weather_data": pd.DataFrame(),
                "station_info": pd.DataFrame()
            }

            if _self.closest_stations_df.empty:
                print("No closest stations found.")
                return result

            # Filter stations that have data for the specified year
            available_stations = _self.closest_stations_df[
                pd.to_datetime(_self.closest_stations_df['END'], format='%Y%m%d', errors='coerce') >= pd.to_datetime(
                    str(_self.year) + '0101', format='%Y%m%d')
                ]

            if available_stations.empty:
                print("No data available for the specified year in nearby stations.")
                return result

            station_id = str(available_stations.iloc[0]['USAF']) + "-" + str(available_stations.iloc[0]['WBAN'])
            file_content = _self._download_weather_data(station_id)

            if file_content:
                weather_data = _self._extract_weather_data(file_content)
                result["weather_data"] = weather_data
                result["station_info"] = available_stations.iloc[0].to_frame().T
                return result

            print(f"Failed to download data for {station_id}-{_self.year}.")
            return result

        result = _get_weather_data(self, **kwargs)
        return result

    def cursor(self):
        return self.file_url
