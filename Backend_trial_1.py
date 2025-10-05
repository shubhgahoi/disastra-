from flask import Flask, request, jsonify
import json
import requests
import math # NEW: Imported for distance calculation

app = Flask(__name__)

# --- NASA EONET API Configuration ---
EONET_API_URL = "https://eonet.gsfc.nasa.gov/api/v3/events"

# NEW: Haversine formula to calculate distance between two points on Earth
def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great-circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371 # Radius of earth in kilometers.
    return c * r

# --- Error Handlers ---
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not Found", "message": str(e)}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred."}), 500

# --- Existing Functions for Local Files ---
def load_messages(disaster=None):
    with open('emergency_messages.json', 'r', encoding='utf-8') as f:
        messages = json.load(f)
    if disaster:
        messages = [m for m in messages if m['disaster'].lower() == disaster.lower()]
    return messages

def load_quiz(level=None):
    with open('quiz_questions.json', 'r', encoding='utf-8') as f:
        questions = json.load(f)
    if level:
        questions = [q for q in questions if q['level'].lower() == level.lower()]
    return questions

# --- Main App Routes ---
@app.route('/')
def home():
    return "Disaster Preparedness Backend Running!"

@app.route('/emergency_messages', methods=['GET'])
def get_emergency_messages():
    disaster = request.args.get('disaster')
    messages = load_messages(disaster)
    return jsonify(messages)

@app.route('/quiz_questions', methods=['GET'])
def get_quiz_questions():
    level = request.args.get('level')
    questions = load_quiz(level)
    return jsonify(questions)

# UPDATED: This route now accepts lat/lon and filters events
@app.route('/get_events', methods=['GET'])
def get_live_events():
    # Get user location from URL parameters if they exist
    user_lat = request.args.get('lat', type=float)
    user_lon = request.args.get('lon', type=float)
    
    try:
        params = {'status': 'open', 'limit': 50, 'days': 30}
        response = requests.get(EONET_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        all_events = []
        for event in data.get('events', []):
            # Check if the event has valid geometry data
            if event.get('geometry') and event['geometry'][0]['type'] == 'Point':
                all_events.append({
                    'title': event.get('title'),
                    'category': event['categories'][0]['title'] if event.get('categories') else 'Unknown',
                    'date': event['geometry'][0]['date'],
                    'coordinates': event['geometry'][0]['coordinates'] # [lon, lat]
                })

        # If no location is provided, return all events
        if user_lat is None or user_lon is None:
            return jsonify(all_events)
            
        # If location is provided, filter the events
        nearby_events = []
        max_distance_km = 500 # Define our search radius in kilometers

        for event in all_events:
            event_lon, event_lat = event['coordinates']
            distance = haversine(user_lon, user_lat, event_lon, event_lat)
            
            if distance <= max_distance_km:
                nearby_events.append(event)
                
        return jsonify(nearby_events)

    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Could not fetch data from NASA EONET", "details": str(e)}), 502
    except Exception as e:
        app.logger.error(f"An unexpected error occurred in /get_events: {e}")
        return server_error(e)


if __name__ == '__main__':
    app.run()