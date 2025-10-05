from flask import Flask, request, jsonify, send_from_directory
import json
import requests
import math
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# --- CONFIGURATION ---
EONET_API_URL = "https://eonet.gsfc.nasa.gov/api/v3/events"
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- HELPER FUNCTIONS ---

def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371 # Radius of earth in kilometers.
    return c * r

def read_json_file(filename, default_data):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return default_data

def write_json_file(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

# --- ERROR HANDLERS & EXISTING ROUTES ---
# (No changes to these parts)

@app.errorhandler(404)
def not_found(e): return jsonify({"error": "Not Found", "message": str(e)}), 404
@app.errorhandler(500)
def server_error(e): return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred."}), 500

@app.route('/')
def home(): return "Disaster Preparedness Backend Running!"
@app.route('/emergency_messages', methods=['GET'])
def get_emergency_messages():
    disaster = request.args.get('disaster')
    with open('emergency_messages.json', 'r', encoding='utf-8') as f: messages = json.load(f)
    if disaster: messages = [m for m in messages if m['disaster'].lower() == disaster.lower()]
    return jsonify(messages)

@app.route('/quiz_questions', methods=['GET'])
def get_quiz_questions():
    level = request.args.get('level')
    with open('quiz_questions.json', 'r', encoding='utf-8') as f: questions = json.load(f)
    if level: questions = [q for q in questions if q['level'].lower() == level.lower()]
    return jsonify(questions)

@app.route('/get_events', methods=['GET'])
def get_live_events():
    user_lat = request.args.get('lat', type=float)
    user_lon = request.args.get('lon', type=float)
    try:
        params = {'status': 'open', 'limit': 50, 'days': 30}
        response = requests.get(EONET_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        all_events = []
        for event in data.get('events', []):
            if event.get('geometry') and event['geometry'][0]['type'] == 'Point':
                all_events.append({'title': event.get('title'), 'category': event['categories'][0]['title'] if event.get('categories') else 'Unknown', 'date': event['geometry'][0]['date'], 'coordinates': event['geometry'][0]['coordinates']})
        if user_lat is None or user_lon is None: return jsonify(all_events)
        nearby_events = []
        max_distance_km = 500
        for event in all_events:
            event_lon, event_lat = event['coordinates']
            distance = haversine(user_lon, user_lat, event_lon, event_lat)
            if distance <= max_distance_km: nearby_events.append(event)
        return jsonify(nearby_events)
    except Exception as e:
        app.logger.error(f"Error in /get_events: {e}")
        return server_error(e)

# --- NEW ROUTES FOR PROFILE PICTURE ---

@app.route('/upload_picture/<username>', methods=['POST'])
def upload_picture(username):
    if 'profile_pic' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    
    file = request.files['profile_pic']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        # Secure the filename and create a new unique name
        original_filename = secure_filename(file.filename)
        extension = os.path.splitext(original_filename)[1]
        new_filename = f"{username}{extension}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
        
        # Save the file
        file.save(file_path)
        
        # Update the user's progress file with the image URL
        progress_data = read_json_file('user_progress.json', {})
        if username not in progress_data:
            progress_data[username] = {}
        
        image_url = f"/uploads/{new_filename}"
        progress_data[username]['profile_picture_url'] = image_url
        write_json_file('user_progress.json', progress_data)
        
        return jsonify({"message": "File uploaded successfully", "url": image_url}), 200

@app.route('/uploads/<filename>')
def serve_uploaded_file(filename):
    """Serves a file from the uploads directory."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run()