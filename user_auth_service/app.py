from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import os

app = Flask(__name__)
CORS(app)

# MongoDB connection
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://mongodb:27017/')
client = MongoClient(MONGO_URI)
db = client['auth_db']
users_collection = db['users']

# Logged in users (stores tokens in memory)
logged_in_users = {}

# Health check endpoint
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"message": "Auth service is running on port 84"}), 200

# Register new user
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    
    # Check if all fields are provided
    if not email or not password or not name:
        return jsonify({"error": "Missing fields"}), 400
    
    # Check if user exists in MongoDB
    if users_collection.find_one({"email": email}):
        return jsonify({"error": "User already exists"}), 400
    
    # Save new user to MongoDB
    user_data = {
        "name": name,
        "email": email,
        "password": password  # In production, hash this!
    }
    users_collection.insert_one(user_data)
    
    return jsonify({"message": "User registered successfully"}), 201

# Login user
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    # Check if fields are provided
    if not email or not password:
        return jsonify({"error": "Missing email or password"}), 400
    
    # Find user in MongoDB
    user = users_collection.find_one({"email": email})
    
    if not user:
        return jsonify({"error": "Invalid email or password"}), 401
    
    # Check password
    if user["password"] != password:
        return jsonify({"error": "Invalid email or password"}), 401
    
    # Create simple token
    token = f"token_{email}"
    logged_in_users[token] = email
    
    return jsonify({
        "message": "Login successful",
        "token": token,
        "user": {"name": user["name"], "email": user["email"]}
    }), 200

# Get current user info
@app.route('/api/auth/me', methods=['GET'])
def get_me():
    # Get token from header
    token = request.headers.get('Authorization')
    
    if not token:
        return jsonify({"error": "No token provided"}), 401
    
    # Remove "Bearer " if present
    token = token.replace("Bearer ", "")
    
    # Check if token is valid
    if token not in logged_in_users:
        return jsonify({"error": "Invalid token"}), 401
    
    email = logged_in_users[token]
    user = users_collection.find_one({"email": email})
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({
        "name": user["name"],
        "email": user["email"]
    }), 200

# Get all users (for testing and viewing in browser)
@app.route('/api/auth/users', methods=['GET'])
def get_all_users():
    users = list(users_collection.find({}, {"_id": 0, "password": 0}))
    return jsonify({"users": users}), 200

# Logout
@app.route('/api/auth/logout', methods=['POST'])
def logout():
    token = request.headers.get('Authorization')
    
    if token:
        token = token.replace("Bearer ", "")
        if token in logged_in_users:
            del logged_in_users[token]
    
    return jsonify({"message": "Logged out successfully"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=84, debug=True)