from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import json
import boto3
from botocore.exceptions import ClientError
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# AWS S3 config
S3_BUCKET = os.getenv("S3_BUCKET", "conference-room-booking-weather-forcast")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Initialize S3 client with explicit credentials if provided
s3_config = {"region_name": AWS_REGION}
if os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
    s3_config["aws_access_key_id"] = os.getenv("AWS_ACCESS_KEY_ID")
    s3_config["aws_secret_access_key"] = os.getenv("AWS_SECRET_ACCESS_KEY")

s3 = boto3.client("s3", **s3_config)

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
    try:
        file_key = f"forecasts/{location.replace(' ', '_')}/{date}.json"
        
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=file_key,
            Body=json.dumps(weather_data),
            ContentType="application/json"
        )
        
        weather_data["s3_location"] = f"s3://{S3_BUCKET}/{file_key}"
        print(f"Successfully saved to S3: {file_key}")
        
    except ClientError as e:
        error_msg = f"Failed to save to S3: {str(e)}"
        print(error_msg)
        weather_data["s3_error"] = error_msg

    return jsonify(weather_data), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=86, debug=False)