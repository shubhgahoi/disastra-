from flask import Flask, request, jsonify
import json
import pyttsx3
app = Flask(__name__)



# Error handlers for structured JSON error responses
@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": "Bad Request", "message": str(e)}), 400

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not Found", "message": str(e)}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred."}), 500

# emergency messages~
def load_messages(disaster=None):
    with open('emergency_messages.json', 'r') as f:
        messages = json.load(f)
    if disaster:
        messages = [m for m in messages if m['disaster'].lower() == disaster.lower()]
    return messages

# quiz questions~
def load_quiz(level=None):
    with open('quiz_questions.json', 'r') as f:
        questions = json.load(f)
    if level:
        questions = [q for q in questions if q['level'].lower() == level.lower()]
    return questions


@app.route('/')
def home():
    return "Disaster Preparedness Backend Running!"

@app.route('/emergency_messages', methods=['GET'] )
def get_emergency_messages():
    disaster = request.args.get('disaster')
    messages = load_messages(disaster)
    return jsonify(messages)

#  getting quiz questions~
@app.route('/quiz_questions', methods=['GET'])
def get_quiz_questions():
    level = request.args.get('level')
    questions = load_quiz(level)
    return jsonify(questions)

# submitting quiz answers and calculating score~
@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    data = request.get_json()
    answers = data.get('answers')  # List of {'question_id': .., 'selected_option': ..}
    user_id = data.get('user_id')
    with open('quiz_questions.json', 'r') as f:
        questions = json.load(f)
    score = 0
    for ans in answers:
        question_id = ans['question_id']
        selected_option = ans['selected_option']
        correct_answer = next((q['Answer'] for q in questions if q['id'] == question_id), None)
        if selected_option == correct_answer:
            score += 1
    feedback = "Great job!" if score > (len(answers)/2) else "Keep practicing!"
    # TODO: Save user progress here
    return jsonify({"status": "success", "score": score, "feedback": feedback})

# getting user progress~
@app.route('/progress', methods=['GET'])
def get_progress():
    user_id = request.args.get('user_id')
    progress_data = {"quizzes_completed": 3, "average_score": 7.5}  # Replace with real logic
    return jsonify({"user_id": user_id, "progress": progress_data})

@app.route('/tts', methods=['POST'])
def text_to_speech():
    data = request.get_json()
    text = data.get('text')
    global engine
    if not text or engine is None:
        engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()
    return jsonify({"status": "success", "message": "Text converted to speech"})



# --- New: Voice Recognition placeholder ---
@app.route('/voice_recognition', methods=['POST'])
def voice_recognition():
    # Placeholder, real integration needed with audio processing
    return jsonify({"transcribed_text": "This is a placeholder for speech-to-text result."})




if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)