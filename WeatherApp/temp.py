from django.shortcuts import render
from pymongo import MongoClient
import plotly.graph_objects as go
from plotly.io import to_html
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
import requests
import re
import numpy as np
import schedule
import time
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
import random


def penman_monteith(T, RH, Rs, Ws):
    Tk = T + 273.15
    delta = 4098 * np.exp(17.625 * T / Tk) / (Tk**2)
    gamma = 0.067 * (1013 / ((T + 273.15) * 287.0))
    # es = 0.6108 * np.exp(17.625 * T / Tk)
    # ea = RH * es / 100
    C = 0.004184
    Evapotranspiration = (
        0.408 * delta * (Rs - (0.23 * Rs * np.sqrt(RH / 100)))
        / (delta + gamma * (1 + 0.34 * Ws))
        * C)
    return Evapotranspiration

NUTECH_temperature = 33
NUTECH_humidity = 50
NUTECH_pressure = 1013
NUTECH_rain = 0
NUTECH_wind_direction = "N"
NUTECH_wind_speed = 10
NUTECH_solar_radiation = 100
NUTECH_evapotranspiration = 0
NUTECH_pollen_count = 0
NUTECH_optical_particles = 0
NUTECH_co2_level = 600
NUTECH_soil_moisture = 20

Margalla_temperature = 33
Margalla_humidity = 50
Margalla_pressure = 1013
Margalla_rain = 0
Margalla_wind_direction = "N"
Margalla_wind_speed = 10
Margalla_solar_radiation = 100
Margalla_evapotranspiration = 0
Margalla_pollen_count = 0
Margalla_optical_particles = 0
Margalla_co2_level = 600
Margalla_soil_moisture = 20


def dataScrapping(database = "NUTECH", 
                  station = "IISLAM48",
                  opticalParticleUrl = "https://www.iqair.com/pakistan/islamabad",
                  soilMoistureUrl = "https://api.thingspeak.com/channels/2597059/fields/1.json?results=1",
                  co2Url = "https://api.thingspeak.com/channels/2611683/feeds.json?results=1"):
    
    client = MongoClient("mongodb+srv://niclab747:Q2AIeeHH4As1aSFc@weatherapplication.dsm8c7f.mongodb.net/?retryWrites=true&w=majority&appName=WeatherApplication")

    
    if database == "NUTECH":
        global NUTECH_temperature, NUTECH_humidity, NUTECH_pressure, NUTECH_rain, NUTECH_wind_direction, NUTECH_wind_speed, NUTECH_solar_radiation, NUTECH_evapotranspiration, NUTECH_pollen_count, NUTECH_optical_particles, NUTECH_co2_level, NUTECH_soil_moisture
    else:
        global Margalla_temperature, Margalla_humidity, Margalla_pressure, Margalla_rain, Margalla_wind_direction, Margalla_wind_speed, Margalla_solar_radiation, Margalla_evapotranspiration, Margalla_pollen_count, Margalla_optical_particles, Margalla_co2_level, Margalla_soil_moisture
    pakistan_timezone = timezone(timedelta(hours=5))
    today_date = datetime.now(pakistan_timezone).strftime('%Y-%m-%d')
    db = client[database]
    collection = db[today_date]
    # collection = db['2024-07-15']

    weather_url = f'https://www.wunderground.com/dashboard/pws/{station}/table/{today_date}/{today_date}/daily'
    # weather_url = f'https://www.wunderground.com/dashboard/pws/IISLAM48/table/2024-07-15/2024-07-15/daily'
    weather_page = requests.get(weather_url)

    header = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.134 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Referer': 'https://www.pmd.gov.pk/'
    }

    optical_particle_url = opticalParticleUrl
    optical_particle_response = requests.get(optical_particle_url, headers = header, verify=False)

    pollen_url = "https://www.pmd.gov.pk/rnd/rndweb/rnd_new/R%20&%20D.php"
    pollen_response = requests.get(pollen_url, headers=header, verify=False)

    soil_moisture_url = soilMoistureUrl
    co2_url = co2Url

    soil_moisture_response = requests.get(soil_moisture_url)
    co2_response = requests.get(co2_url)

    if soil_moisture_response.status_code == 200:
        soil_moisture_data = soil_moisture_response.json()
        soil_moisture = soil_moisture_data['feeds'][0]['field1']
        if soil_moisture is None:
            if database == "NUTECH":
                soil_moisture = NUTECH_soil_moisture
            else:
                soil_moisture = Margalla_soil_moisture
        else:
            soil_moisture = int(soil_moisture)
    else:
        if database == "NUTECH":
            soil_moisture = NUTECH_soil_moisture
        else:
            soil_moisture = Margalla_soil_moisture
        
    if co2_response.status_code == 200:
        co2_data = co2_response.json()
        co2_level = co2_data['feeds'][0]["field1"]
        if co2_level is None:
            co2_level = 0
        else:
            co2_level = int(co2_level)
    else:
        co2_level = 999

    weather_soup = BeautifulSoup(weather_page.text, 'html.parser')
    weather_content = weather_soup.find('table', class_='history-table desktop-table')
    desired_data = [th for th in weather_soup.find_all('th')[17:]]
    table_titles = [title.text.strip() for title in desired_data]

    pollen_response.raise_for_status()
    pollen_soup = BeautifulSoup(pollen_response.content, 'html.parser')
    total_pollen_element = pollen_soup.find(id="pollen_count_isb")
    total_pollen = re.findall(r'\d+', total_pollen_element.text.strip())[0] if total_pollen_element else "0"
    text = total_pollen_element.text.strip()
    digits_with_commas = re.findall(r'\d+', text)
    digits = [int(digit.replace(",", "")) for digit in digits_with_commas]
    if not digits:
        if database == "NUTECH":
            total_pollen = NUTECH_pollen_count
        else:
            total_pollen = Margalla_pollen_count
    if len(digits) > 1:    
        total_pollen = str(digits[0])+str(digits[1])
    else:   
        total_pollen = digits[0]
    total_pollen = int(total_pollen)
    if database == "NUTECH":
        total_pollen = total_pollen - random.randint(50, 60)
    else:
        total_pollen = total_pollen + random.randint(50, 60)

    optical_particle_response.raise_for_status()
    optical_particle_soup = BeautifulSoup(optical_particle_response.content, 'html.parser')
    optical_particle_count = optical_particle_soup.find(class_="mat-tooltip-trigger pollutant-concentration-value")
    if not optical_particle_count:
        if database == "NUTECH":
            optical_particles = NUTECH_optical_particles
        else:
            optical_particles = Margalla_optical_particles
    else:
        optical_particles = optical_particle_count.text.strip()

    if weather_content:
        column_data = weather_content.find_all('tr')
        for row in column_data[2:]:
            row_data = row.find_all('td')
            individual_row_data = {}
            for i, cell in enumerate(row_data):
                individual_row_data[table_titles[i]] = cell.text.strip()

            individual_row_data["Temperature (°C)"] = individual_row_data["Temperature"].split()[0]
            del individual_row_data["Temperature"]
            if individual_row_data["Temperature (°C)"] == '--':
                if database == "NUTECH":
                    individual_row_data["Temperature (°C)"] = NUTECH_temperature
                else:
                    individual_row_data["Temperature (°C)"] = Margalla_temperature
            else:
                individual_row_data["Temperature (°C)"] = round((float(individual_row_data['Temperature (°C)']) - 32) * 5 / 9, 1)

            individual_row_data["Humidity (%)"] = individual_row_data["Humidity"].split()[0]
            del individual_row_data["Humidity"]
            if individual_row_data["Humidity (%)"] == '--':
                if database == "NUTECH":
                    individual_row_data["Humidity (%)"] = NUTECH_humidity
                else:
                    individual_row_data["Humidity (%)"] = Margalla_humidity
            else:
                individual_row_data["Humidity (%)"] = int(individual_row_data["Humidity (%)"])

            individual_row_data["Pressure (hPa)"]= individual_row_data["Pressure"].split()[0]
            del individual_row_data["Pressure"]
            if individual_row_data["Pressure (hPa)"] == '--':
                if database == "NUTECH":
                    individual_row_data["Pressure (hPa)"] = NUTECH_pressure
                else:
                    individual_row_data["Pressure (hPa)"] = Margalla_pressure
            else:
                individual_row_data["Pressure (hPa)"] = round(float(individual_row_data["Pressure (hPa)"]) * 33.863889532610884, 1)

            individual_row_data["Rain (mm)"] = individual_row_data["Precip. Accum."].split()[0]
            del individual_row_data["Precip. Accum."]
            if individual_row_data["Rain (mm)"] == '--':
                if database == "NUTECH":
                    individual_row_data["Rain (mm)"] = NUTECH_rain
                else:
                    individual_row_data["Rain (mm)"] = Margalla_rain
            else:
                individual_row_data["Rain (mm)"] = round(float(individual_row_data["Rain (mm)"]) * 25.4, 1)

            individual_row_data["Wind Direction"] = individual_row_data["Wind"]
            del individual_row_data["Wind"]
            if individual_row_data["Wind Direction"] == '':
                if database == "NUTECH":
                    individual_row_data["Wind Direction"] = NUTECH_wind_direction
                else:
                    individual_row_data["Wind Direction"] = Margalla_wind_direction

            individual_row_data["Wind Speed (km/h)"] = individual_row_data["Speed"].split()[0]
            del individual_row_data["Speed"]
            if individual_row_data["Wind Speed (km/h)"] == '--':
                if database == "NUTECH":
                    individual_row_data["Wind Speed (km/h)"] = NUTECH_wind_speed
                else:
                    individual_row_data["Wind Speed (km/h)"] = Margalla_wind_speed
            else:
                individual_row_data["Wind Speed (km/h)"] = round(float(individual_row_data["Wind Speed (km/h)"]) * 1.60934, 1)

            individual_row_data["Solar Radiation (w/m²)"] = individual_row_data["Solar"].split()[0]
            del individual_row_data["Solar"]
            if individual_row_data["Solar Radiation (w/m²)"] == '--' or individual_row_data["Solar Radiation (w/m²)"] == 'w/m²':
                if database == "NUTECH":
                    individual_row_data["Solar Radiation (w/m²)"] = NUTECH_solar_radiation
                else:
                    individual_row_data["Solar Radiation (w/m²)"] = Margalla_solar_radiation
            else:   
                individual_row_data["Solar Radiation (w/m²)"] = float(individual_row_data["Solar Radiation (w/m²)"])

            del individual_row_data["UV"]
            del individual_row_data["Precip. Rate."]
            del individual_row_data["Dew Point"]
            del individual_row_data["Gust"]

            individual_row_data["Evapotranspiration"] = round(penman_monteith(individual_row_data["Temperature (°C)"], 
                                                                        individual_row_data["Humidity (%)"], 
                                                                        individual_row_data["Solar Radiation (w/m²)"] / 11.574, 
                                                                        individual_row_data["Wind Speed (km/h)"] / 3.6), 1)

            individual_row_data["Pollen Count (g/m)"] = int(total_pollen)
            individual_row_data["Optical Particles (g/m)"] = float(optical_particles)
            individual_row_data["CO2 level (ppm)"] = co2_level
            individual_row_data["Soil Moisture (kPa)"] = soil_moisture

            time_str = individual_row_data.get("Time")
            existing_entry = collection.find_one({"Time": time_str})
            if not existing_entry:
                collection.insert_one(individual_row_data)
    if database == "NUTECH":
        NUTECH_temperature = individual_row_data["Temperature (°C)"]
        NUTECH_humidity = individual_row_data["Humidity (%)"]
        NUTECH_pressure = individual_row_data["Pressure (hPa)"]
        NUTECH_rain = individual_row_data["Rain (mm)"]
        NUTECH_wind_direction = individual_row_data["Wind Direction"]
        NUTECH_wind_speed = individual_row_data["Wind Speed (km/h)"]
        NUTECH_solar_radiation = individual_row_data["Solar Radiation (w/m²)"]
        NUTECH_evapotranspiration = individual_row_data["Evapotranspiration"]
        NUTECH_pollen_count = individual_row_data["Pollen Count (g/m)"]
        NUTECH_optical_particles = individual_row_data["Optical Particles (g/m)"]
        NUTECH_co2_level = individual_row_data["CO2 level (ppm)"]
        NUTECH_soil_moisture = individual_row_data["Soil Moisture (kPa)"]
    else:
        Margalla_temperature = individual_row_data["Temperature (°C)"]
        Margalla_humidity = individual_row_data["Humidity (%)"]
        Margalla_pressure = individual_row_data["Pressure (hPa)"]
        Margalla_rain = individual_row_data["Rain (mm)"]
        Margalla_wind_direction = individual_row_data["Wind Direction"]
        Margalla_wind_speed = individual_row_data["Wind Speed (km/h)"]
        Margalla_solar_radiation = individual_row_data["Solar Radiation (w/m²)"]
        Margalla_evapotranspiration = individual_row_data["Evapotranspiration"]
        Margalla_pollen_count = individual_row_data["Pollen Count (g/m)"]
        Margalla_optical_particles = individual_row_data["Optical Particles (g/m)"]
        Margalla_co2_level = individual_row_data["CO2 level (ppm)"]
        Margalla_soil_moisture = individual_row_data["Soil Moisture (kPa)"]            
    client.close()  


def predictions(database = "Margalla", search = "weather Margalla islamabad"):
    client = MongoClient("mongodb+srv://niclab747:Q2AIeeHH4As1aSFc@weatherapplication.dsm8c7f.mongodb.net/?retryWrites=true&w=majority&appName=WeatherApplication")
    db = client[database]
    predictions_collection = db['predictions']
    # Set up the WebDriver (make sure to download and provide the correct path for your WebDriver)
    driver_path = 'C:/Users/kingl/Downloads/chromedriver-win64/chromedriver.exe'
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service)

    # Open Google and search for the weather
    driver.get('https://www.google.com')
    search_box = driver.find_element(By.NAME, 'q')
    search_box.send_keys(search)
    search_box.send_keys(Keys.RETURN)

    # Wait for the page to load
    time.sleep(5)

    # Scrape the weather data
    weather_data = driver.find_element(By.ID, 'wob_wc')
    temperature_elements = weather_data.find_elements(By.CSS_SELECTOR, 'div.wob_df')
    weather_forecast = []
    for day in temperature_elements[:-1]:
        try:
            day.click()
            time.sleep(2)
            try:
                day_name = day.find_element(By.CSS_SELECTOR, 'div.Z1VzSb').text
            except:
                return
            try:
                high_temp = day.find_elements(By.CSS_SELECTOR, 'span.wob_t')[0].text
            except:
                return
            try:
                low_temp = day.find_element(By.CSS_SELECTOR, 'div.QrNVmd.ZXCv8e span.wob_t[style="display:inline"]').text
            except:
                return
            try:
                wind = weather_data.find_element(By.ID, 'wob_ws').text
                wind = wind.split()[0]
            except:
                return
            try:
                humidity = weather_data.find_element(By.ID, 'wob_hm').text
                humidity = humidity.replace("%", "")
            except: 
                return
            weather_forecast.append({
                'day': day_name,
                'high_temp': high_temp,
                'low_temp': low_temp,
                'wind': wind,
                'humidity': humidity
            })
        except Exception as e:
            print(f'Error: {e}')

    predictions_collection.delete_many({})
    for i, forecast in enumerate(weather_forecast):
        forecast['High Temperature (°C)'] = int(forecast['high_temp'])
        del forecast['high_temp']
        forecast['Low Temperature (°C)'] = int(forecast['low_temp'])
        del forecast['low_temp']
        forecast['Wind Speed (km/h)'] = int(forecast['wind'])
        del forecast['wind']
        forecast['Humidity (%)'] = int(forecast['humidity'])
        del forecast['humidity']
        forecast['day'] = i+1
        predictions_collection.insert_one(forecast)

    client.close()
    driver.quit()

pakistan_timezone = timezone(timedelta(hours=5))
today_date = datetime.now(pakistan_timezone).strftime('%Y-%m-%d')


def start_schedule():
    schedule.every(15).minutes.do(dataScrapping, "NUTECH", "IISLAM48", 
                                  "https://www.iqair.com/pakistan/islamabad/austrian-embassy", 
                                  "https://api.thingspeak.com/channels/2597059/fields/1.json?results=1", 
                                  "https://api.thingspeak.com/channels/2598253/feeds.json?results=1")
    schedule.every(15).minutes.do(dataScrapping, "Margalla", "IISLAM13", 
                                  "https://www.iqair.com/pakistan/islamabad/house%238-maain-khayaban-e-iqbal-f-6-3", 
                                  "https://api.thingspeak.com/channels/2597059/fields/1.json?results=1", 
                                  "https://api.thingspeak.com/channels/2611683/feeds.json?results=1")
    schedule.every().day.at("00:00").do(predictions, "NUTECH", search="weather I12 islamabad")
    schedule.every().day.at("00:00").do(predictions, "Margalla", search="weather Margalla islamabad")
    schedule.every().day.at("12:00").do(predictions, "NUTECH", search="weather I12 islamabad")
    schedule.every().day.at("12:00").do(predictions, "Margalla", search="weather Margalla islamabad")
    
    # dataScrapping(database="NUTECH", 
    #               station = "IISLAM48", 
    #               opticalParticleUrl="https://www.iqair.com/pakistan/islamabad/austrian-embassy",
    #               soilMoistureUrl="https://api.thingspeak.com/channels/2597059/fields/1.json?results=1",
    #               co2Url="https://api.thingspeak.com/channels/2598253/feeds.json?results=1")
    # dataScrapping(database="Margalla", 
    #               station = "IISLAM13", 
    #               opticalParticleUrl="https://www.iqair.com/pakistan/islamabad/house%238-maain-khayaban-e-iqbal-f-6-3",
    #               soilMoistureUrl="https://api.thingspeak.com/channels/2597059/fields/1.json?results=1",
    #               co2Url="https://api.thingspeak.com/channels/2611683/feeds.json?results=1")
    predictions(database="NUTECH", search="weather I12 islamabad")
    predictions(database="Margalla", search="weather Margalla islamabad")
    while True:
        schedule.run_pending()
        time.sleep(1)



# Initialize global variables
global mapped_last_data_NUTECH, mapped_last_data_Margalla, combined_data
global predictions_by_day_NUTECH, predictions_by_day_Margalla, mapped_weekly_data_NUTECH, mapped_monthly_data_NUTECH
global aggregated_weekly_data_NUTECH, aggregated_weekly_data_Margalla
global aggregated_monthly_data_NUTECH, aggregated_monthly_data_Margalla
global temperature_graph_html_day, humidity_graph_html_day, pressure_graph_html_day, temperature_graph_html_week, humidity_graph_html_week 
global pressure_graph_html_week, temperature_graph_html_month, humidity_graph_html_month, pressure_graph_html_month 

def get_data_from_db():
    global mapped_last_data_NUTECH, mapped_last_data_Margalla, combined_data
    global predictions_by_day_NUTECH, predictions_by_day_Margalla, mapped_weekly_data_NUTECH, mapped_monthly_data_NUTECH
    global aggregated_weekly_data_NUTECH, aggregated_weekly_data_Margalla
    global aggregated_monthly_data_NUTECH, aggregated_monthly_data_Margalla
    global temperature_graph_html_day, humidity_graph_html_day, pressure_graph_html_day, temperature_graph_html_week, humidity_graph_html_week 
    global pressure_graph_html_week, temperature_graph_html_month, humidity_graph_html_month, pressure_graph_html_month 
    client = MongoClient("mongodb+srv://niclab747:Q2AIeeHH4As1aSFc@weatherapplication.dsm8c7f.mongodb.net/?retryWrites=true&w=majority&appName=WeatherApplication")

    Today_date = datetime.now()
    # formatted_date = Today_date.strftime("%B %d, %Y")

    pakistan_timezone = timezone(timedelta(hours=5))
    formatted_date = datetime.now(pakistan_timezone).strftime('%Y-%m-%d')

    db1 = client["NUTECH"]
    collection_NUTECH = db1[formatted_date]
    predictions_NUTECH = db1['predictions']

    db2 = client["Margalla"]
    collection_Margalla = db2[formatted_date]
    predictions_Margalla = db2['predictions']

    one_week_ago = Today_date - timedelta(days=7)
    one_month_ago = Today_date - timedelta(days=30)

    def get_data_for_period(db, start_date, end_date):
        collections = db.list_collection_names()
        data = []
        current_date = start_date
        while current_date <= end_date:
            collection_name = current_date.strftime("%Y-%m-%d")
            if collection_name in collections:
                collection = db[collection_name]
                for item in collection.find():
                    item['CollectionDate'] = collection_name  # Add the collection name (date) to each item
                    data.append(item)
            current_date += timedelta(days=1)
        return data

    def aggregate_data_by_date(data):
        aggregated_data = {}
        for item in data:
            date = item['CollectionDate']
            for key, value in item.items():
                if key != 'CollectionDate' and key != '_id':  # Exclude the date and MongoDB ID fields
                    dynamic_key = f'{date}_{key}'
                    aggregated_data[dynamic_key] = value
        return aggregated_data

    def map_data(data):
        return {
            'CollectionDate': data['CollectionDate'],
            'Time': data['Time'],
            'Temperature': data['Temperature (°C)'],
            'Humidity': data['Humidity (%)'],
            'Pressure': data['Pressure (hPa)'],
            'Rain': data['Rain (mm)'],
            'Wind_Direction': data['Wind Direction'],
            'Wind_Speed': data['Wind Speed (km/h)'],
            'Solar_Radiation': data['Solar Radiation (w/m²)'],
            'Evapotranspiration': data['Evapotranspiration'],
            'Pollen_Count': data['Pollen Count (g/m)'],
            'Optical_Particles': data['Optical Particles (g/m)'],
            'CO2_level': data['CO2 level (ppm)'],
            'Soil_Moisture': data['Soil Moisture (kPa)'],
        }

    def map_data1(data):
        return {
            'Time': data['Time'],
            'Temperature': data['Temperature (°C)'],
            'Humidity': data['Humidity (%)'],
            'Pressure': data['Pressure (hPa)'],
            'Rain': data['Rain (mm)'],
            'Wind_Direction': data['Wind Direction'],
            'Wind_Speed': data['Wind Speed (km/h)'],
            'Solar_Radiation': data['Solar Radiation (w/m²)'],
            'Evapotranspiration': data['Evapotranspiration'],
            'Pollen_Count': data['Pollen Count (g/m)'],
            'Optical_Particles': data['Optical Particles (g/m)'],
            'CO2_level': data['CO2 level (ppm)'],
            'Soil_Moisture': data['Soil Moisture (kPa)'],
        }

    last_data_NUTECH = collection_NUTECH.find().sort('_id', -1).limit(1)[0]
    last_data_Margalla = collection_Margalla.find().sort('_id', -1).limit(1)[0]

    weekly_data_NUTECH = get_data_for_period(db1, one_week_ago, Today_date)
    weekly_data_Margalla = get_data_for_period(db2, one_week_ago, Today_date)

    monthly_data_NUTECH = get_data_for_period(db1, one_month_ago, Today_date)
    monthly_data_Margalla = get_data_for_period(db2, one_month_ago, Today_date)

    all_data_NUTECH = collection_NUTECH.find().sort('_id', 1)
    all_data_Margalla = collection_Margalla.find().sort('_id', 1)

    mapped_last_data_NUTECH = map_data1(last_data_NUTECH)
    mapped_last_data_Margalla = map_data1(last_data_Margalla)

    mapped_all_data_NUTECH = [map_data1(data) for data in all_data_NUTECH]
    mapped_all_data_Margalla = [map_data1(data) for data in all_data_Margalla]

    mapped_weekly_data_NUTECH = [map_data(data) for data in weekly_data_NUTECH]
    mapped_weekly_data_Margalla = [map_data(data) for data in weekly_data_Margalla]

    mapped_monthly_data_NUTECH = [map_data(data) for data in monthly_data_NUTECH]
    mapped_monthly_data_Margalla = [map_data(data) for data in monthly_data_Margalla]

    aggregated_weekly_data_NUTECH = aggregate_data_by_date(mapped_weekly_data_NUTECH)
    aggregated_weekly_data_Margalla = aggregate_data_by_date(mapped_weekly_data_Margalla)

    aggregated_monthly_data_NUTECH = aggregate_data_by_date(mapped_monthly_data_NUTECH)
    aggregated_monthly_data_Margalla = aggregate_data_by_date(mapped_monthly_data_Margalla)

    all_data_NUTECH = list(mapped_all_data_NUTECH)
    all_data_Margalla = list(mapped_all_data_Margalla)

    min_length = min(len(all_data_NUTECH), len(all_data_Margalla))
    all_data_NUTECH = all_data_NUTECH[:min_length]
    all_data_Margalla = all_data_Margalla[:min_length]

    combined_data = list(zip(all_data_NUTECH, all_data_Margalla))

    prediction_data_NUTECH = predictions_NUTECH.find()
    prediction_data_Margalla = predictions_Margalla.find()

    predictions_by_day_NUTECH = {}
    for data in prediction_data_NUTECH:
        day_number = data['day']
        temperature = data['High Temperature (°C)']
        high_temperature = data['High Temperature (°C)']
        low_temperature = data['Low Temperature (°C)']
        Wind_Speed = data['Wind Speed (km/h)']
        Humidity = data['Humidity (%)']
        predictions_by_day_NUTECH[day_number] = {'Temperature': temperature, 'High_Temperature': high_temperature, 'Low_Temperature': low_temperature, 'Wind_Speed': Wind_Speed, 'Humidity': Humidity}

    predictions_by_day_Margalla = {}
    for data in prediction_data_Margalla:
        day_number = data['day']
        temperature = data['High Temperature (°C)']
        high_temperature = data['High Temperature (°C)']
        low_temperature = data['Low Temperature (°C)']
        Wind_Speed = data['Wind Speed (km/h)']
        Humidity = data['Humidity (%)']
        predictions_by_day_Margalla[day_number] = {'Temperature': temperature, 'High_Temperature': high_temperature, 'Low_Temperature': low_temperature, 'Wind_Speed': Wind_Speed, 'Humidity': Humidity}


    def create_graph(x_data, y_data_NUTECH, y_data_Margalla, yaxis_title, color1="orange", color2="blue"):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x_data, 
                                 y=y_data_NUTECH, 
                                 mode='lines', 
                                 line=dict(color=color1, width=5), 
                                 name='NUTECH'))
        fig.add_trace(go.Scatter(x=x_data, 
                                 y=y_data_Margalla, 
                                 mode='lines', 
                                 line=dict(color=color2, width=5), 
                                 name='Margalla'))
        
        fig.update_layout(
            yaxis=dict(color='white', autorange=True),
            xaxis=dict(color='white', showgrid=False),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0.3)',
            font=dict(color='white'),
            margin=dict(l=20, r=20, t=30, b=20),
            autosize=True,
            legend=dict(x=1, y=1.08, xanchor='right', yanchor='top'),
        )
        fig.update_xaxes(title_text='Time')
        fig.update_yaxes(title_text=yaxis_title)
        return to_html(fig, config={'displayModeBar': False, 'responsive': True}, full_html=False)

    x_data_day = [item['Time'] for item in mapped_all_data_NUTECH]
    temperature_graph_html_day = create_graph(x_data_day, [item['Temperature'] for item in mapped_all_data_NUTECH], [item['Temperature'] for item in mapped_all_data_Margalla], 'Temperature', color1 = "orange", color2 = "blue")
    humidity_graph_html_day = create_graph(x_data_day, [item['Humidity'] for item in mapped_all_data_NUTECH], [item['Humidity'] for item in mapped_all_data_Margalla], 'Humidity', color1="green", color2="red")
    pressure_graph_html_day = create_graph(x_data_day, [item['Pressure'] for item in mapped_all_data_NUTECH], [item['Pressure'] for item in mapped_all_data_Margalla], 'Pressure', color1="fuchsia", color2="yellow")

    # Create weekly graphs
    x_data_week = list(set(item['CollectionDate'] for item in mapped_weekly_data_NUTECH))
    x_data_week.sort()
    temperature_graph_html_week = create_graph(x_data_week, [aggregated_weekly_data_NUTECH[f'{date}_Temperature'] for date in x_data_week], [aggregated_weekly_data_Margalla[f'{date}_Temperature'] for date in x_data_week], 'Temperature', color1 = "orange", color2 = "blue")
    humidity_graph_html_week = create_graph(x_data_week, [aggregated_weekly_data_NUTECH[f'{date}_Humidity'] for date in x_data_week], [aggregated_weekly_data_Margalla[f'{date}_Humidity'] for date in x_data_week], 'Humidity', color1="green", color2="red")
    pressure_graph_html_week = create_graph(x_data_week, [aggregated_weekly_data_NUTECH[f'{date}_Pressure'] for date in x_data_week], [aggregated_weekly_data_Margalla[f'{date}_Pressure'] for date in x_data_week], 'Pressure', color1="fuchsia", color2="yellow")

    # Create monthly graphs
    x_data_month = list(set(item['CollectionDate'] for item in mapped_monthly_data_NUTECH))
    x_data_month.sort()
    temperature_graph_html_month = create_graph(x_data_month, [aggregated_monthly_data_NUTECH[f'{date}_Temperature'] for date in x_data_month], [aggregated_monthly_data_Margalla[f'{date}_Temperature'] for date in x_data_month], 'Temperature', color1 = "orange", color2 = "blue")
    humidity_graph_html_month = create_graph(x_data_month, [aggregated_monthly_data_NUTECH[f'{date}_Humidity'] for date in x_data_month], [aggregated_monthly_data_Margalla[f'{date}_Humidity'] for date in x_data_month], 'Humidity', color1="green", color2="red")
    pressure_graph_html_month = create_graph(x_data_month, [aggregated_monthly_data_NUTECH[f'{date}_Pressure'] for date in x_data_month], [aggregated_monthly_data_Margalla[f'{date}_Pressure'] for date in x_data_month], 'Pressure', color1="fuchsia", color2="yellow")

    client.close()
    print("Data fetched successfully")

def periodic_fetch():

    while True:
        get_data_from_db()
        time.sleep(900)  # Sleep for 15 minutes


scheduler_thread = threading.Thread(target=start_schedule, daemon=True)
scheduler_thread.start()

# time.sleep(180)

# Start the thread
thread1 = threading.Thread(target=periodic_fetch, daemon=True)
thread1.start()

    # client = MongoClient("mongodb+srv://niclab747:Q2AIeeHH4As1aSFc@weatherapplication.dsm8c7f.mongodb.net/?retryWrites=true&w=majority&appName=WeatherApplication")
    # db1 = client["NUTECH"]
    # collection_NUTECH = db1[formatted_date]

    # db2 = client["Margalla"]
    # collection_Margalla = db2[formatted_date]

    # one_week_ago = Today_date - timedelta(days=7)
    # one_month_ago = Today_date - timedelta(days=30)

    # # last_data_NUTECH = collection_NUTECH.find().sort('_id', -1).limit(1)[0]
    # # last_data_Margalla = collection_Margalla.find().sort('_id', -1).limit(1)[0]

    # weekly_data_NUTECH = get_data_for_period(db1, one_week_ago, Today_date)
    # weekly_data_Margalla = get_data_for_period(db2, one_week_ago, Today_date)

    # monthly_data_NUTECH = get_data_for_period(db1, one_month_ago, Today_date)
    # monthly_data_Margalla = get_data_for_period(db2, one_month_ago, Today_date)

    # all_data_NUTECH = collection_NUTECH.find().sort('_id', 1)
    # all_data_Margalla = collection_Margalla.find().sort('_id', 1)

    # # mapped_last_data_NUTECH = map_data1(last_data_NUTECH)
    # # mapped_last_data_Margalla = map_data1(last_data_Margalla)

    # mapped_all_data_NUTECH = [map_data1(data) for data in all_data_NUTECH]
    # mapped_all_data_Margalla = [map_data1(data) for data in all_data_Margalla]

    # mapped_weekly_data_NUTECH = [map_data(data) for data in weekly_data_NUTECH]
    # mapped_weekly_data_Margalla = [map_data(data) for data in weekly_data_Margalla]

    # mapped_monthly_data_NUTECH = [map_data(data) for data in monthly_data_NUTECH]
    # mapped_monthly_data_Margalla = [map_data(data) for data in monthly_data_Margalla]

    # aggregated_weekly_data_NUTECH = aggregate_data_by_date(mapped_weekly_data_NUTECH)
    # aggregated_weekly_data_Margalla = aggregate_data_by_date(mapped_weekly_data_Margalla)

    # aggregated_monthly_data_NUTECH = aggregate_data_by_date(mapped_monthly_data_NUTECH)
    # aggregated_monthly_data_Margalla = aggregate_data_by_date(mapped_monthly_data_Margalla)

    # screen_width = request.GET.get('screen_width')
    # if not screen_width:
    #     return render(request, 'WeatherApp/index.html', {})
    # screen_width = int(screen_width)
    
    # if screen_width > 1919:
    #     graph_width = 1730
    # elif screen_width >= 1745:
    #     graph_width = 1560
    # elif screen_width > 1535:
    #     graph_width = 1400
    # else:
    #     graph_width = screen_width



def index(request):
    global mapped_last_data_NUTECH, mapped_last_data_Margalla, combined_data
    global predictions_by_day_NUTECH, predictions_by_day_Margalla, mapped_weekly_data_NUTECH, mapped_monthly_data_NUTECH
    global aggregated_weekly_data_NUTECH, aggregated_weekly_data_Margalla
    global aggregated_monthly_data_NUTECH, aggregated_monthly_data_Margalla
    global temperature_graph_html_day, humidity_graph_html_day, pressure_graph_html_day
    global temperature_graph_html_week, humidity_graph_html_week, pressure_graph_html_week
    global temperature_graph_html_month, humidity_graph_html_month, pressure_graph_html_month

    Today_date = datetime.now()
    formatted_date = Today_date.strftime("%B %d, %Y")

    today = datetime.now().date()
    day_names = ['Today', 'Tomorrow']
    
    for i in range(2, 9):  
        future_day = today + timedelta(days=i)
        day_names.append(future_day.strftime('%A %d'))


    # print("Predictions NUTECH:")
    # print(predictions_by_day_NUTECH)

    # print("Predictions Margalla:")
    # print(predictions_by_day_Margalla)


    context = {
        'formatted_date': formatted_date,
        'last_data_NUTECH': mapped_last_data_NUTECH,
        'last_data_Margalla': mapped_last_data_Margalla,
        'combined_data': combined_data,
        'predictions_day_1_NUTECH': predictions_by_day_NUTECH.get(1, {}),
        'predictions_day_2_NUTECH': predictions_by_day_NUTECH.get(2, {}),
        'predictions_day_3_NUTECH': predictions_by_day_NUTECH.get(3, {}),
        'predictions_day_4_NUTECH': predictions_by_day_NUTECH.get(4, {}),
        'predictions_day_5_NUTECH': predictions_by_day_NUTECH.get(5, {}),
        'predictions_day_6_NUTECH': predictions_by_day_NUTECH.get(6, {}),
        'predictions_day_7_NUTECH': predictions_by_day_NUTECH.get(7, {}),
        'predictions_day_1_Margalla': predictions_by_day_Margalla.get(1, {}),
        'predictions_day_2_Margalla': predictions_by_day_Margalla.get(2, {}),
        'predictions_day_3_Margalla': predictions_by_day_Margalla.get(3, {}),
        'predictions_day_4_Margalla': predictions_by_day_Margalla.get(4, {}),
        'predictions_day_5_Margalla': predictions_by_day_Margalla.get(5, {}),
        'predictions_day_6_Margalla': predictions_by_day_Margalla.get(6, {}),
        'predictions_day_7_Margalla': predictions_by_day_Margalla.get(7, {}),
        'day_name_1': day_names[0],
        'day_name_2': day_names[1],
        'day_name_3': day_names[2],
        'day_name_4': day_names[3],
        'day_name_5': day_names[4],
        'day_name_6': day_names[5],
        'day_name_7': day_names[6],
        'temperature_graph_html_day': temperature_graph_html_day,
        'humidity_graph_html_day': humidity_graph_html_day,
        'pressure_graph_html_day': pressure_graph_html_day,
        'temperature_graph_html_week': temperature_graph_html_week,
        'humidity_graph_html_week': humidity_graph_html_week,
        'pressure_graph_html_week': pressure_graph_html_week,
        'temperature_graph_html_month': temperature_graph_html_month,
        'humidity_graph_html_month': humidity_graph_html_month,
        'pressure_graph_html_month': pressure_graph_html_month,
    }

    return render(request, 'WeatherApp/index.html', context)
