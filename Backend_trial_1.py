from flask import Flask, request, jsonify
import json
import requests # Make sure requests is imported

app = Flask(__name__)

# --- NASA EONET API Configuration ---
EONET_API_URL = "https://eonet.gsfc.nasa.gov/api/v3/events"

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

# NEW: Route to get live disaster events from NASA
@app.route('/get_events', methods=['GET'])
def get_live_events():
    try:
        # Request the latest 20 open events from the last 30 days from NASA's API
        params = {'status': 'open', 'limit': 20, 'days': 30}
        response = requests.get(EONET_API_URL, params=params, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        
        data = response.json()
        
        # Simplify the data for our app
        simplified_events = []
        for event in data.get('events', []):
            simplified_events.append({
                'title': event.get('title'),
                'category': event['categories'][0]['title'] if event.get('categories') else 'Unknown',
                'date': event['geometry'][0]['date'] if event.get('geometry') else 'N/A',
                'link': event.get('link')
            })
            
        return jsonify(simplified_events)

    except requests.exceptions.RequestException as e:
        # If the request to NASA fails, return an error
        return jsonify({"error": "Could not fetch data from NASA EONET", "details": str(e)}), 502
    except Exception as e:
        # For any other unexpected errors
        app.logger.error(f"An unexpected error occurred in /get_events: {e}")
        return server_error(e)


if __name__ == '__main__':
    app.run()