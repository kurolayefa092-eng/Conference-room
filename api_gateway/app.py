from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import requests
import os
from functools import wraps
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Microservices URLs
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:84")
ROOM_SERVICE_URL = os.getenv("ROOM_SERVICE_URL", "http://room-service:85")
WEATHER_SERVICE_URL = os.getenv("WEATHER_SERVICE_URL", "http://weather-service:86")
BOOKING_SERVICE_URL = os.getenv("BOOKING_SERVICE_URL", "http://booking-service:87")

# Logging function
def log_request(service, endpoint, method, status_code):
    timestamp = datetime.utcnow().isoformat()
    print(f"[{timestamp}] {method} /{service}{endpoint} -> {status_code}")

# Authentication middleware
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({"error": "Authorization header required"}), 401
        
        # Verify token with auth service
        try:
            # The auth service just needs the Authorization header, not a JSON body
            verify_response = requests.post(
                f"{AUTH_SERVICE_URL}/api/auth/verify",
                headers={"Authorization": auth_header}
            )
            
            if verify_response.status_code != 200:
                return jsonify({"error": "Invalid or expired token"}), 401
                
        except Exception as e:
            return jsonify({"error": f"Authentication failed: {str(e)}"}), 500
        
        return f(*args, **kwargs)
    
    return decorated_function

# Proxy function to forward requests
def proxy_request(service_url, path, method='GET', data=None, headers=None):
    try:
        url = f"{service_url}{path}"
        
        # Prepare headers
        req_headers = {}
        if headers:
            req_headers.update(headers)
        
        # Forward the request
        if method == 'GET':
            response = requests.get(url, headers=req_headers, params=request.args)
        elif method == 'POST':
            response = requests.post(url, json=data or request.get_json(), headers=req_headers)
        elif method == 'PUT':
            response = requests.put(url, json=data or request.get_json(), headers=req_headers)
        elif method == 'DELETE':
            response = requests.delete(url, headers=req_headers)
        else:
            return jsonify({"error": "Method not allowed"}), 405
        
        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get('Content-Type', 'application/json')
        )
        
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Service unavailable: {str(e)}"}), 503

# ==========================================
# HEALTH CHECK
# ==========================================
@app.route("/health", methods=["GET"])
def health():
    # Check all services health
    services_status = {}
    
    services = {
        "auth": f"{AUTH_SERVICE_URL}/health",
        "room": f"{ROOM_SERVICE_URL}/health",
        "weather": f"{WEATHER_SERVICE_URL}/health",
        "booking": f"{BOOKING_SERVICE_URL}/health"
    }
    
    all_healthy = True
    for service_name, health_url in services.items():
        try:
            response = requests.get(health_url, timeout=2)
            services_status[service_name] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "code": response.status_code
            }
            if response.status_code != 200:
                all_healthy = False
        except Exception as e:
            services_status[service_name] = {
                "status": "unhealthy",
                "error": str(e)
            }
            all_healthy = False
    
    return jsonify({
        "gateway": "healthy",
        "services": services_status,
        "overall": "healthy" if all_healthy else "degraded"
    }), 200 if all_healthy else 503

# ==========================================
# AUTH SERVICE ROUTES (Public - No Auth Required)
# ==========================================
@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    log_request("auth", "/register", "POST", "->")
    response = proxy_request(AUTH_SERVICE_URL, "/api/auth/register", method='POST')
    log_request("auth", "/register", "POST", response.status_code)
    return response

@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    log_request("auth", "/login", "POST", "->")
    response = proxy_request(AUTH_SERVICE_URL, "/api/auth/login", method='POST')
    log_request("auth", "/login", "POST", response.status_code)
    return response

@app.route("/api/auth/verify", methods=["POST"])
def auth_verify():
    log_request("auth", "/verify", "POST", "->")
    headers = {"Authorization": request.headers.get("Authorization")}
    response = proxy_request(AUTH_SERVICE_URL, "/api/auth/verify", method='POST', headers=headers)
    log_request("auth", "/verify", "POST", response.status_code)
    return response

# ==========================================
# ROOM SERVICE ROUTES (Public for viewing, Auth for modifications)
# ==========================================
@app.route("/api/rooms", methods=["GET"])
def get_rooms():
    log_request("room", "/rooms", "GET", "->")
    response = proxy_request(ROOM_SERVICE_URL, "/api/rooms", method='GET')
    log_request("room", "/rooms", "GET", response.status_code)
    return response

@app.route("/api/rooms/<room_id>", methods=["GET"])
def get_room(room_id):
    log_request("room", f"/rooms/{room_id}", "GET", "->")
    response = proxy_request(ROOM_SERVICE_URL, f"/api/rooms/{room_id}", method='GET')
    log_request("room", f"/rooms/{room_id}", "GET", response.status_code)
    return response

@app.route("/api/rooms", methods=["POST"])
@require_auth
def create_room():
    log_request("room", "/rooms", "POST", "->")
    response = proxy_request(ROOM_SERVICE_URL, "/api/rooms", method='POST')
    log_request("room", "/rooms", "POST", response.status_code)
    return response

@app.route("/api/rooms/<room_id>", methods=["PUT"])
@require_auth
def update_room(room_id):
    log_request("room", f"/rooms/{room_id}", "PUT", "->")
    response = proxy_request(ROOM_SERVICE_URL, f"/api/rooms/{room_id}", method='PUT')
    log_request("room", f"/rooms/{room_id}", "PUT", response.status_code)
    return response

@app.route("/api/rooms/<room_id>", methods=["DELETE"])
@require_auth
def delete_room(room_id):
    log_request("room", f"/rooms/{room_id}", "DELETE", "->")
    response = proxy_request(ROOM_SERVICE_URL, f"/api/rooms/{room_id}", method='DELETE')
    log_request("room", f"/rooms/{room_id}", "DELETE", response.status_code)
    return response

# ==========================================
# WEATHER SERVICE ROUTES (Public)
# ==========================================
@app.route("/api/weather/forecast", methods=["POST"])
def get_weather_forecast():
    log_request("weather", "/forecast", "POST", "->")
    response = proxy_request(WEATHER_SERVICE_URL, "/api/weather/forecast", method='POST')
    log_request("weather", "/forecast", "POST", response.status_code)
    return response

@app.route("/api/weather/forecast/<location>", methods=["GET"])
def get_forecasts_by_location(location):
    log_request("weather", f"/forecast/{location}", "GET", "->")
    response = proxy_request(WEATHER_SERVICE_URL, f"/api/weather/forecast/{location}", method='GET')
    log_request("weather", f"/forecast/{location}", "GET", response.status_code)
    return response

@app.route("/api/weather/forecasts", methods=["GET"])
def get_all_forecasts():
    log_request("weather", "/forecasts", "GET", "->")
    response = proxy_request(WEATHER_SERVICE_URL, "/api/weather/forecasts", method='GET')
    log_request("weather", "/forecasts", "GET", response.status_code)
    return response

# ==========================================
# BOOKING SERVICE ROUTES (Require Auth)
# ==========================================
@app.route("/api/booking/check-availability", methods=["POST"])
def check_availability():
    log_request("booking", "/check-availability", "POST", "->")
    response = proxy_request(BOOKING_SERVICE_URL, "/api/booking/check-availability", method='POST')
    log_request("booking", "/check-availability", "POST", response.status_code)
    return response

@app.route("/api/booking/confirm", methods=["POST"])
@require_auth
def confirm_booking():
    log_request("booking", "/confirm", "POST", "->")
    response = proxy_request(BOOKING_SERVICE_URL, "/api/booking/confirm", method='POST')
    log_request("booking", "/confirm", "POST", response.status_code)
    return response

@app.route("/api/booking/my-bookings", methods=["GET"])
@require_auth
def get_my_bookings():
    log_request("booking", "/my-bookings", "GET", "->")
    response = proxy_request(BOOKING_SERVICE_URL, "/api/booking/my-bookings", method='GET')
    log_request("booking", "/my-bookings", "GET", response.status_code)
    return response

@app.route("/api/booking/all", methods=["GET"])
@require_auth
def get_all_bookings():
    log_request("booking", "/all", "GET", "->")
    response = proxy_request(BOOKING_SERVICE_URL, "/api/booking/all", method='GET')
    log_request("booking", "/all", "GET", response.status_code)
    return response

@app.route("/api/booking/<booking_id>", methods=["GET"])
@require_auth
def get_booking(booking_id):
    log_request("booking", f"/{booking_id}", "GET", "->")
    response = proxy_request(BOOKING_SERVICE_URL, f"/api/booking/{booking_id}", method='GET')
    log_request("booking", f"/{booking_id}", "GET", response.status_code)
    return response

@app.route("/api/booking/cancel/<booking_id>", methods=["DELETE"])
@require_auth
def cancel_booking(booking_id):
    log_request("booking", f"/cancel/{booking_id}", "DELETE", "->")
    response = proxy_request(BOOKING_SERVICE_URL, f"/api/booking/cancel/{booking_id}", method='DELETE')
    log_request("booking", f"/cancel/{booking_id}", "DELETE", response.status_code)
    return response

# ==========================================
# ERROR HANDLERS
# ==========================================
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=False)