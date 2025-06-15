from fastapi import FastAPI
from pydantic import BaseModel
import requests

app = FastAPI()

# ✅ Crop moisture reference (based on your image)
IDEAL_CROP_MOISTURE = {
    "rice": 30,
    "maize": 50,
    "chickpea": 60,
    "kidneybeans": 45,
    "pigeonpeas": 45,
    "mothbeans": 30,
    "mungbean": 80,
    "blackgram": 60,
    "lentil": 90,
    "pomegranate": 30,
    "banana": 40,
    "mango": 15,
    "grapes": 60,
    "watermelon": 70,
    "muskmelon": 30,
    "apple": 50,
    "orange": 60,
    "papaya": 20,
    "coconut": 45,
    "cotton": 70,
    "jute": 20,
    "coffee": 20
}

# ✅ Weather API
def get_weather_forecast(city, api_key):
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric"
    response = requests.get(url)
    if response.status_code != 200:
        return None, None
    data = response.json()
    next_day = data['list'][:8]
    avg_temp = sum([i['main']['temp'] for i in next_day]) / 8
    total_rain = sum([i.get('rain', {}).get('3h', 0) for i in next_day])
    return round(avg_temp, 2), round(total_rain, 2)

# ✅ Soil Moisture Calculation
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

# ✅ Farmer-friendly messages
def get_irrigation_tip(crop, predicted_moisture):
    ideal = IDEAL_CROP_MOISTURE.get(crop.lower())
    if ideal is None:
        return "🔍 Crop not found in database. Please check spelling."

    if predicted_moisture < ideal - 10:
        return "💧 Soil is too dry. Please irrigate the field."
    elif predicted_moisture > ideal + 10:
        return "⚠️ Soil has too much water. Avoid watering. Improve drainage if needed."
    else:
        return "✅ Moisture is good for this crop. No need to water."

def get_weather_alerts(temp, rain):
    alerts = []
    if rain > 30:
        alerts.append("🌧️ Heavy rain expected. Ensure proper drainage.")
    if temp > 40:
        alerts.append("🔥 Very high temperature. Use mulch or shade if possible.")
    if temp < 10:
        alerts.append("❄️ Cold temperature may affect some crops.")
    return alerts

# ✅ API Input
class SoilData(BaseModel):
    N: float
    P: float
    K: float
    pH: float
    current_moisture: float
    city: str
    crop: str

# ✅ API Endpoint
@app.post("/predict")
def predict_soil_moisture(data: SoilData):
    api_key = "04bf89ecabf9ac4cae7a7173c5cdd1bb"
    predicted_temp, predicted_rainfall = get_weather_forecast(data.city, api_key)

    if predicted_temp is None:
        return {"error": "❌ Could not fetch weather data. Please check city name."}

    predicted_moisture = predict_moisture(
        data.N, data.P, data.K, data.pH,
        data.current_moisture, predicted_temp, predicted_rainfall
    )

    advice = get_irrigation_tip(data.crop, predicted_moisture)
    alerts = get_weather_alerts(predicted_temp, predicted_rainfall)

    return {
        "Predicted Moisture (%)": predicted_moisture,
        "Crop": data.crop.title(),
        "Advice": advice,
        "Weather Alert": alerts,
        "Tomorrow's Weather": {
            "Temperature (°C)": predicted_temp,
            "Rainfall (mm)": predicted_rainfall
        }
    }
