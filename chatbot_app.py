import random
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import sys
import statistics 
from datetime import datetime
import pytz 

from flask import Flask, request, jsonify, session, render_template, url_for # Added url_for for clarity, though not strictly needed in .py for basic use
import os 
import traceback


app = Flask(__name__)


app.secret_key = os.environ.get('FLASK_SECRET_KEY', b'_5#y2L"F4Q8z\n\xec]/') 


analyzer = None
punkt_available = False

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


HAPPY = "Happy" #
SAD = "Sad" #
ANGRY = "Angry" #
STRESSED = "Stressed" #
CALM = "Calm" #
INITIAL = "Initial" #


question_banks = { #
    INITIAL: [ #
        "Hello! How was your day overall?", "Hi there! Tell me a bit about what you did today.", #
        "Hey! What kind of day did you have?", "Good day! What's been happening?", #
        "How did things go for you today?", "What's been the main focus of your day so far?", #
        "Anything interesting happen today?", 
    ],
    HAPPY: [ 
        "That's wonderful to hear! What was the absolute best moment?", "Fantastic! What put the biggest smile on your face?", #
        "Great! Can you share more about what made it so good?", "Awesome! What are you feeling most grateful for from today?", #
        "Love that positivity! What energy are you carrying into tomorrow?", "Excellent! Did anything unexpected but pleasant happen?", #
        "Sounds like a success! What accomplishment are you most proud of today?", "So glad to hear it! Who did you share these good vibes with?", #
    ],
    SAD: [ 
        "I'm really sorry it was a tough day. Is there anything you'd like to share about it?", "That sounds difficult. What weighed most heavily on you?", #
        "Hearing that makes me sad for you. Was there a particular moment that was hardest?", "I'm here to listen. What's been on your mind?", #
        "It's okay to have days like this. Is there anything, even small, that brought a tiny bit of comfort?", "Take your time. What do you feel you need right now?", #
        "That sounds draining. What part of the day felt the longest?", "Sending virtual support. Remember to be kind to yourself. What's one small act of self-care you could do?", #
    ],
    ANGRY: [ 
        "It sounds like something really frustrating happened. What got you feeling angry?", "Okay, take a deep breath. What specifically triggered that anger?", #
        "That sounds infuriating. Can you describe the situation?", "Feeling angry is valid. What happened to make you feel this way?", #
        "It's tough dealing with anger. What was the core issue?", "Did something feel unfair or unjust today?", #
        "What was the situation that made you feel provoked?", "Sometimes venting helps. What's the main thing you wish had gone differently?", #
    ],
    STRESSED: [ 
        "It sounds like you had a lot on your plate today. What felt the most overwhelming?", "Stress can be exhausting. What was the biggest source of pressure?", #
        "Okay, let's unpack that. What tasks or situations were most demanding?", "Feeling stressed is tough. What's taking up most of your mental energy?", #
        "It sounds like you were juggling a lot. Did you feel like you had enough time or resources?", "What felt like the biggest challenge you had to tackle today?", #
        "Are there any specific deadlines or expectations causing stress?", "What's one thing that might help you feel a little less stressed right now?", #
    ],
    CALM: [ 
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

    keyword_influence = 0.0 
    if total_keywords > 0: 
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
    else: # 
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



@app.route('/')
def index():
    """Serves the main landing page (index.html)."""
    session.permanent = True #
    if 'initialized' not in session: #
        print("DEBUG (Backend /): New session initializing.") #
        session['current_mood_context'] = INITIAL #
        session['asked_mood_questions'] = {mood: [] for mood in question_banks.keys()} #
        session['asked_time_questions'] = [] #
        session['conversation_scores'] = [] #
        session['initialized'] = True #
        session.modified = True #


    return render_template('index.html') #


@app.route('/chatbot_page')
def chatbot_page():
    """Serves the chatbot page content (chatbot.html) for the iframe."""
   
    return render_template('chatbot.html')


@app.route('/chat', methods=['POST'])
def chat_endpoint():
    """Handles chat messages, calculates score, and returns bot reply."""
    if not session.get('initialized'): #
        print("ERROR: /chat called but session not initialized.") #
     
        session.clear(); session['initialized'] = True; session['current_mood_context'] = INITIAL #
        session['asked_mood_questions'] = {mood: [] for mood in question_banks.keys()} #
        session['asked_time_questions'] = []; session['conversation_scores'] = []; session.modified = True #

    data = request.json #
    if data is None: return jsonify({"error": "Invalid request format"}), 400 #
    user_message = data.get('message') #

   
    current_mood_context = session.get('current_mood_context', INITIAL) #
    asked_mood_questions = session.get('asked_mood_questions', {mood: [] for mood in question_banks.keys()}) #
    asked_time_questions = session.get('asked_time_questions', []) #
    conversation_scores = session.get('conversation_scores', []) #
   
    if not isinstance(asked_mood_questions, dict): asked_mood_questions = {mood: [] for mood in question_banks.keys()} #
    for mood in question_banks.keys(): #
        if mood not in asked_mood_questions or not isinstance(asked_mood_questions[mood], list): asked_mood_questions[mood] = [] #
    if not isinstance(asked_time_questions, list): asked_time_questions = [] #
    if not isinstance(conversation_scores, list): conversation_scores = [] #

    bot_reply = "Something went wrong." #
    detected_mood_for_response = current_mood_context #
    next_mood_context_for_session = current_mood_context #

    try:
        if user_message is not None: # 
            print(f"\n--- Processing User Message ---") #
            print(f"DEBUG: Received: '{user_message[:50]}...' | Current Context: {current_mood_context}") #

            
            detected_mood, score = get_mood_and_score(user_message) #
            detected_mood_for_response = detected_mood #

         
            print(f"SCORE_ACCESS: Score for this message: {score:.4f}") #
            conversation_scores.append(score) #
            if score <= -0.5: print("SCORE_ACCESS: User sentiment is very negative.") #
            elif score < 0.1: print("SCORE_ACCESS: User sentiment is slightly negative or neutral.") #
            elif score >= 0.5: print("SCORE_ACCESS: User sentiment is very positive!") #
            else: print("SCORE_ACCESS: User sentiment is slightly positive.") #
            if len(conversation_scores) > 0: #
                try: print(f"SCORE_ACCESS: Average conversation score: {statistics.mean(conversation_scores):.4f}") #
                except Exception as stat_e: print(f"SCORE_ACCESS: Error calculating stats: {stat_e}") #

           
            print(f"DEBUG: Mood detected: {detected_mood}") #
            next_mood_context_for_session = detected_mood #
           
            if current_mood_context == SAD and detected_mood == HAPPY: next_mood_context_for_session = CALM #
            elif current_mood_context in [ANGRY, STRESSED] and detected_mood == HAPPY: next_mood_context_for_session = CALM #

            current_time = get_time_of_day_ist() #
            question, is_time, time_key = get_next_question(next_mood_context_for_session, current_time) #
            bot_reply = question #
            print(f"DEBUG: Selected Reply: '{bot_reply[:50]}...'") #

           
            if is_time and time_key: #
                 if (time_key, question) not in asked_time_questions: asked_time_questions.append((time_key, question)) #
            else: #
                 context_to_mark = next_mood_context_for_session #
                 if context_to_mark not in asked_mood_questions: asked_mood_questions[context_to_mark] = [] #
                 if question not in asked_mood_questions[context_to_mark]: asked_mood_questions[context_to_mark].append(question) #
            print("--- End Processing User Message ---\n") #

        else:
            print("\n--- Processing Initial Request ---") #
            current_time = get_time_of_day_ist() #
            question, is_time, time_key = get_next_question(INITIAL, current_time) #
            bot_reply = question #
            detected_mood_for_response = INITIAL #
            next_mood_context_for_session = INITIAL #
            print(f"DEBUG: Selected Initial Reply: '{bot_reply[:50]}...'") #
           
            if is_time and time_key: #
                 if (time_key, question) not in asked_time_questions: asked_time_questions.append((time_key, question)) #
            else: #
                 if INITIAL not in asked_mood_questions: asked_mood_questions[INITIAL] = [] #
                 if question not in asked_mood_questions[INITIAL]: asked_mood_questions[INITIAL].append(question) #
            print("--- End Initial Request ---\n") #

        
        session['current_mood_context'] = next_mood_context_for_session #
        session['asked_mood_questions'] = asked_mood_questions #
        session['asked_time_questions'] = asked_time_questions #
        session['conversation_scores'] = conversation_scores #
        session.modified = True #

      
        return jsonify({"bot_reply": bot_reply, "detected_mood": detected_mood_for_response}) #

    except Exception as e:
        print("\n!!!!!!!!!!!!!! ERROR in /chat !!!!!!!!!!!!!!") #
        print(f"Error Type: {type(e).__name__}: {e}") #
        traceback.print_exc() #
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n") #
        
        session.modified = True
        return jsonify({"error": f"Internal error: {type(e).__name__}.", "bot_reply": "Oops! My circuits are tangled."}), 500 #


@app.route('/reset', methods=['POST'])
def reset_session():
    """Clears the session and provides a new initial question."""
    print("DEBUG (Backend /reset): Resetting session.") #
    session.clear() #
    # 
    session['initialized'] = True; session['current_mood_context'] = INITIAL #
    session['asked_mood_questions'] = {mood: [] for mood in question_banks.keys()} #
    session['asked_time_questions'] = []; session['conversation_scores'] = [] #
    initial_question = "Okay, let's start over. How are you feeling now?" #
    try:
        current_time = get_time_of_day_ist() #
        question, is_time, time_key = get_next_question(INITIAL, current_time) #
        initial_question = question #
        # 
        if is_time and time_key: #
             if (time_key, question) not in session['asked_time_questions']: session['asked_time_questions'].append((time_key, question)) #
        else: #
             if INITIAL not in session['asked_mood_questions']: session['asked_mood_questions'][INITIAL] = [] #
             if question not in session['asked_mood_questions'][INITIAL]: session['asked_mood_questions'][INITIAL].append(question) #
        session.modified = True #
        return jsonify({"status": "success", "initial_message": initial_question}) #
    except Exception as e:
         print(f"ERROR during session reset's get_next_question: {e}") #
         traceback.print_exc() #
         session.modified = True # # 
         return jsonify({"status": "error", "message": "Failed to get new question after reset."}), 500 #

# --- Main Execution ---
if __name__ == '__main__':
    print("Starting Mood Reflect Bot application...") #
    if not setup_nltk_data(): #
        print("\nExiting: NLTK setup failed.") #
        sys.exit(1) #
    # Check for pytz library
    try: import pytz; print("pytz library found.") #
    except ImportError: print("\n--- WARNING: 'pytz' not installed. Using system local time. (pip install pytz)\n") #

    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}") #
    print("\nStarting Flask development server...") #
    print("Access the bot at: http://127.0.0.1:5000/") #
    print("Press CTRL+C to stop.") #
    # Set host='0.0.0.0' to make accessible on your local network
    app.run(debug=True, port=5000, host='127.0.0.1') #