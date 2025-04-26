import random
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import sys
import statistics
from datetime import datetime, timedelta, date # Added date
import pytz
import sqlite3
from flask import Flask, request, jsonify, session, render_template, url_for, flash, redirect, send_from_directory
import os
import traceback
from werkzeug.utils import secure_filename

# --- Basic Flask App Setup ---
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
DATABASE = 'mood_data.db'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', b'_5#y2L"F4Q8z\n\xec]/')

# --- Database Setup ---
def get_db():
    try:
        db = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        return db
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        return None

def init_db():
    db = get_db()
    if db:
        try:
            with app.app_context():
                 db.execute('''
                     CREATE TABLE IF NOT EXISTS mood_logs (
                         id INTEGER PRIMARY KEY AUTOINCREMENT,
                         timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                         mood TEXT NOT NULL,
                         score REAL NOT NULL
                     );
                 ''')
                 db.commit()
                 print("Database initialized and mood_logs table ensured.")
        except sqlite3.Error as e:
            print(f"Error initializing database table: {e}")
        finally:
            db.close()
    else:
        print("Failed to get DB connection for initialization.")

# --- Helper Function for File Uploads ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- NLTK Setup ---
analyzer = None
punkt_available = False
# ...(Existing setup_nltk_data function - unchanged)...
def setup_nltk_data():
    """Initializes necessary NLTK resources. Run once at startup."""
    global analyzer, punkt_available
    print("Setting up NLTK data...")
    try:
        try:
            analyzer = SentimentIntensityAnalyzer() #
            print("NLTK 'vader_lexicon' loaded successfully.") #
        except LookupError:
            print("\n--- NLTK SETUP ERROR ---") #
            print("Error: NLTK 'vader_lexicon' not found.") #
            print("Please download it by running: import nltk; nltk.download('vader_lexicon')") #
            print("---------------------------\n") #
            return False
        try:
            nltk.word_tokenize("Test sentence for punkt.") #
            print("NLTK 'punkt' tokenizer available.") #
            punkt_available = True #
        except LookupError:
            print("\n--- NLTK SETUP WARNING ---") #
            print("Warning: NLTK 'punkt' tokenizer not found. Falling back to basic split.") #
            print("Download with: import nltk; nltk.download('punkt')") #
            print("---------------------------\n") #
            punkt_available = False #
        except Exception as e:
            print(f"\n--- NLTK SETUP WARNING ---") #
            print(f"Warning: Error testing 'punkt': {e}. Falling back to basic split.") #
            print("---------------------------\n") #
            punkt_available = False #
        print("NLTK setup complete.") #
        return True
    except Exception as e:
        print(f"\n--- UNEXPECTED NLTK SETUP FAILED ---") #
        print(f"An unexpected error occurred: {e}") #
        print("------------------------------------\n") #
        return False

# --- Mood Categories, Constants, Questions, Keywords ---
# ...(Existing constants, question_banks, keywords - unchanged)...
HAPPY = "Happy" #
SAD = "Sad" #
ANGRY = "Angry" #
STRESSED = "Stressed" #
CALM = "Calm" #
INITIAL = "Initial" #

question_banks = { #
    INITIAL: [ #
        "Hello! How was your day overall?", "Hi there! Tell me a bit about what you did today?", #
        "Hey! What kind of day did you have?", "Good day! What's been happening?", #
        "How did things go for you today?", "What's been the main focus of your day so far?", #
        "Anything interesting happen today?", #
    ],
    HAPPY: [ #
        "That's wonderful to hear! What was the absolute best moment?", "Fantastic! What put the biggest smile on your face?", #
        "Great! Can you share more about what made it so good?", "Awesome! What are you feeling most grateful for from today?", #
        "Love that positivity! What energy are you carrying into tomorrow?", "Excellent! Did anything unexpected but pleasant happen?", #
        "Sounds like a success! What accomplishment are you most proud of today?", "So glad to hear it! Who did you share these good vibes with?", #
    ],
    SAD: [ #
        "I'm really sorry it was a tough day. Is there anything you'd like to share about it?", "That sounds difficult. What weighed most heavily on you?", #
        "Hearing that makes me sad for you. Was there a particular moment that was hardest?", "I'm here to listen. What's been on your mind?", #
        "It's okay to have days like this. Is there anything, even small, that brought a tiny bit of comfort?", "Take your time. What do you feel you need right now?", #
        "That sounds draining. What part of the day felt the longest?", "Sending virtual support. Remember to be kind to yourself. What's one small act of self-care you could do?", #
    ],
    ANGRY: [ #
        "It sounds like something really frustrating happened. What got you feeling angry?", "Okay, take a deep breath. What specifically triggered that anger?", #
        "That sounds infuriating. Can you describe the situation?", "Feeling angry is valid. What happened to make you feel this way?", #
        "It's tough dealing with anger. What was the core issue?", "Did something feel unfair or unjust today?", #
        "What was the situation that made you feel provoked?", "Sometimes venting helps. What's the main thing you wish had gone differently?", #
    ],
    STRESSED: [ #
        "It sounds like you had a lot on your plate today. What felt the most overwhelming?", "Stress can be exhausting. What was the biggest source of pressure?", #
        "Okay, let's unpack that. What tasks or situations were most demanding?", "Feeling stressed is tough. What's taking up most of your mental energy?", #
        "It sounds like you were juggling a lot. Did you feel like you had enough time or resources?", "What felt like the biggest challenge you had to tackle today?", #
        "Are there any specific deadlines or expectations causing stress?", "What's one thing that might help you feel a little less stressed right now?", #
    ],
    CALM: [ #
        "That sounds like a nice, steady day. What contributed to that sense of calm?", "Good to hear things were smooth. What was the most peaceful part of your day?", #
        "A calm day can be refreshing. Did you have any moments of quiet reflection?", "Okay, sounds like things were manageable. What did you enjoy doing at your own pace?", #
        "What helped you maintain that sense of balance today?", "Were there any particular activities that felt relaxing?", #
        "It's good to have those days. What are you looking forward to this evening?", "What part of the day felt the most 'neutral' or 'easy'?", #
        "How's your energy level feeling right now?", "Anything nice planned for the rest of the day/evening?", #
    ]
}
time_specific_questions = { #
    "morning": [ #
        "Good morning! How did you sleep last night?", "Morning! What did you have for breakfast?", #
        "What are your main plans or hopes for the day ahead?", "Starting the day off - how are you feeling right now?", #
        "Get a good rest?", #
    ],
    "midday": [ #
        "How's your day progressing so far?", "Taking a break? How is your energy level holding up?", #
        "What did you have for lunch?", "Anything interesting happen this morning?", #
    ],
    "evening": [ #
        "Good evening! How did your day turn out?", "Winding down? What was the highlight of your day?", #
        "How was your dinner?", "Reflecting on the day, what stands out?", #
        "Planning to relax this evening?", #
    ],
}
HAPPY_KEYWORDS = {"happy", "joy", "great", "awesome", "wonderful", "good", "excited", "thrilled", "fantastic", "yay", "love", "liked", "enjoy", "fun", "positive", "blessed", "cheerful", "amazing", "perfect", "glad", "pleased", "delighted", "elated", "celebrate", "success"} #
SAD_KEYWORDS = {"sad", "unhappy", "down", "miserable", "depressed", "tear", "cry", "gloomy", "awful", "terrible", "hurt", "lonely", "upset", "discouraged", "mourning", "bad", "rough", "low", "blue", "grief", "sorrow", "pain", "difficult"} #
ANGRY_KEYWORDS = {"angry", "mad", "furious", "pissed", "irritated", "annoyed", "frustrated", "enraged", "livid", "rage", "hate", "resentful", "bitter", "aggravated", "fuming", "irate", "outraged", "unfair", "unjust"} #
STRESSED_KEYWORDS = {"stressed", "overwhelmed", "anxious", "worried", "pressure", "deadline", "busy", "frantic", "tension", "difficult", "hard", "struggle", "tired", "exhausted", "demanding", "hectic", "swamped", "buried", "tight", "nervous", "panicked"} #
CALM_KEYWORDS = {"calm", "peaceful", "relaxed", "chill", "easy", "smooth", "quiet", "tranquil", "restful", "breeze", "steady", "balanced", "mellow", "content", "okay", "fine", "alright", "neutral", "manageable", "serene", "composed"} #
KEYWORD_MAX_INFLUENCE = 0.2 #


# --- Quotes ---
QUOTES = {
    "general": [
        "\"The best way to predict the future is to create it.\" - Peter Drucker",
        "\"Believe you can and you're halfway there.\" - Theodore Roosevelt",
        "\"Your limitation—it's only your imagination.\" - Unknown",
        "\"Push yourself, because no one else is going to do it for you.\" - Unknown",
        "\"Great things never come from comfort zones.\" - Unknown",
        "\"Dream it. Wish it. Do it.\" - Unknown",
        "\"Success doesn’t just find you. You have to go out and get it.\" - Unknown",
        "\"The harder you work for something, the greater you'll feel when you achieve it.\" - Unknown",
        "\"Don’t stop when you’re tired. Stop when you’re done.\" - Unknown",
        "\"Wake up with determination. Go to bed with satisfaction.\" - Unknown"
    ],
    "positive": [ # For HAPPY, CALM (slightly positive)
        "\"Keep your face always toward the sunshine, and shadows will fall behind you.\" - Walt Whitman",
        "\"Let your unique awesomeness and positive energy inspire confidence in others.\" - Unknown",
        "\"The happiness of your life depends upon the quality of your thoughts.\" - Marcus Aurelius",
        "\"Wherever you go, no matter what the weather, always bring your own sunshine.\" - Anthony J. D'Angelo",
        "\"Positivity always wins... Always.\" - Gary Vaynerchuk",
        "\"Embrace the glorious mess that you are.\" - Elizabeth Gilbert",
        "\"Today is a good day for a good day.\" - Unknown"
    ],
    "uplifting": [ # For SAD, ANGRY, STRESSED (negative moods)
        "\"It's okay not to be okay. Just don't give up.\" - Unknown",
        "\"Hard times don’t create heroes. It is during the hard times when the 'hero' within us is revealed.\" - Bob Riley",
        "\"This too shall pass.\" - Persian Proverb",
        "\"You are stronger than you think.\" - Unknown",
        "\"Every storm runs out of rain.\" - Maya Angelou",
        "\"Even the darkest night will end and the sun will rise.\" - Victor Hugo",
        "\"Sometimes the bad things that happen in our lives put us directly on the path to the best things that will ever happen to us.\" - Unknown",
        "\"Breathe. It's just a bad day, not a bad life.\" - Unknown"
    ],
     "calm": [ # Specifically for CALM mood
        "\"Within you, there is a stillness and a sanctuary to which you can retreat at any time and be yourself.\" - Hermann Hesse",
        "\"Peace comes from within. Do not seek it without.\" - Buddha",
        "\"Calmness is the cradle of power.\" - Josiah Gilbert Holland",
        "\"Simply breathing can be a meditation.\" - Unknown",
        "\"Find peace in the present moment.\" - Unknown"
    ]
}

# --- Mood Analysis, Time of Day, Get Next Question Functions ---
# ...(Existing get_mood_and_score, get_time_of_day_ist, get_next_question functions - unchanged)...
def get_mood_and_score(text): #
    """Analyzes text using VADER and keywords to determine mood and score.""" #
    global punkt_available, analyzer #
    if analyzer is None: #
        print("ERROR: Sentiment analyzer not initialized!") #
        return CALM, 0.0 # Fallback
    vs = analyzer.polarity_scores(text) #
    compound_score = vs['compound'] #
    neg_score = vs['neg'] #
    pos_score = vs['pos'] #

    tokens = [] #
    text_lower = text.lower() #
    if punkt_available: #
        try: tokens = nltk.word_tokenize(text_lower) #
        except Exception as e: tokens = text_lower.split() #
    else: tokens = text_lower.split() #

    happy_count = sum(1 for w in tokens if w in HAPPY_KEYWORDS) #
    sad_count = sum(1 for w in tokens if w in SAD_KEYWORDS) #
    angry_count = sum(1 for w in tokens if w in ANGRY_KEYWORDS) #
    stressed_count = sum(1 for w in tokens if w in STRESSED_KEYWORDS) #
    calm_count = sum(1 for w in tokens if w in CALM_KEYWORDS) #
    total_keywords = happy_count + sad_count + angry_count + stressed_count + calm_count #

    keyword_influence = 0.0 #
    if total_keywords > 0: #
        net_keyword_effect = (happy_count + calm_count) - (sad_count + angry_count + stressed_count) #
        influence_ratio = net_keyword_effect / total_keywords #
        keyword_influence = influence_ratio * KEYWORD_MAX_INFLUENCE #

    combined_score = max(-1.0, min(1.0, compound_score + keyword_influence)) #

    mood = CALM #
    POSITIVE_THRESHOLD = 0.35; NEGATIVE_THRESHOLD = -0.35 #
    STRONG_NEG_VADER = 0.20; STRONG_POS_VADER = 0.20 #
    keyword_counts = {HAPPY: happy_count, SAD: sad_count, ANGRY: angry_count, STRESSED: stressed_count, CALM: calm_count} #
    dominant_keyword_mood = max(keyword_counts, key=keyword_counts.get) if total_keywords > 0 else None #
    dominant_keyword_count = keyword_counts.get(dominant_keyword_mood, 0) #

    if combined_score >= POSITIVE_THRESHOLD and pos_score >= STRONG_POS_VADER: #
        mood = HAPPY #
        if dominant_keyword_mood == CALM and dominant_keyword_count > happy_count: mood = CALM #
    elif combined_score <= NEGATIVE_THRESHOLD and neg_score >= STRONG_NEG_VADER * 0.8: #
        if dominant_keyword_mood == ANGRY and dominant_keyword_count > 0: mood = ANGRY #
        elif dominant_keyword_mood == STRESSED and dominant_keyword_count > 0: mood = STRESSED #
        elif dominant_keyword_mood == SAD and dominant_keyword_count > 0: mood = SAD #
        else: mood = SAD #
    else: # Neutral/Mixed Range #
        if dominant_keyword_mood: #
            is_dominant_significant = dominant_keyword_count > 0 and dominant_keyword_count >= max(total_keywords * 0.4, 1) #
            if is_dominant_significant: #
                if dominant_keyword_mood == HAPPY and pos_score > neg_score + 0.1: mood = HAPPY #
                elif dominant_keyword_mood == ANGRY and neg_score > pos_score + 0.1: mood = ANGRY #
                elif dominant_keyword_mood == STRESSED and neg_score > pos_score: mood = STRESSED #
                elif dominant_keyword_mood == SAD and neg_score > pos_score: mood = SAD #
                elif dominant_keyword_mood == CALM: mood = CALM #
                else: mood = CALM #
            else: mood = CALM #
        else: mood = CALM #
    if combined_score > 0.6 and mood != HAPPY: mood = HAPPY #
    if combined_score < -0.6 and mood not in [SAD, ANGRY, STRESSED]: mood = SAD #

    return mood, combined_score #

def get_time_of_day_ist(): #
    """Determines the current time of day category ('morning', 'midday', 'evening') in IST.""" #
    try:
        ist = pytz.timezone('Asia/Kolkata') #
        hour = datetime.now(ist).hour #
        if 5 <= hour < 12: return "morning" #
        elif 12 <= hour < 17: return "midday" #
        else: return "evening" #
    except Exception as e:
        print(f"Warning: Could not get IST time ({e}). Falling back to system local time.") #
        hour = datetime.now().hour #
        if 5 <= hour < 12: return "morning" #
        elif 12 <= hour < 17: return "midday" #
        else: return "evening" #

def get_next_question(mood_context, current_time_category): #
    """Selects the next question based on mood and time, managing asked questions in session.""" #
    if 'asked_mood_questions' not in session: session['asked_mood_questions'] = {mood: [] for mood in question_banks.keys()} #
    if 'asked_time_questions' not in session: session['asked_time_questions'] = [] #
    if mood_context not in session['asked_mood_questions']: session['asked_mood_questions'][mood_context] = [] #

    asked_mood_for_context = session['asked_mood_questions'].get(mood_context, []) #
    asked_time_tuples = session['asked_time_questions'] #

    possible_questions = [] #
    is_time_specific_candidate = False #
    time_bank_key_candidate = None #

    current_mood_bank = question_banks.get(mood_context, []) #
    unasked_mood_questions = [q for q in current_mood_bank if q not in asked_mood_for_context] #
    possible_questions.extend(unasked_mood_questions) #

    if mood_context == INITIAL: #
        time_bank = time_specific_questions.get(current_time_category, []) #
        unasked_time_questions = [q for q in time_bank if (current_time_category, q) not in asked_time_tuples] #
        possible_questions.extend(unasked_time_questions) #
        random.shuffle(possible_questions) #

    if not possible_questions: #
        print(f"DEBUG (get_next_question): No unasked questions for '{mood_context}'. Resetting.") #
        session['asked_mood_questions'][mood_context] = [] #
        possible_questions.extend(current_mood_bank) #

        if mood_context == INITIAL and not possible_questions: #
             time_bank = time_specific_questions.get(current_time_category, []) #
             session['asked_time_questions'] = [t for t in asked_time_tuples if t[0] != current_time_category] #
             unasked_time_questions = [q for q in time_bank if (current_time_category, q) not in session['asked_time_questions']] #
             possible_questions.extend(unasked_time_questions) #
             random.shuffle(possible_questions) #

        if not possible_questions and mood_context != CALM: #
            print(f"DEBUG (get_next_question): Falling back to CALM questions.") #
            mood_context = CALM #
            calm_bank = question_banks.get(CALM, []) #
            if CALM not in session['asked_mood_questions']: session['asked_mood_questions'][CALM] = [] #
            asked_calm = session['asked_mood_questions'].get(CALM, []) #
            unasked_calm = [q for q in calm_bank if q not in asked_calm] #
            if not unasked_calm: #
                 session['asked_mood_questions'][CALM] = [] #
                 possible_questions.extend(calm_bank) #
            else: possible_questions.extend(unasked_calm) #

        if not possible_questions: #
            print("ERROR (get_next_question): No questions available.") #
            return "Is there anything else on your mind?", False, None #

    question_to_ask = random.choice(possible_questions) #

    time_bank_for_category = time_specific_questions.get(current_time_category, []) #
    if question_to_ask in time_bank_for_category: #
         if (current_time_category, question_to_ask) not in asked_time_tuples: #
              is_time_specific_candidate = True #
              time_bank_key_candidate = current_time_category #

    return question_to_ask, is_time_specific_candidate, time_bank_key_candidate #


# --- Flask Routes ---
# ...(Existing routes: index, chatbot_page, profile, api/profile GET/POST, api/profile/picture, uploaded_file - unchanged)...
@app.route('/')
def index():
    """Serves the main landing page (index.html)."""
    session.permanent = True
    # Initialize session keys if they don't exist
    session.setdefault('initialized', True)
    session.setdefault('current_mood_context', INITIAL)
    session.setdefault('asked_mood_questions', {mood: [] for mood in question_banks.keys()})
    session.setdefault('asked_time_questions', [])
    session.setdefault('conversation_scores', []) # Still keep for immediate avg? Optional.
    # Initialize profile data in session if not present
    session.setdefault('profile', {
        'name': 'User Name', # Default values
        'age': None,
        'weight': None,
        'picture_filename': None # Store only filename
    })
    session.modified = True # Ensure changes are saved
    # Pass theme variable to template
    return render_template('index.html', theme='dark') # Assuming dark theme is default for now

@app.route('/chatbot_page')
def chatbot_page():
    """Serves the chatbot page content (chatbot.html) for the iframe."""
    # Pass theme variable to template
    return render_template('chatbot.html', theme='dark')

# --- Profile Page Route ---
@app.route('/profile')
def profile():
    """Serves the profile page."""
    # Initialize profile in session if it doesn't exist (e.g., direct navigation)
    session.setdefault('profile', {
        'name': 'User Name', 'age': None, 'weight': None, 'picture_filename': None
    })
    # Pass theme variable to template
    return render_template('profile.html', theme='dark')


# --- Profile API Routes ---

@app.route('/api/profile', methods=['GET'])
def get_profile():
    """API endpoint to get current profile data from session."""
    profile_data = session.get('profile', { # Provide default if somehow missing
        'name': 'N/A', 'age': None, 'weight': None, 'picture_filename': None
    })
    return jsonify(profile_data)

@app.route('/api/profile', methods=['POST'])
def update_profile():
    """API endpoint to update profile text data in session."""
    data = request.json
    if not data:
        return jsonify({"detail": "Invalid request format"}), 400

    current_profile = session.get('profile', {}) # Get current or empty dict

    # Update only provided fields
    if 'name' in data:
        current_profile['name'] = data['name']
    if 'age' in data:
        try:
             # Handle potential empty string or null from frontend
             current_profile['age'] = int(data['age']) if data.get('age') else None
        except (ValueError, TypeError):
             return jsonify({"detail": "Invalid age format"}), 400
    if 'weight' in data:
         try:
              # Handle potential empty string or null from frontend
              current_profile['weight'] = float(data['weight']) if data.get('weight') else None
         except (ValueError, TypeError):
              return jsonify({"detail": "Invalid weight format"}), 400

    session['profile'] = current_profile # Save back to session
    session.modified = True
    print(f"DEBUG: Profile updated in session: {session['profile']}")
    return jsonify({"message": "Profile updated successfully", "profile": current_profile})

@app.route('/api/profile/picture', methods=['POST'])
def update_profile_picture():
    """API endpoint to handle profile picture upload."""
    if 'profile_picture' not in request.files:
        return jsonify({"detail": "No picture file part"}), 400
    file = request.files['profile_picture']
    if file.filename == '':
        return jsonify({"detail": "No selected picture file"}), 400

    if file and allowed_file(file.filename):
        # Generate a more unique filename to avoid conflicts
        # Using timestamp + original filename is safer
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_filename = f"{timestamp}_{secure_filename(file.filename)}"

        # Construct full path
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

        try:
            # Optional: Delete old picture if it exists
            old_filename = session.get('profile', {}).get('picture_filename')
            if old_filename:
                 old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], old_filename)
                 if os.path.exists(old_file_path):
                    try:
                        os.remove(old_file_path)
                        print(f"DEBUG: Deleted old profile picture: {old_filename}")
                    except OSError as e:
                        print(f"Error deleting old file {old_filename}: {e}")


            file.save(file_path)
            print(f"DEBUG: Profile picture saved to: {file_path}")

            # Update filename in session
            current_profile = session.get('profile', {})
            current_profile['picture_filename'] = unique_filename
            session['profile'] = current_profile
            session.modified = True
            print(f"DEBUG: Profile picture filename updated in session: {unique_filename}")

            return jsonify({"message": "Picture uploaded successfully", "filename": unique_filename})

        except Exception as e:
            print(f"ERROR saving profile picture: {e}")
            traceback.print_exc()
            return jsonify({"detail": f"Could not save picture: {e}"}), 500
    else:
        return jsonify({"detail": "File type not allowed"}), 400

# Serve uploaded files (needed for the <img> tag src)
@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
     # Security: Ensure filename is safe and only serves from the upload folder
     safe_path = os.path.abspath(app.config['UPLOAD_FOLDER'])
     # Ensure the filename doesn't contain path elements like '..'
     filename = secure_filename(filename)
     requested_path = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], filename))

     if not requested_path.startswith(safe_path):
          # Directory traversal attempt
          return "Not Found", 404

     return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# --- Chatbot API Routes ---
# ...(Existing /chat and /reset routes - /chat modified for DB logging, /reset unchanged)...
@app.route('/chat', methods=['POST'])
def chat_endpoint():
    """Handles chat messages, logs mood/score to DB, and returns bot reply."""
    if not session.get('initialized'):
        print("ERROR: /chat called but session not initialized. Re-initializing.")
        session.clear(); session['initialized'] = True; session['current_mood_context'] = INITIAL
        session['asked_mood_questions'] = {mood: [] for mood in question_banks.keys()}
        session['asked_time_questions'] = []; session['conversation_scores'] = []
        session.setdefault('profile', { 'name': 'User Name', 'age': None, 'weight': None, 'picture_filename': None })
        session.modified = True

    data = request.json
    if data is None: return jsonify({"error": "Invalid request format"}), 400
    user_message = data.get('message')

    current_mood_context = session.get('current_mood_context', INITIAL)
    # Ensure these session variables exist and have correct types
    asked_mood_questions = session.setdefault('asked_mood_questions', {mood: [] for mood in question_banks.keys()})
    asked_time_questions = session.setdefault('asked_time_questions', [])
    conversation_scores = session.setdefault('conversation_scores', []) # Still keep for immediate avg? Optional.

    if not isinstance(asked_mood_questions, dict): asked_mood_questions = {mood: [] for mood in question_banks.keys()}
    for mood in question_banks.keys():
        asked_mood_questions.setdefault(mood, [])
    if not isinstance(asked_time_questions, list): asked_time_questions = []
    if not isinstance(conversation_scores, list): conversation_scores = []

    bot_reply = "Something went wrong."
    detected_mood_for_response = current_mood_context
    score_for_response = 0.0 # Initialize score
    next_mood_context_for_session = current_mood_context

    try:
        if user_message is not None: # Process user message
            print(f"\n--- Processing User Message ---")
            print(f"DEBUG: Received: '{user_message[:50]}...' | Current Context: {current_mood_context}")

            detected_mood, score = get_mood_and_score(user_message)
            detected_mood_for_response = detected_mood
            score_for_response = score # Capture the score

            print(f"SCORE_ACCESS: Score for this message: {score:.4f}")
            conversation_scores.append(score) # Optional: keep session scores for other uses

            # --- Log to Database ---
            db = get_db()
            if db:
                try:
                    # Use UTC for database storage for consistency
                    timestamp_utc = datetime.utcnow()
                    # Convert to IST for logging message if needed, but store UTC
                    # timestamp_ist = timestamp_utc.replace(tzinfo=pytz.utc).astimezone(pytz.timezone('Asia/Kolkata'))

                    db.execute(
                        'INSERT INTO mood_logs (timestamp, mood, score) VALUES (?, ?, ?)',
                        (timestamp_utc, detected_mood, score) # Store UTC timestamp
                    )
                    db.commit()
                    print(f"DB_LOG: Logged (UTC): {timestamp_utc.strftime('%Y-%m-%d %H:%M:%S')}, {detected_mood}, {score:.4f}")
                except sqlite3.Error as e:
                    print(f"ERROR: Failed to log mood to database: {e}")
                    # Should we return an error to the user? Maybe not for logging failure.
                finally:
                    db.close()
            else:
                print("ERROR: Could not get DB connection for logging.")
            # --- End Log to Database ---

            print(f"DEBUG: Mood detected: {detected_mood}")
            next_mood_context_for_session = detected_mood
            if current_mood_context == SAD and detected_mood == HAPPY: next_mood_context_for_session = CALM
            elif current_mood_context in [ANGRY, STRESSED] and detected_mood == HAPPY: next_mood_context_for_session = CALM

            current_time = get_time_of_day_ist()
            question, is_time, time_key = get_next_question(next_mood_context_for_session, current_time)
            bot_reply = question
            print(f"DEBUG: Selected Reply: '{bot_reply[:50]}...'")

            # Update asked questions in session
            if is_time and time_key:
                 if (time_key, question) not in asked_time_questions: asked_time_questions.append((time_key, question))
            else:
                 context_to_mark = next_mood_context_for_session
                 asked_mood_questions.setdefault(context_to_mark, []) # Ensure key exists
                 if question not in asked_mood_questions[context_to_mark]: asked_mood_questions[context_to_mark].append(question)
            print("--- End Processing User Message ---\n")

        else: # Handle Initial Request (when message is null)
            print("\n--- Processing Initial Request ---")
            current_time = get_time_of_day_ist()
            question, is_time, time_key = get_next_question(INITIAL, current_time)
            bot_reply = question
            detected_mood_for_response = INITIAL
            score_for_response = 0.0 # No score for initial message
            next_mood_context_for_session = INITIAL
            print(f"DEBUG: Selected Initial Reply: '{bot_reply[:50]}...'")
            # Update asked questions in session
            if is_time and time_key:
                 if (time_key, question) not in asked_time_questions: asked_time_questions.append((time_key, question))
            else:
                 asked_mood_questions.setdefault(INITIAL, []) # Ensure key exists
                 if question not in asked_mood_questions[INITIAL]: asked_mood_questions[INITIAL].append(question)
            print("--- End Initial Request ---\n")

        # Update session state
        session['current_mood_context'] = next_mood_context_for_session
        session['asked_mood_questions'] = asked_mood_questions
        session['asked_time_questions'] = asked_time_questions
        session['conversation_scores'] = conversation_scores
        session.modified = True

        # Return mood and score along with reply (frontend doesn't use this yet)
        return jsonify({
            "bot_reply": bot_reply,
            "detected_mood": detected_mood_for_response,
            "score": score_for_response
        })

    except Exception as e:
        print("\n!!!!!!!!!!!!!! ERROR in /chat !!!!!!!!!!!!!!")
        print(f"Error Type: {type(e).__name__}: {e}")
        traceback.print_exc()
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        session.modified = True # Still try to save session if possible
        return jsonify({"error": f"Internal error: {type(e).__name__}.", "bot_reply": "Oops! My circuits are tangled."}), 500


@app.route('/reset', methods=['POST'])
def reset_session():
    """Clears the session and provides a new initial question."""
    print("DEBUG (Backend /reset): Resetting session.")
    profile_data = session.get('profile', None) # Preserve profile
    session.clear() # Clears everything including profile
    # Re-initialize essential session keys after clearing
    session['initialized'] = True; session['current_mood_context'] = INITIAL
    session['asked_mood_questions'] = {mood: [] for mood in question_banks.keys()}
    session['asked_time_questions'] = []; session['conversation_scores'] = []
    # Restore or re-initialize profile data
    if profile_data:
        session['profile'] = profile_data
    else:
         session.setdefault('profile', { 'name': 'User Name', 'age': None, 'weight': None, 'picture_filename': None })

    initial_question = "Okay, let's start over. How are you feeling now?"
    try:
        current_time = get_time_of_day_ist()
        question, is_time, time_key = get_next_question(INITIAL, current_time)
        initial_question = question
        # Update asked questions in session
        if is_time and time_key:
             if (time_key, question) not in session['asked_time_questions']: session['asked_time_questions'].append((time_key, question))
        else:
             session['asked_mood_questions'].setdefault(INITIAL, [])
             if question not in session['asked_mood_questions'][INITIAL]: session['asked_mood_questions'][INITIAL].append(question)
        session.modified = True
        return jsonify({"status": "success", "initial_message": initial_question})
    except Exception as e:
         print(f"ERROR during session reset's get_next_question: {e}")
         traceback.print_exc()
         session.modified = True
         return jsonify({"status": "error", "message": "Failed to get new question after reset."}), 500


# --- Mood History API (with Dummy Data) ---
@app.route('/api/mood_history', methods=['GET'])
def get_mood_history():
    """API endpoint to fetch mood data for the chart, includes dummy data if needed."""
    days = request.args.get('days', 7, type=int)
    # Use UTC for date calculations to match database storage
    end_date_utc = datetime.utcnow()
    start_date_utc = end_date_utc - timedelta(days=days -1) # Include today

    db = get_db()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500

    logs = []
    try:
        cursor = db.cursor()
        cursor.execute(
            "SELECT timestamp, score FROM mood_logs WHERE date(timestamp) >= date(?) AND date(timestamp) <= date(?) ORDER BY timestamp ASC",
             (start_date_utc.strftime('%Y-%m-%d'), end_date_utc.strftime('%Y-%m-%d')) # Compare dates only
        )
        logs = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Error fetching mood history: {e}")
        # Don't return error yet, try generating dummy data
    finally:
        if db:
            db.close()

    # --- Process data: Calculate daily average ---
    daily_scores = {} # Key: 'YYYY-MM-DD', Value: list of scores
    if logs:
        for log in logs:
            ts_str = log['timestamp']
            try:
                # Timestamps stored as UTC TEXT 'YYYY-MM-DD HH:MM:SS.ffffff'
                ts_utc = datetime.strptime(ts_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
                day_str = ts_utc.strftime('%Y-%m-%d')
                if day_str not in daily_scores:
                    daily_scores[day_str] = []
                daily_scores[day_str].append(log['score'])
            except (ValueError, TypeError) as parse_err:
                 print(f"Warning: Could not parse timestamp '{ts_str}'. Skipping log. Error: {parse_err}")
                 continue

    chart_labels = []
    chart_values = []
    has_real_data = bool(logs) # Flag to know if we used real data

    # Generate labels and values for the specified range
    current_date_utc = start_date_utc
    while current_date_utc.date() <= end_date_utc.date():
        day_str = current_date_utc.strftime('%Y-%m-%d')
        chart_labels.append(day_str)
        if day_str in daily_scores:
            avg_score = statistics.mean(daily_scores[day_str])
            chart_values.append(round(avg_score, 2))
        else:
            # If no real data exists at all for the period, add dummy data
            if not has_real_data:
                 # Generate somewhat random dummy score between -0.8 and 0.8
                 dummy_score = round(random.uniform(-0.8, 0.8), 2)
                 chart_values.append(dummy_score)
            else:
                # If there's some real data, but not for this day, use null
                chart_values.append(None)
        current_date_utc += timedelta(days=1)

    # Return data formatted for Chart.js
    return jsonify({
        "labels": chart_labels,
        "scores": chart_values,
        "has_real_data": has_real_data # Indicate if dummy data was used
    })


# --- Daily Quote API ---
@app.route('/api/daily_quote', methods=['GET'])
def get_daily_quote():
    """Provides a quote based on the latest mood entry for today."""
    today_start_utc = datetime.combine(datetime.utcnow().date(), datetime.min.time())
    today_end_utc = datetime.combine(datetime.utcnow().date(), datetime.max.time())

    db = get_db()
    if not db:
        # Fallback to general quote if DB fails
        return jsonify({"quote": random.choice(QUOTES["general"])})

    latest_mood = None
    try:
        cursor = db.cursor()
        # Get the mood from the most recent entry today
        cursor.execute(
            """
            SELECT mood FROM mood_logs
            WHERE timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (today_start_utc, today_end_utc)
        )
        result = cursor.fetchone()
        if result:
            latest_mood = result['mood']
    except sqlite3.Error as e:
        print(f"Error fetching latest mood for quote: {e}")
        # Fallback to general quote on error
    finally:
        if db:
            db.close()

    quote = ""
    if latest_mood == HAPPY:
        quote = random.choice(QUOTES["positive"])
    elif latest_mood == SAD or latest_mood == ANGRY or latest_mood == STRESSED:
        quote = random.choice(QUOTES["uplifting"])
    elif latest_mood == CALM:
         quote = random.choice(QUOTES["calm"])
    else: # No mood found for today or error occurred
        quote = random.choice(QUOTES["general"])

    return jsonify({"quote": quote})


# --- Main Execution ---
if __name__ == '__main__':
    print("Starting Mood Reflect Bot application...")
    init_db() # Initialize the database on startup
    if not setup_nltk_data():
        print("\nExiting: NLTK setup failed.")
        sys.exit(1)
    try: import pytz; print("pytz library found.")
    except ImportError: print("\n--- WARNING: 'pytz' not installed. Using system local time. (pip install pytz)\n")

    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Database file at: {os.path.abspath(DATABASE)}")
    print(f"Upload folder configured at: {os.path.abspath(app.config['UPLOAD_FOLDER'])}")
    print("\nStarting Flask development server...")
    print("Access the app at: http://127.0.0.1:5000/")
    print("Access profile page at: http://127.0.0.1:5000/profile")
    print("Press CTRL+C to stop.")
    # Use threaded=False if using SQLite locally
    app.run(debug=True, port=5000, host='127.0.0.1', threaded=False)

