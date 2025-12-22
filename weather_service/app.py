from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import json
import boto3
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# AWS S3 config
S3_BUCKET = os.getenv("S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")

s3 = boto3.client("s3", region_name=AWS_REGION)

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

    # Store JSON in S3
    file_key = f"{location.replace(' ', '_')}/{date}.json"

    s3.put_object(
        Bucket=S3_BUCKET,
        Key=file_key,
        Body=json.dumps(weather_data),
        ContentType="application/json"
    )

    return jsonify(weather_data), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=86, debug=False)
