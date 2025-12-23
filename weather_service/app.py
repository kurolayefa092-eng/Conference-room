from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import random
import os
from datetime import datetime
import requests
from urllib.parse import urljoin

app = Flask(__name__)
CORS(app)

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://weather-mongodb:27017/")
client = MongoClient(MONGO_URI)
db = client["weather_service"]
forecasts_collection = db["forecasts"]
bookings_collection = db["bookings"]

# Room Service Configuration
ROOM_SERVICE_URL = os.getenv("ROOM_SERVICE_URL", "http://room-service:85")

BASE_TEMP = 21  # degrees C

def calculate_surcharge(temp_diff):
    """Calculate surcharge percentage based on temperature difference from base temp"""
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

def get_room_price(room_id):
    """Fetch room price from room service"""
    try:
        room_service_url = urljoin(ROOM_SERVICE_URL, f"/api/rooms/{room_id}")
        response = requests.get(room_service_url, timeout=5)
        if response.status_code == 200:
            room_data = response.json()
            return room_data.get("price_per_day", 0), room_data.get("name", "Unknown"), room_data.get("location", "Unknown")
        else:
            return None, None, None
    except Exception as e:
        print(f"Error fetching room price: {e}")
        return None, None, None

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"message": "Weather & Booking service running on port 86"}), 200

# Fetch weather forecast + calculate final price based on room service price
@app.route("/api/weather/forecast", methods=["POST"])
def get_weather_forecast():
    """Get weather forecast and calculate price based on room service pricing"""
    data = request.get_json()
    location = data.get("location")
    date = data.get("date")
    room_id = data.get("room_id")

    if not location or not date:
        return jsonify({"error": "Location and date are required"}), 400

    # Fetch base price from room service if room_id provided
    base_price = 0
    room_name = "Unknown"
    if room_id:
        base_price, room_name, _ = get_room_price(room_id)
        if base_price is None:
            return jsonify({"error": f"Room {room_id} not found in room service"}), 404

    # Check if forecast already exists for this location and date
    forecast = forecasts_collection.find_one({"location": location, "date": date})
    if not forecast:
        # Generate new forecast
        forecast_temp = random.randint(-5, 35)
        temp_diff = abs(forecast_temp - BASE_TEMP)
        surcharge_percentage = calculate_surcharge(temp_diff)
        additional_charge = (surcharge_percentage / 100) * base_price
        final_price = base_price + additional_charge

        forecast = {
            "location": location,
            "date": date,
            "forecasted_temperature": forecast_temp,
            "temperature_difference": temp_diff,
            "additional_charge_percentage": surcharge_percentage,
            "additional_charge_amount": round(additional_charge, 2),
            "final_price": round(final_price, 2),
            "base_price": base_price,
            "room_id": room_id,
            "room_name": room_name,
            "generated_at": datetime.utcnow().isoformat()
        }
        forecasts_collection.insert_one(forecast)
    else:
        # Recalculate if base price changed
        if base_price > 0 and forecast.get("base_price") != base_price:
            temp_diff = forecast.get("temperature_difference", 0)
            surcharge_percentage = forecast.get("additional_charge_percentage", 0)
            additional_charge = (surcharge_percentage / 100) * base_price
            final_price = base_price + additional_charge
            
            forecast["base_price"] = base_price
            forecast["room_id"] = room_id
            forecast["room_name"] = room_name
            forecast["additional_charge_amount"] = round(additional_charge, 2)
            forecast["final_price"] = round(final_price, 2)
            
            forecasts_collection.update_one(
                {"location": location, "date": date},
                {"$set": forecast}
            )
        
        forecast["_id"] = str(forecast["_id"])

    return jsonify(forecast), 200

# Check room availability
# Check room availability
@app.route("/api/booking/check-availability", methods=["POST"])
def check_availability():
    """Check if room is available and return pricing with weather adjustment"""
    data = request.get_json()
    room_id = data.get("room_id")
    date = data.get("date")
    location = data.get("location", "Unknown")

    if not room_id or not date:
        return jsonify({"error": "room_id and date are required"}), 400

    # Fetch room details and price from room service
    base_price, room_name, room_location = get_room_price(room_id)
    if base_price is None:
        return jsonify({"error": f"Room {room_id} not found"}), 404

    # Use room location if available
    if room_location:
        location = room_location

    # Check if room is already booked for this date
    existing_booking = bookings_collection.find_one({
        "room_id": room_id,
        "date": date,
        "status": "confirmed"
    })

    available = existing_booking is None

    # Get or generate forecast with weather-adjusted pricing
    forecast_resp = forecasts_collection.find_one({"location": location, "date": date})
    if forecast_resp:
        # Recalculate pricing with current room price
        temp_diff = forecast_resp.get("temperature_difference", 0)
        surcharge_percentage = calculate_surcharge(temp_diff)
        additional_charge = (surcharge_percentage / 100) * base_price
        final_price = base_price + additional_charge

        forecast_resp = {
            "location": location,
            "date": date,
            "forecasted_temperature": forecast_resp["forecasted_temperature"],
            "temperature_difference": temp_diff,
            "additional_charge_percentage": surcharge_percentage,
            "additional_charge_amount": round(additional_charge, 2),
            "final_price": round(final_price, 2),
            "base_price": base_price,
            "room_id": room_id,
            "room_name": room_name
        }
    else:
        # Generate new forecast
        forecast_resp = get_weather_forecast_data(location, date, base_price, room_id, room_name)

    return jsonify({
        "available": available,
        "room_id": room_id,
        "room_name": room_name,
        "pricing": forecast_resp,
        "existing_booking": existing_booking if existing_booking else None
    }), 200

def get_weather_forecast_data(location, date, base_price, room_id="", room_name="Unknown"):
    """Generate weather forecast and calculate pricing"""
    forecast_temp = random.randint(-5, 35)
    temp_diff = abs(forecast_temp - BASE_TEMP)
    surcharge_percentage = calculate_surcharge(temp_diff)
    additional_charge = (surcharge_percentage / 100) * base_price
    final_price = base_price + additional_charge

    forecast = {
        "location": location,
        "date": date,
        "forecasted_temperature": forecast_temp,
        "temperature_difference": temp_diff,
        "additional_charge_percentage": surcharge_percentage,
        "additional_charge_amount": round(additional_charge, 2),
        "final_price": round(final_price, 2),
        "base_price": base_price,
        "room_id": room_id,
        "room_name": room_name,
        "generated_at": datetime.utcnow().isoformat()
    }
    result = forecasts_collection.insert_one(forecast)
    forecast["_id"] = str(result.inserted_id)
    return forecast

# Confirm booking - Mark room as booked
@app.route("/api/booking/confirm", methods=["POST"])
def confirm_booking():
    """Confirm and save booking, preventing double-booking"""
    data = request.get_json()
    room_id = data.get("room_id")
    date = data.get("date")
    client_name = data.get("client_name")
    client_email = data.get("client_email")

    if not all([room_id, date, client_name, client_email]):
        return jsonify({"error": "room_id, date, client_name, and client_email are required"}), 400

    # Fetch room details from room service
    base_price, room_name, location = get_room_price(room_id)
    if base_price is None:
        return jsonify({"error": f"Room {room_id} not found"}), 404

    # Double-check: Ensure room is not already booked
    existing_booking = bookings_collection.find_one({
        "room_id": room_id,
        "date": date,
        "status": "confirmed"
    })
    if existing_booking:
        return jsonify({
            "success": False,
            "message": "Room already booked for this date",
            "booked_by": existing_booking.get("client_name"),
            "booked_at": existing_booking.get("booked_at")
        }), 409

    # Get or generate forecast
    forecast = forecasts_collection.find_one({"location": location, "date": date})
    if not forecast:
        forecast = get_weather_forecast_data(location, date, base_price, room_id, room_name)
    else:
        # Ensure pricing is current
        temp_diff = forecast.get("temperature_difference", 0)
        surcharge_percentage = calculate_surcharge(temp_diff)
        additional_charge = (surcharge_percentage / 100) * base_price
        final_price = base_price + additional_charge
        
        forecast["_id"] = str(forecast["_id"])
        forecast["additional_charge_amount"] = round(additional_charge, 2)
        forecast["final_price"] = round(final_price, 2)
        forecast["base_price"] = base_price

    # Create and save booking
    booking = {
        "room_id": room_id,
        "room_name": room_name,
        "location": location,
        "date": date,
        "client_name": client_name,
        "client_email": client_email,
        "base_price": base_price,
        "weather_adjustment": {
            "forecasted_temperature": forecast["forecasted_temperature"],
            "temperature_difference": forecast["temperature_difference"],
            "additional_charge_percentage": forecast["additional_charge_percentage"],
            "additional_charge_amount": forecast["additional_charge_amount"]
        },
        "final_price": forecast["final_price"],
        "status": "confirmed",
        "booked_at": datetime.utcnow().isoformat()
    }

    try:
        result = bookings_collection.insert_one(booking)
        booking["_id"] = str(result.inserted_id)

        return jsonify({
            "success": True,
            "message": "Booking confirmed successfully",
            "booking": booking
        }), 201
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error creating booking: {str(e)}"
        }), 500

# Get all bookings for a room on a specific date
@app.route("/api/booking/room/<room_id>/<date>", methods=["GET"])
def get_room_bookings(room_id, date):
    """Get all bookings for a specific room on a specific date"""
    bookings = list(bookings_collection.find({
        "room_id": room_id,
        "date": date,
        "status": "confirmed"
    }))
    
    for booking in bookings:
        booking["_id"] = str(booking["_id"])
    
    return jsonify({
        "room_id": room_id,
        "date": date,
        "bookings": bookings,
        "is_booked": len(bookings) > 0
    }), 200

# Cancel booking
@app.route("/api/booking/cancel/<booking_id>", methods=["POST"])
def cancel_booking(booking_id):
    """Cancel a booking and free up the room"""
    from bson.objectid import ObjectId
    
    try:
        result = bookings_collection.update_one(
            {"_id": ObjectId(booking_id)},
            {"$set": {"status": "cancelled", "cancelled_at": datetime.utcnow().isoformat()}}
        )
        
        if result.matched_count == 0:
            return jsonify({"error": "Booking not found"}), 404
        
        return jsonify({
            "success": True,
            "message": "Booking cancelled successfully"
        }), 200
    except Exception as e:
        return jsonify({
            "error": f"Error cancelling booking: {str(e)}"
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=86, debug=True)