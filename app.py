from fastapi import FastAPI, Query
from pydantic import BaseModel
import requests

app = FastAPI()

# ------------------ Weather API Call ------------------ #
def get_weather_forecast(city, api_key):
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric"
    response = requests.get(url)
    if response.status_code != 200:
        return None, None
    data = response.json()
    next_day = data['list'][:8]  # next 24 hours (3hr intervals)
    avg_temp = sum([i['main']['temp'] for i in next_day]) / 8
    total_rain = sum([i.get('rain', {}).get('3h', 0) for i in next_day])
    return round(avg_temp, 2), round(total_rain, 2)

# ------------------ Soil Model Functions ------------------ #
def compute_soil_factors(N, P, K, pH):
    if N > 70 and 6 <= pH <= 7.5:
        absorption_factor = 0.8
    elif N > 50 and 5.5 <= pH <= 8:
        absorption_factor = 0.7
    else:
        absorption_factor = 0.6

    if K > 60 and 6 <= pH <= 7.5:
        evap_rate_per_deg = 0.3
    elif K > 40:
        evap_rate_per_deg = 0.4
    else:
        evap_rate_per_deg = 0.5

    return absorption_factor, evap_rate_per_deg

def predict_moisture(N, P, K, pH, current_moisture, predicted_temp, predicted_rainfall):
    absorption_factor, evap_rate_per_deg = compute_soil_factors(N, P, K, pH)
    moisture_gain = absorption_factor * predicted_rainfall
    moisture_loss = evap_rate_per_deg * predicted_temp
    predicted_moisture = current_moisture + moisture_gain - moisture_loss
    return round(max(0, min(predicted_moisture, 100)), 2)

# ------------------ Request Model ------------------ #
class SoilData(BaseModel):
    N: float
    P: float
    K: float
    pH: float
    current_moisture: float
    city: str

# ------------------ API Endpoint ------------------ #
@app.post("/predict")
def predict_soil_moisture(data: SoilData):
    api_key = "04bf89ecabf9ac4cae7a7173c5cdd1bb"  # OpenWeatherMap API key
    predicted_temp, predicted_rainfall = get_weather_forecast(data.city, api_key)

    if predicted_temp is None:
        return {"error": "Could not fetch weather data. Check city name or API key."}

    moisture = predict_moisture(data.N, data.P, data.K, data.pH, data.current_moisture, predicted_temp, predicted_rainfall)

    if moisture < 20:
        status = "Too Dry"
    elif 20 <= moisture <= 60:
        status = "Optimal"
    else:
        status = "Too Wet"

    return {
        "predicted_moisture": moisture,
        "status": status,
        "weather": {
            "avg_temp_24h": predicted_temp,
            "rainfall_24h_mm": predicted_rainfall
        }
    }
