import streamlit as st
from noaa_isd_connection import NOAAisdWeatherDataConnection
import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
import psychrolib
import numba as nb
import time


# Initialize psychrolib
psychrolib.SetUnitSystem(psychrolib.SI)

def calculate_relative_humidity_func(air_temperature_C, dew_point_temperature_C):
    return psychrolib.GetRelHumFromTDewPoint(air_temperature_C, dew_point_temperature_C) * 100.0

# Numba jit-compiled function for relative humidity calculation
@nb.vectorize([nb.float64(nb.float64, nb.float64)])
def calculate_relative_humidity_numba(air_temperature_C, dew_point_temperature_C):
    return psychrolib.GetRelHumFromTDewPoint(air_temperature_C, dew_point_temperature_C) * 100.0

st.set_page_config(
    page_title='Demo of Streamlit.connection for NOAA ISD lite weather dataset',
    page_icon='🔌'
)

st.title("🔌 Demo of Streamlit.connection for NOAA ISD lite weather dataset")

st.write("Curious to learn more about the weather, global warming or even the unprecedented flooding in Vermont or the most recent extreme heat wave the Southern U.S.")

st.subheader("Where / when do you want to get to know the weather")
address = st.text_input(label="Building Address", value="Montreal", help="Support address, city, zip code, etc.")

# Layout for side by side date inputs
col1, col2 = st.columns(2)
# Calculate default dates
end_date_default = datetime.date.today() - datetime.timedelta(days=2)
start_date_default = end_date_default - datetime.timedelta(days=365)
with col2:
    end_date = st.date_input(label="End Date",
                             value=end_date_default,
                             min_value=None,
                             max_value=datetime.date.today())

with col1:
    start_date = st.date_input(label="Start Date",
                               value=start_date_default,
                               min_value=end_date - relativedelta(years=50),
                               max_value=end_date - datetime.timedelta(days=7))

st.write("You can add a psychrometric model and benchmark the numba vectorized calculation")
col, _ = st.columns(2)
with col:
    calculate_relative_humidity = st.checkbox("Calculate Relative Humidity", value=False)
    if calculate_relative_humidity:
        use_vectorized_function = st.selectbox("Select Relative Humidity Function", ["Numba Vectorized", "Simple Function with pd .apply"])


data = st.experimental_connection('weather_data', type=NOAAisdWeatherDataConnection, ttl=3600, address=address, start_date=start_date, end_date=end_date)

weather_data_list = []
for year in range(start_date.year, end_date.year + 1):
    results = data.get(address=address, year=year)
    year_weather_data = results["weather_data"]
    weather_data_list.append(year_weather_data)

weather_data = pd.concat(weather_data_list)
station_info = results["station_info"]

# Filter data between start_date and end_date
weather_data = weather_data[(weather_data.index >= pd.to_datetime(start_date)) & (weather_data.index <= pd.to_datetime(end_date))]

# Benchmarking the time for relative humidity calculation
if calculate_relative_humidity:
    start_time = time.time()
    if use_vectorized_function == "Numba Vectorized":
        # Calculate Relative Humidity using Numba-compiled function
        weather_data['Relative Humidity, %'] = calculate_relative_humidity_numba(weather_data['Air Temperature, Celcius'].values, weather_data['Dew Point Temperature, Celcius'].values)
    else:
        weather_data['Relative Humidity, %'] = weather_data.apply(lambda row: calculate_relative_humidity_func(row['Air Temperature, Celcius'], row['Dew Point Temperature, Celcius']), axis=1)

    end_time = time.time()
    elapsed_time = end_time - start_time
    st.write(f"Time taken for relative humidity calculation: {elapsed_time:.4f} seconds")

st.write(f"weather fetched for:")
st.dataframe(station_info)

st.subheader("Temperatures")
st.line_chart(weather_data[['Air Temperature, Celcius', 'Dew Point Temperature, Celcius']])
st.subheader("Barometric Pressure")
st.line_chart(weather_data[['Sea Level Pressure, kPa']])
st.subheader("Wind Speed")
st.line_chart(weather_data[['Wind Speed Rate, m/s']])
st.subheader("Precipitations")
st.line_chart(weather_data[['Liquid Precipitation Depth Dimension 1hr, mm']])

if calculate_relative_humidity:
    st.subheader("Relative Humidity")
    st.line_chart(weather_data[['Relative Humidity, %']])

st.subheader(f"Source File available at:")
st.write(f"{data.cursor(results)}")
