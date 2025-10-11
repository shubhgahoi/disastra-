from flask import Flask, request, jsonify, send_from_directory
import json
import requests
import math
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# --- CONFIGURATION & BOT LOGIC ---
EONET_API_URL = "https://eonet.gsfc.nasa.gov/api/v3/events"
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
BOT_LOGIC = [
    ("any", ["hello", "hi", "hey"], "Hello! I am the Disastra assistant. How can I help you prepare today? You can ask for 'help'."),
    ("any", ["thank", "bye"], "You're welcome! Stay safe and prepared."),
    ("any", ["quiz"], "You can test your knowledge by taking a preparedness quiz from the main dashboard."),
    ("any", ["help"], "You can ask me about safety for a 'fire', 'earthquake', 'flood', or 'cyclone'. You can also ask about the 'quiz', 'family plan', 'live alerts', or 'emergency kit'."),
    ("all", ["fire", "safety"], "During a fire, your priority is to get out safely. Feel doors for heat before opening and stay low to avoid smoke."),
    ("all", ["earthquake", "safety"], "In an earthquake, Drop, Cover, and Hold On! Get under a sturdy table and protect your head and neck."),
    ("all", ["flood", "safety"], "If a flood warning is issued, move to higher ground immediately. Do not walk or drive through floodwaters."),
    ("all", ["cyclone", "safety"], "During a cyclone, stay indoors and away from windows. Monitor official news sources for updates."),
    ("all", ["family", "plan"], "The Family Plan feature helps you store emergency contacts and meeting places. You can find it on the main dashboard."),
    ("all", ["live", "alerts"], "The Live Alerts section shows recent natural events using data from NASA."),
    ("all", ["emergency", "kit"], "Your emergency kit should contain water, food, a first-aid kit, a flashlight, and batteries. Use the 'Emergency Kit' checklist to track your items."),
]

# --- NEW: ACHIEVEMENT DEFINITIONS ---
ACHIEVEMENTS = {
    "first_steps": {
        "title": "First Steps",
        "description": "Complete your first quiz."
    },
    "kit_master": {
        "title": "Kit Master",
        "description": "Check off all items in your emergency kit."
    },
    "planner": {
        "title": "Planner",
        "description": "Fill out your family emergency plan."
    },
    "streak_starter": {
        "title": "Streak Starter",
        "description": "Achieve a quiz streak of 3 or more."
    }
}

# --- NEW: ACHIEVEMENT CHECKING LOGIC ---
def check_user_achievements(user_progress):
    unlocked = []
    
    # Check for "First Steps"
    if user_progress.get("quizzes_completed", 0) >= 1:
        unlocked.append("first_steps")
        
    # Check for "Kit Master"
    kit_checklist = user_progress.get("kit_checklist", {})
    if kit_checklist and all(kit_checklist.values()):
        # This assumes the kit has items. all() on an empty dict is True.
        unlocked.append("kit_master")
        
    # Check for "Planner"
    emergency_plan = user_progress.get("emergency_plan", {})
    # Simple check: if at least 3 fields are filled, we count it.
    if len([v for v in emergency_plan.values() if v]) >= 3:
        unlocked.append("planner")
        
    # Check for "Streak Starter"
    if user_progress.get("current_streak", 0) >= 3 or user_progress.get("best_streak", 0) >= 3:
        unlocked.append("streak_starter")
        
    return unlocked

# --- HELPER FUNCTIONS & OTHER ROUTES ---
def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2]); dlon = lon2 - lon1; dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2; c = 2 * math.asin(math.sqrt(a)); r = 6371
    return c * r
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
    user_lat = request.args.get('lat', type=float); user_lon = request.args.get('lon', type=float)
    try:
        params = {'status': 'open', 'limit': 50, 'days': 30}
        response = requests.get(EONET_API_URL, params=params, timeout=10)
        response.raise_for_status(); data = response.json(); all_events = []
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
@app.route('/upload_picture/<username>', methods=['POST'])
def upload_picture(username):
    if 'profile_pic' not in request.files: return jsonify({"error": "No file part"}), 400
    file = request.files['profile_pic']
    if file.filename == '': return jsonify({"error": "No selected file"}), 400
    if file:
        original_filename = secure_filename(file.filename); extension = os.path.splitext(original_filename)[1]
        new_filename = f"{username}{extension}"; file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
        file.save(file_path)
        with open('user_progress.json', 'r+') as f:
            progress_data = json.load(f)
            if username not in progress_data: progress_data[username] = {}
            image_url = f"/uploads/{new_filename}"
            progress_data[username]['profile_picture_url'] = image_url
            f.seek(0)
            json.dump(progress_data, f, indent=4)
        return jsonify({"message": "File uploaded", "url": image_url}), 200
@app.route('/uploads/<filename>')
def serve_uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- NEW: ACHIEVEMENTS ENDPOINT ---
@app.route('/achievements/<username>', methods=['GET'])
def get_achievements(username):
    try:
        with open('user_progress.json', 'r') as f:
            progress_data = json.load()
        
        user_progress = progress_data.get(username, {})
        unlocked_ids = check_user_achievements(user_progress)
        
        return jsonify({
            "all_achievements": ACHIEVEMENTS,
            "unlocked_achievements": unlocked_ids
        })
    except FileNotFoundError:
        return jsonify({
            "all_achievements": ACHIEVEMENTS,
            "unlocked_achievements": []
        })
    except Exception as e:
        app.logger.error(f"Error in /achievements: {e}")
        return server_error(e)

@app.route('/chatbot', methods=['POST'])
def handle_chatbot():
    user_message = request.json.get('message', '').lower()
    for strategy, keywords, response in BOT_LOGIC:
        if strategy == 'any':
            if any(kw in user_message for kw in keywords):
                return jsonify({"response": response})
        elif strategy == 'all':
            if all(kw in user_message for kw in keywords):
                return jsonify({"response": response})
    return jsonify({"response": "I'm sorry, I don't have information about that yet. You can ask for 'help' to see what I know."})

if __name__ == '__main__':
    app.run()