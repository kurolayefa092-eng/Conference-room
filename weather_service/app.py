from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import random
import json
import boto3
import os
from botocore.exceptions import ClientError

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
IDEAL_TEMP = 21
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'conference-room-weather-forecasts')

# Initialize S3
try:
    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', ''),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', ''),
        region_name=os.getenv('AWS_REGION', 'eu-west-2')
    )
except Exception as e:
    print(f"S3 Init Warning: {e}")
    s3_client = None

# --- LOGIC FUNCTIONS ---

def calculate_charge(temp):
    """Lecturer's specific pricing tiers"""
    diff = abs(temp - IDEAL_TEMP)
    if diff < 2: return 0.0
    if diff < 5: return 0.10
    if diff < 10: return 0.20
    if diff < 20: return 0.30
    return 0.50

def save_to_s3(data):
    """Storage logic to keep a record of the forecast"""
    if not s3_client:
        return {"stored": False, "error": "S3 Client not initialized"}
    
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    filename = f"forecasts/{data['city']}_{data['date']}_{timestamp}.json"
    
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=filename,
            Body=json.dumps(data),
            ContentType='application/json'
        )
        return {"stored": True, "key": filename}
    except ClientError as e:
        return {"stored": False, "error": str(e)}

# --- ENDPOINTS ---

@app.route('/api/weather/forecast', methods=['GET'])
def get_weather():
    location = request.args.get('location', 'London')
    date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    # Simulate Temperature
    simulated_temp = round(random.uniform(-5, 35), 1) 
    charge_pct = calculate_charge(simulated_temp)
    
    forecast_results = {
        "city": location,
        "date": date_str,
        "temp": simulated_temp,
        "ideal": IDEAL_TEMP,
        "diff": round(abs(simulated_temp - IDEAL_TEMP), 1),
        "additional_charge_pct": charge_pct * 100,
        "processed_at": datetime.now().isoformat()
    }
    
    # PERSISTENCE: Save the calculation to S3
    storage_status = save_to_s3(forecast_results)
    forecast_results['storage'] = storage_status
    
    return jsonify(forecast_results), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=86, debug=True)