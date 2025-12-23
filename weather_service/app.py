from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import random
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://weather-mongodb:27017/")
client = MongoClient(MONGO_URI)
db = client["weather_service"]
forecasts_collection = db["forecasts"]

BASE_TEMP = 21  # degrees C

def calculate_surcharge(temp_diff):
    if temp_diff < 2:
        return 0
    elif temp_diff < 5:
        return 10
    elif temp_diff < 10:
        return 20
    elif temp_diff < 20:
        return 30
    else:
        return 50

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"message": "Weather service running on port 86"}), 200

@app.route("/api/weather/forecast", methods=["POST"])
def get_weather_forecast():
    data = request.get_json()

    location = data.get("location")
    date = data.get("date")
    base_price = data.get("base_price", 0)

    if not location or not date:
        return jsonify({"error": "Location and date are required"}), 400

    # Check if forecast already exists for this location and date
    existing_forecast = forecasts_collection.find_one({
        "location": location,
        "date": date
    })

    if existing_forecast:
        # Return existing forecast
        existing_forecast["_id"] = str(existing_forecast["_id"])
        return jsonify(existing_forecast), 200

    # Mock forecast temperature (-5 to 35 C)
    forecast_temp = random.randint(-5, 35)
    temp_diff = abs(forecast_temp - BASE_TEMP)

    surcharge_percentage = calculate_surcharge(temp_diff)
    additional_charge = (surcharge_percentage / 100) * base_price
    final_price = base_price + additional_charge

    weather_data = {
        "location": location,
        "date": date,
        "forecasted_temperature": forecast_temp,
        "temperature_difference": temp_diff,
        "additional_charge_percentage": surcharge_percentage,
        "additional_charge_amount": round(additional_charge, 2),
        "final_price": round(final_price, 2),
        "generated_at": datetime.utcnow().isoformat()
    }

    # Store in MongoDB
    try:
        result = forecasts_collection.insert_one(weather_data)
        weather_data["_id"] = str(result.inserted_id)
        print(f"Successfully saved to MongoDB: {location} - {date}")
    except Exception as e:
        print(f"Error saving to MongoDB: {e}")
        return jsonify({"error": f"Failed to save forecast: {str(e)}"}), 500

    return jsonify(weather_data), 200

@app.route("/api/weather/forecast/<location>", methods=["GET"])
def get_forecasts_by_location(location):
    """Get all forecasts for a specific location"""
    try:
        forecasts = list(forecasts_collection.find({"location": location}))
        for forecast in forecasts:
            forecast["_id"] = str(forecast["_id"])
        
        return jsonify({
            "location": location,
            "count": len(forecasts),
            "forecasts": forecasts
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/weather/forecasts", methods=["GET"])
def get_all_forecasts():
    """Get all forecasts"""
    try:
        forecasts = list(forecasts_collection.find())
        for forecast in forecasts:
            forecast["_id"] = str(forecast["_id"])
        
        return jsonify({
            "count": len(forecasts),
            "forecasts": forecasts
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=86, debug=False)