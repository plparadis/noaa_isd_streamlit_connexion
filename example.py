import streamlit as st
from noaa_isd_connection import NOAAisdWeatherDataConnection
import datetime

st.set_page_config(
    page_title='Demo of Streamlit.connection for NOAA ISD lite weather dataset',
    page_icon='🔌'
)

st.title("🔌 Demo of Streamlit.connection for NOAA ISD lite weather dataset")

st.subheader("Where / when do you want to get the weather")
address = st.text_input(label="Building Address", value="05444", help="Support address, city, zip code, etc.")
year = st.number_input(label="Year of historical weather data", value=datetime.date.today().year)



data = st.experimental_connection('weather_data', type=NOAAisdWeatherDataConnection, ttl=3600, address=address, year=year)
results = data.get(year=year)
weather_data = results["weather_data"]
station_info = results["station_info"]

st.write(f"weather fetched for:")
st.dataframe(station_info)

st.subheader("Temperatures")
st.line_chart(weather_data[['Air Temperature, Celcius',
       'Dew Point Temperature, Celcius']])
st.subheader("Barometric Pressure")
st.line_chart(weather_data[['Sea Level Pressure, kPa']])
st.subheader("Wind Speed")
st.line_chart(weather_data[['Wind Speed Rate, m/s']])
st.subheader("Precipitations")
st.line_chart(weather_data[['Liquid Precipitation Depth Dimension 1hr, mm']])


