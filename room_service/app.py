from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import os

app = Flask(__name__)
CORS(app)

# MongoDB connection
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://mongodb:27017/')
client = MongoClient(MONGO_URI)
db = client['room_db']
rooms_collection = db['rooms']

# Health check endpoint
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"message": "Room service is running on port 85"}), 200

# Get all rooms
@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    rooms = list(rooms_collection.find({}, {"_id": 0}))
    return jsonify({"rooms": rooms, "count": len(rooms)}), 200

# Get room by ID
@app.route('/api/rooms/<room_id>', methods=['GET'])
def get_room(room_id):
    room = rooms_collection.find_one({"room_id": room_id}, {"_id": 0})
    if not room:
        return jsonify({"error": "Room not found"}), 404
    return jsonify(room), 200

# Filter rooms by capacity
@app.route('/api/rooms/filter/capacity', methods=['GET'])
def filter_by_capacity():
    min_capacity = request.args.get('min', type=int, default=0)
    max_capacity = request.args.get('max', type=int, default=1000)
    
    rooms = list(rooms_collection.find({
        "capacity": {"$gte": min_capacity, "$lte": max_capacity}
    }, {"_id": 0}))
    
    return jsonify({"rooms": rooms, "count": len(rooms)}), 200

# Filter rooms by location
@app.route('/api/rooms/filter/location', methods=['GET'])
def filter_by_location():
    location = request.args.get('location', type=str)
    if not location:
        return jsonify({"error": "Location parameter required"}), 400
    
    rooms = list(rooms_collection.find({
        "location": {"$regex": location, "$options": "i"}
    }, {"_id": 0}))
    
    return jsonify({"rooms": rooms, "count": len(rooms)}), 200

# Filter rooms by price range
@app.route('/api/rooms/filter/price', methods=['GET'])
def filter_by_price():
    min_price = request.args.get('min', type=float, default=0)
    max_price = request.args.get('max', type=float, default=10000)
    
    rooms = list(rooms_collection.find({
        "price_per_hour": {"$gte": min_price, "$lte": max_price}
    }, {"_id": 0}))
    
    return jsonify({"rooms": rooms, "count": len(rooms)}), 200

# Initialize database with sample rooms
@app.route('/api/rooms/seed', methods=['POST'])
def seed_rooms():
    # Check if already seeded
    if rooms_collection.count_documents({}) > 0:
        return jsonify({"message": "Database already contains rooms"}), 200
    
    # UK Conference Rooms Data with prices
    uk_rooms = [
        {
            "room_id": "LON001",
            "name": "The Churchill Room",
            "location": "London, Westminster",
            "capacity": 50,
            "price_per_hour": 150.00,
            "price_per_day": 1000.00,
            "amenities": ["Projector", "Video Conference", "Whiteboard", "WiFi"],
            "description": "Named after Winston Churchill, perfect for executive meetings"
        },
        {
            "room_id": "LON002",
            "name": "Thames View Conference Hall",
            "location": "London, South Bank",
            "capacity": 200,
            "price_per_hour": 350.00,
            "price_per_day": 2500.00,
            "amenities": ["Stage", "Audio System", "Projector", "Catering Available"],
            "description": "Large conference hall with stunning Thames views"
        },
        {
            "room_id": "LON003",
            "name": "The Boardroom at Canary Wharf",
            "location": "London, Canary Wharf",
            "capacity": 20,
            "price_per_hour": 200.00,
            "price_per_day": 1400.00,
            "amenities": ["Smart Board", "Video Conference", "Coffee Machine"],
            "description": "Premium boardroom in the heart of London's financial district"
        },
        {
            "room_id": "MAN001",
            "name": "Northern Innovation Hub",
            "location": "Manchester, City Centre",
            "capacity": 100,
            "price_per_hour": 120.00,
            "price_per_day": 850.00,
            "amenities": ["Projector", "Sound System", "WiFi", "Breakout Rooms"],
            "description": "Modern space for tech conferences and innovation summits"
        },
        {
            "room_id": "MAN002",
            "name": "Media City Conference Room",
            "location": "Manchester, Salford Quays",
            "capacity": 75,
            "price_per_hour": 100.00,
            "price_per_day": 700.00,
            "amenities": ["Video Production", "Streaming Equipment", "Green Screen"],
            "description": "State-of-the-art facility for media and digital events"
        },
        {
            "room_id": "BIR001",
            "name": "Bullring Business Suite",
            "location": "Birmingham, City Centre",
            "capacity": 40,
            "price_per_hour": 80.00,
            "price_per_day": 550.00,
            "amenities": ["Projector", "Video Conference", "Catering"],
            "description": "Central location ideal for midlands business meetings"
        },
        {
            "room_id": "EDI001",
            "name": "Edinburgh Castle View Room",
            "location": "Edinburgh, Old Town",
            "capacity": 60,
            "price_per_hour": 110.00,
            "price_per_day": 800.00,
            "amenities": ["Projector", "WiFi", "Historic Setting"],
            "description": "Elegant room with views of Edinburgh Castle"
        },
        {
            "room_id": "EDI002",
            "name": "Scottish Parliament Conference Hall",
            "location": "Edinburgh, Holyrood",
            "capacity": 150,
            "price_per_hour": 180.00,
            "price_per_day": 1300.00,
            "amenities": ["Stage", "Audio System", "Translation Booths"],
            "description": "Professional venue near the Scottish Parliament"
        },
        {
            "room_id": "GLA001",
            "name": "Clyde Riverside Meeting Room",
            "location": "Glasgow, City Centre",
            "capacity": 30,
            "price_per_hour": 75.00,
            "price_per_day": 500.00,
            "amenities": ["Smart Board", "Video Conference", "River Views"],
            "description": "Modern riverside venue in Glasgow's business district"
        },
        {
            "room_id": "BRI001",
            "name": "Harbourside Innovation Centre",
            "location": "Bristol, Harbourside",
            "capacity": 80,
            "price_per_hour": 95.00,
            "price_per_day": 650.00,
            "amenities": ["Projector", "Sound System", "WiFi", "Outdoor Terrace"],
            "description": "Creative space for tech and innovation events"
        },
        {
            "room_id": "LEE001",
            "name": "Yorkshire Business Hub",
            "location": "Leeds, City Centre",
            "capacity": 45,
            "price_per_hour": 70.00,
            "price_per_day": 480.00,
            "amenities": ["Projector", "Video Conference", "Catering Kitchen"],
            "description": "Versatile space in Leeds' business quarter"
        },
        {
            "room_id": "LIV001",
            "name": "Albert Dock Conference Suite",
            "location": "Liverpool, Albert Dock",
            "capacity": 120,
            "price_per_hour": 130.00,
            "price_per_day": 900.00,
            "amenities": ["Stage", "Audio Visual", "Waterfront Views"],
            "description": "Historic dockside venue for large conferences"
        }
    ]
    
    rooms_collection.insert_many(uk_rooms)
    
    return jsonify({
        "message": "Database seeded successfully",
        "rooms_added": len(uk_rooms)
    }), 201

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=85, debug=True)