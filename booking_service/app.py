from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# Environment variables for service URLs
ROOM_SERVICE_URL = os.getenv("ROOM_SERVICE_URL", "http://room-service:85")
WEATHER_SERVICE_URL = os.getenv("WEATHER_SERVICE_URL", "http://weather-service:86")

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"message": "Booking service running"}), 200

@app.route("/api/bookings/calculate", methods=["POST"])
def calculate_booking_price():
    data = request.get_json()
    room_id = data.get("room_id")
    date = data.get("date")

    if not room_id or not date:
        return jsonify({"error": "room_id and date are required"}), 400

    # 1️⃣ Get room details from Room Service
    room_resp = requests.get(f"{ROOM_SERVICE_URL}/api/rooms/{room_id}")
    if room_resp.status_code != 200:
        return jsonify({"error": "Room not found"}), 404
    room_data = room_resp.json()
    location = room_data.get("location")
    base_price = room_data.get("price_per_hour")  # or per_day depending on your booking model

    # 2️⃣ Get weather-adjusted price from Weather Service
    weather_payload = {
        "location": location,
        "date": date,
        "base_price": base_price
    }
    weather_resp = requests.post(f"{WEATHER_SERVICE_URL}/api/weather/forecast", json=weather_payload)
    if weather_resp.status_code != 200:
        return jsonify({"error": "Weather service error"}), 500
    weather_data = weather_resp.json()

    # 3️⃣ Construct booking response
    booking_summary = {
        "room_id": room_id,
        "location": location,
        "date": date,
        "base_price": base_price,
        "forecasted_temperature": weather_data.get("forecasted_temperature"),
        "temperature_difference": weather_data.get("temperature_difference"),
        "additional_charge_percentage": weather_data.get("additional_charge_percentage"),
        "additional_charge_amount": weather_data.get("additional_charge_amount"),
        "final_price": weather_data.get("final_price")
    }

    return jsonify(booking_summary), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=87, debug=False)
