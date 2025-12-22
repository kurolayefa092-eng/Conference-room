from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# Use environment variables for URLs so they work in Docker
ROOM_SERVICE_URL = os.getenv('ROOM_SERVICE_URL', 'http://room-service:85/api/rooms')
WEATHER_SERVICE_URL = os.getenv('WEATHER_SERVICE_URL', 'http://weather-service:86/api/weather/forecast')

@app.route('/api/pricing/calculate', methods=['GET'])
def calculate_final_price():
    room_id = request.args.get('room_id')
    date = request.args.get('date')

    if not room_id or not date:
        return jsonify({"error": "Missing room_id or date"}), 400

    try:
        # 1. Call Room Service
        room_resp = requests.get(f"{ROOM_SERVICE_URL}/{room_id}")
        if room_resp.status_code != 200:
            return jsonify({"error": "Room not found"}), 404
        
        room_data = room_resp.json()
        
        # 2. Call Weather Service
        weather_params = {'location': room_data['location'], 'date': date}
        weather_resp = requests.get(WEATHER_SERVICE_URL, params=weather_params)
        
        if weather_resp.status_code != 200:
            return jsonify({"error": "Weather service failed"}), 500
        
        weather_data = weather_resp.json()

        # 3. Calculation Logic
        base_price = room_data['price_per_hour']
        surcharge_pct = weather_data['additional_charge_pct'] / 100
        final_price = round(base_price * (1 + surcharge_pct), 2)

        return jsonify({
            "room": room_data['name'],
            "base_price": base_price,
            "surcharge": f"{weather_data['additional_charge_pct']}%",
            "final_price": final_price,
            "weather_details": weather_data
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=87)