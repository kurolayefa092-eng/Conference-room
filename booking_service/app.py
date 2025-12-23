from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import requests
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://booking-mongodb:27017/")
client = MongoClient(MONGO_URI)
db = client["booking_service"]
bookings_collection = db["bookings"]

# Microservices URLs
ROOM_SERVICE_URL = os.getenv("ROOM_SERVICE_URL", "http://room-service:85")
WEATHER_SERVICE_URL = os.getenv("WEATHER_SERVICE_URL", "http://weather-service:86")

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"message": "Booking service running on port 87"}), 200

@app.route("/api/booking/check-availability", methods=["POST"])
def check_availability():
    """
    Check if a room is available and get price with weather adjustment
    Request body: {
        "room_id": "LIV001",
        "date": "2024-12-25"
    }
    """
    data = request.get_json()
    room_id = data.get("room_id")
    date = data.get("date")
    
    if not room_id or not date:
        return jsonify({"error": "room_id and date are required"}), 400
    
    # 1. Check if room exists
    try:
        room_response = requests.get(f"{ROOM_SERVICE_URL}/api/rooms/{room_id}")
        if room_response.status_code != 200:
            return jsonify({"error": "Room not found"}), 404
        
        room_data = room_response.json()
    except Exception as e:
        return jsonify({"error": f"Failed to fetch room data: {str(e)}"}), 500
    
    # 2. Check if room is already booked for this date
    existing_booking = bookings_collection.find_one({
        "room_id": room_id,
        "date": date,
        "status": "confirmed"
    })
    
    if existing_booking:
        return jsonify({
            "available": False,
            "message": "This room is already booked for the selected date. Please try another room or date.",
            "room": room_data,
            "existing_booking": {
                "booking_id": str(existing_booking["_id"]),
                "booked_by": existing_booking.get("client_name", "Unknown"),
                "date": existing_booking["date"]
            }
        }), 200
    
    # 3. Get weather forecast and calculate price
    try:
        weather_response = requests.post(
            f"{WEATHER_SERVICE_URL}/api/weather/forecast",
            json={
                "location": room_data["location"],
                "date": date,
                "base_price": room_data["price_per_day"]
            }
        )
        
        if weather_response.status_code != 200:
            return jsonify({"error": "Failed to get weather forecast"}), 500
        
        weather_data = weather_response.json()
    except Exception as e:
        return jsonify({"error": f"Failed to fetch weather data: {str(e)}"}), 500
    
    # 4. Return availability with pricing
    return jsonify({
        "available": True,
        "message": "Room is available for booking",
        "room": room_data,
        "pricing": {
            "base_price": room_data["price_per_day"],
            "forecasted_temperature": weather_data["forecasted_temperature"],
            "temperature_difference": weather_data["temperature_difference"],
            "additional_charge_percentage": weather_data["additional_charge_percentage"],
            "additional_charge_amount": weather_data["additional_charge_amount"],
            "final_price": weather_data["final_price"]
        },
        "date": date
    }), 200

@app.route("/api/booking/confirm", methods=["POST"])
def confirm_booking():
    """
    Confirm a booking after user sees the price
    Request body: {
        "room_id": "LIV001",
        "date": "2024-12-25",
        "client_name": "John Doe",
        "client_email": "john@example.com"
    }
    """
    data = request.get_json()
    room_id = data.get("room_id")
    date = data.get("date")
    client_name = data.get("client_name")
    client_email = data.get("client_email")
    
    if not all([room_id, date, client_name, client_email]):
        return jsonify({
            "error": "room_id, date, client_name, and client_email are required"
        }), 400
    
    # 1. Double-check availability (prevent race conditions)
    existing_booking = bookings_collection.find_one({
        "room_id": room_id,
        "date": date,
        "status": "confirmed"
    })
    
    if existing_booking:
        return jsonify({
            "success": False,
            "message": "Sorry! This room was just booked by another client. Please try another room or date."
        }), 409
    
    # 2. Get room details
    try:
        room_response = requests.get(f"{ROOM_SERVICE_URL}/api/rooms/{room_id}")
        if room_response.status_code != 200:
            return jsonify({"error": "Room not found"}), 404
        
        room_data = room_response.json()
    except Exception as e:
        return jsonify({"error": f"Failed to fetch room data: {str(e)}"}), 500
    
    # 3. Get weather and pricing
    try:
        weather_response = requests.post(
            f"{WEATHER_SERVICE_URL}/api/weather/forecast",
            json={
                "location": room_data["location"],
                "date": date,
                "base_price": room_data["price_per_day"]
            }
        )
        
        weather_data = weather_response.json()
    except Exception as e:
        return jsonify({"error": f"Failed to fetch weather data: {str(e)}"}), 500
    
    # 4. Create booking
    booking = {
        "room_id": room_id,
        "room_name": room_data["name"],
        "location": room_data["location"],
        "date": date,
        "client_name": client_name,
        "client_email": client_email,
        "base_price": room_data["price_per_day"],
        "weather_adjustment": {
            "forecasted_temperature": weather_data["forecasted_temperature"],
            "temperature_difference": weather_data["temperature_difference"],
            "additional_charge_percentage": weather_data["additional_charge_percentage"],
            "additional_charge_amount": weather_data["additional_charge_amount"]
        },
        "final_price": weather_data["final_price"],
        "status": "confirmed",
        "booked_at": datetime.utcnow().isoformat()
    }
    
    try:
        result = bookings_collection.insert_one(booking)
        booking["_id"] = str(result.inserted_id)
        
        return jsonify({
            "success": True,
            "message": f"Booking confirmed successfully! {room_data['name']} is booked for {date}.",
            "booking": booking
        }), 201
    except Exception as e:
        return jsonify({"error": f"Failed to create booking: {str(e)}"}), 500

@app.route("/api/booking/my-bookings", methods=["GET"])
def get_my_bookings():
    """
    Get all bookings for a client
    Query param: email
    """
    email = request.args.get("email")
    
    if not email:
        return jsonify({"error": "email parameter is required"}), 400
    
    try:
        bookings = list(bookings_collection.find({"client_email": email}))
        for booking in bookings:
            booking["_id"] = str(booking["_id"])
        
        return jsonify({
            "email": email,
            "count": len(bookings),
            "bookings": bookings
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/booking/all", methods=["GET"])
def get_all_bookings():
    """Get all bookings (admin view)"""
    try:
        bookings = list(bookings_collection.find())
        for booking in bookings:
            booking["_id"] = str(booking["_id"])
        
        return jsonify({
            "count": len(bookings),
            "bookings": bookings
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/booking/<booking_id>", methods=["GET"])
def get_booking(booking_id):
    """Get a specific booking by ID"""
    try:
        from bson.objectid import ObjectId
        booking = bookings_collection.find_one({"_id": ObjectId(booking_id)})
        
        if not booking:
            return jsonify({"error": "Booking not found"}), 404
        
        booking["_id"] = str(booking["_id"])
        return jsonify(booking), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/booking/cancel/<booking_id>", methods=["DELETE"])
def cancel_booking(booking_id):
    """Cancel a booking"""
    try:
        from bson.objectid import ObjectId
        result = bookings_collection.update_one(
            {"_id": ObjectId(booking_id)},
            {"$set": {"status": "cancelled", "cancelled_at": datetime.utcnow().isoformat()}}
        )
        
        if result.modified_count == 0:
            return jsonify({"error": "Booking not found"}), 404
        
        return jsonify({
            "success": True,
            "message": "Booking cancelled successfully"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=87, debug=False)