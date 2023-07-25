import pandas as pd
import geocoder
import requests
import os
import gzip

class WeatherDataDownloader:
    def __init__(self, address, year):
        self.address = address
        self.year = year
        self.base_url = "https://www.ncei.noaa.gov/pub/data/noaa/isd-lite/"
        self.inventory_url = "https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv"
        self.closest_stations_df, self.sorted_stations_df = self._get_closest_weather_stations()

    def geocode_address(self):
        g = geocoder.arcgis(self.address)
        if g.ok:
            return g.lat, g.lng
        else:
            return None, None

    def _get_closest_weather_stations(self):
        inventory_df = pd.read_csv(self.inventory_url)

        address_lat, address_lng = self.geocode_address()
        if address_lat is None or address_lng is None:
            print("Address geocoding failed.")
            return pd.DataFrame(), pd.DataFrame()

        inventory_df['LAT'] = pd.to_numeric(inventory_df['LAT'], errors='coerce')
        inventory_df['LON'] = pd.to_numeric(inventory_df['LON'], errors='coerce')

        inventory_df.dropna(subset=['LAT', 'LON'], inplace=True)

        inventory_df['DISTANCE'] = ((inventory_df['LAT'] - address_lat) ** 2 + (
                    inventory_df['LON'] - address_lng) ** 2) ** 0.5

        sorted_inventory_df = inventory_df.sort_values(by='DISTANCE')

        return sorted_inventory_df, inventory_df

    def download_weather_data(self, station_id):
        filename = f"{self.year}/{station_id}-{self.year}.gz"
        file_url = os.path.join(self.base_url, filename)
        response = requests.get(file_url)

        if response.status_code == 200:
            output_filename = f"{station_id}-{self.year}.gz"
            with open(output_filename, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded {station_id}-{self.year}.gz")
            return output_filename
        else:
            print(f"Failed to download data for {station_id}-{self.year}.")
            print(f"Status Code: {response.status_code}")
            return None

    def delete_file(self, filename):
        try:
            os.remove(filename)
            print(f"Deleted {filename}")
        except OSError as e:
            print(f"Error deleting {filename}: {e}")

    def extract_weather_data(self, filename):
        columns = ['YEAR', 'MONTH', 'DAY', 'HOUR', 'Air Temperature', 'Dew Point Temperature', 'Sea Level Pressure', 'Wind Direction', 'Wind Speed Rate', 'Sky Condition Total Coverage Code', 'Liquid Precipitation Depth Dimension', 'Liquid Precipitation Depth Dimension']
        weather_data = []
        with gzip.open(filename, 'rt') as f:
            for line in f:
                line_data = line.strip().split()
                if len(line_data) != len(columns):
                    # Fill missing values with NaN
                    line_data.extend([float('NaN')] * (len(columns) - len(line_data)))
                weather_data.append(line_data)
        return pd.DataFrame(weather_data, columns=columns)

    def get_weather_data(self):
        if self.closest_stations_df.empty:
            print("No closest stations found.")
            return None, None, None

        station_id = str(self.closest_stations_df.iloc[0]['USAF']) + "-" + str(self.closest_stations_df.iloc[0]['WBAN'])
        end_date = self.closest_stations_df.iloc[0]['END']

        # Check if the station has data for the specified year
        if pd.to_datetime(end_date, format='%Y%m%d', errors='coerce') >= pd.to_datetime(str(self.year) + '0101', format='%Y%m%d'):
            downloaded_file = self.download_weather_data(station_id)

            if downloaded_file:
                weather_data = self.extract_weather_data(downloaded_file)
                self.delete_file(downloaded_file)
                return self.closest_stations_df, self.sorted_stations_df, weather_data
        else:
            # Try the next closest station from the list
            for i in range(1, len(self.closest_stations_df)):
                next_station_id = str(self.closest_stations_df.iloc[i]['USAF']) + "-" + str(self.closest_stations_df.iloc[i]['WBAN'])
                next_end_date = self.closest_stations_df.iloc[i]['END']

                if pd.to_datetime(next_end_date, format='%Y%m%d', errors='coerce') >= pd.to_datetime(str(self.year) + '0101', format='%Y%m%d'):
                    downloaded_file = self.download_weather_data(next_station_id)

                    if downloaded_file:
                        weather_data = self.extract_weather_data(downloaded_file)
                        self.delete_file(downloaded_file)
                        print(f"Data not available for the closest station. Using data from the next closest station.")
                        return self.closest_stations_df.iloc[i:i+1], self.sorted_stations_df, weather_data

        print("No data available for the specified year in nearby stations.")
        return None, None, None

# Example usage of the class
if __name__ == "__main__":
    address = "05444"
    year = 2022

    weather_downloader = WeatherDataDownloader(address, year)
    closest_stations_df, sorted_stations_df, weather_data = weather_downloader.get_weather_data()

    if closest_stations_df is not None and not closest_stations_df.empty:
        # Display the sorted DataFrame of closest weather stations
        print("Sorted DataFrame of Closest Weather Stations:")
        print(closest_stations_df)

    if sorted_stations_df is not None and not sorted_stations_df.empty:
        # Display the full sorted DataFrame of weather stations
        print("\nFull Sorted DataFrame of Weather Stations:")
        print(sorted_stations_df)

    if weather_data is not None and not weather_data.empty:
        # Display the weather data as a DataFrame
        print("\nWeather Data:")
        print(weather_data)

