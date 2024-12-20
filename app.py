# Import necessary libraries
from flask import Flask, render_template, request, redirect, session, url_for, flash, make_response
from openai import OpenAI
import os
import time
import json
import csv
import pandas as pd
import random
import atexit
import secrets  # For generating a secure random key
from functools import wraps
import math
import datetime
import data_classes.mongo_setup as mongo_setup
import services.data_service as svc
from services.create_accounts_in_db import run_create_accounts
# from apscheduler.schedulers.background import BackgroundScheduler
from data_classes.survey import SurveyResponse


# Connect with Mongo DB
mongo_setup.global_init()

# Make sure all userIds are loaded into DB
run_create_accounts()

# Load the config.json file
with open('config.json') as f:
    config = json.load(f)

# Access API key using the config dictionary
my_api_key = config['openai-api-key']

# Set the OpenAI API key
api_key = my_api_key
client = OpenAI(api_key=api_key)

# Set the default timer in seconds
TIMER_LIMIT = 300

# Define the name of the bot
name = 'Assitant'

# Define the role of the bot
role = 'Helpful Chatbot'

# Define the impersonated role with instructions @girma_terfa
impersonated_role = f"""
    From now on, you are going to act as {name}. Your role is {role}."""


initial_message = 'Hello, I am a ChatBot. I am designed to help you with identifying spam emails. Please feel free to ask me anything! Your UserID is '

cwd = os.getcwd()

# Create a Flask web application
application = Flask(__name__)

# Set the secret key using a securely generated random key
application.secret_key = secrets.token_hex(16)

# Global variable to store session data outside the request context
user_sessions = {}


# Save the used and in-use user IDs to a JSON file
def save_used_ids(used_ids):
    with open('used_ids.json', 'w') as f:
        json.dump(used_ids, f)



# A timer check helper function
def session_timeout():
    # Check if the session has a start time
    if 'start_time' in session:
        current_time = datetime.datetime.now(datetime.timezone.utc)
        start_time = session['start_time']
        
        elapsed_time = math.floor((current_time - start_time).total_seconds())

        # If the timer limit has been exceeded, end the session and redirect
        if elapsed_time > TIMER_LIMIT:
            session['timeout_occurred'] = True
            return redirect(url_for('end_chat_session'))
    
    return None


# a decorator or helper to enforce session validity for protected routes
def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session or 'session_token' not in session:
            flash("You must log in first!")
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return wrapper
    


# Route for the login page
@application.route("/", methods=['GET', 'POST'])
def login():
    # Redirect already logged-in users
    if 'user_id' in session and 'session_token' in session:
        flash("You are already logged in!")
        # Redirect to appropriate page based on session state
        if session.get("consent") is False:
            return redirect(url_for('consent'))
        elif session.get("pre_survey") is False:
            return redirect(url_for('pre_survey'))
        elif session.get("instructions") is False:
            return redirect(url_for('instructions'))
        elif session.get("start_timer") is False:
            return redirect(url_for('start_timer'))
        else:
            return redirect(url_for('chatbot'))
    
    # Handle POST request (login form submission)
    if request.method == 'POST':
        user_id = request.form.get('password')  # Get user ID from form input
        existing_user = svc.find_account_by_user_id(user_id)

        if existing_user:
            # Prevent login if the survey is completed
            if existing_user.survey_completed:
                flash("Survey already completed. You cannot log in again.")
                return redirect(url_for('login'))

            # Ensure consistent session start time (timezone-aware)
            start_time = existing_user.start_time
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=datetime.timezone.utc)

            # Initialize conversation history if not already present
            if not existing_user.conversation_history:
                svc.append_conversation(user_id, is_bot=True, content=initial_message + user_id)

            # Generate a unique session token for this login
            session['session_token'] = secrets.token_hex(16)
            session['user_id'] = user_id
            session["email_id"] = existing_user.email_id

            # Initialize other session variables
            session["consent"] = False
            session["pre_survey"] = False
            session["instructions"] = False
            session["start_timer"] = False
            session["chatbotDone"] = False

            # Redirect to the consent page
            return redirect(url_for('consent'))
        else:
            # Invalid login attempt
            flash("Invalid User ID! Please try again.")
            return redirect(url_for('login'))

    # Handle GET request (display login form)
    return render_template('login.html')



# Function to complete chat input using OpenAI's GPT-3.5 Turbo
def chatcompletion(conversation_history):

    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=conversation_history
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print("OpenAI Error:", e)
        return "Failed to generate, please try again!"

# Function to handle user chat input
def chat(user_input):
    conversation_history = session.get('chat_history', [])
    
    # If empty, add initial System instruction
    if conversation_history == [] or conversation_history == '':
        conversation_history = []
        tmp = {
            "role": "system",
            "content": impersonated_role
        }
        conversation_history.append(tmp)

    # Sometimes Flask sends the session stuff as a string instead. Weird.
    if type(conversation_history) == str:
        conversation_history = eval(conversation_history)
    
    # Add user input to the conversation
    conversation_history.append({"role": "user", "content": user_input})
    svc.append_conversation(session['user_id'], is_bot=False, content=user_input)
    
    # Call GPT-3.5 Turbo to get a response
    chatgpt_raw_output = chatcompletion(conversation_history)
    
    # Add GPT response to the conversation
    conversation_history.append({"role": "assistant", "content": chatgpt_raw_output})
    svc.append_conversation(session['user_id'], is_bot=True, content=chatgpt_raw_output)
    
    # Save the conversation history in the session
    session['chat_history'] = conversation_history
    
    # Ensure the user_sessions entry exists
    if session['user_id'] not in user_sessions:
        user_sessions[session['user_id']] = {}

    # Update the global user_sessions dictionary
    user_sessions[session['user_id']]['chat_history'] = conversation_history
    
    return chatgpt_raw_output


# Function to get a response from the chatbot
def get_response(userText):
    return chat(userText)

# *********************************************************

import re
from markupsafe import Markup

def replace_links(text):
    # Regex to find both http and https URLs
    url_pattern = r'(http[s]?://[^\s]+)'
    
    # Replace URLs with clickable but non-functional links
    replaced_text = re.sub(
        url_pattern,
        r'<a href="#" onclick="return false;" style="color: #0000EE; text-decoration: underline;">\1</a>',
        text
    )
    return Markup(replaced_text)  # Mark the text as safe HTML

# Register the filter with Flask
application.jinja_env.filters['replace_links'] = replace_links

# *********************************************************


# Modify the chatbot route to pass email data to the template
@application.route("/chatbot")
@login_required
def chatbot():
    
    # Prevent users from accessing the chatbot route after the session is marked as done
    if session.get("chatbotDone", False):
        flash("You have completed your chatbot session and cannot return.")
        return redirect(url_for('survey'))
    
    # Ensure user is logged in and has a valid session token
    check_return_status = check_user_status(current_page="chatbot")
    if check_return_status != 0:
        return check_return_status
    
    if session["chatbotDone"]:
        redirect(url_for('survey'))

    # Checking if the session has expired
    timeout_redirect = session_timeout()
    if timeout_redirect:
        return timeout_redirect  # If session has timed out, redirect to login

    # Fetch the user's start_time and ensure it's timezone-aware
    existing_user = svc.find_account_by_user_id(session['user_id'])
    start_time = existing_user.start_time

    # Ensure start_time is timezone-aware
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=datetime.timezone.utc)

    # Make current_time timezone-aware
    current_time = datetime.datetime.now(datetime.timezone.utc)

    # Calculate remaining time only after the timer has started
    if existing_user.timer_is_running:
        end_time = start_time + datetime.timedelta(seconds=TIMER_LIMIT)
        time_left = max(0, math.ceil((end_time - current_time).total_seconds()))
    else:
        time_left = TIMER_LIMIT  # If the timer hasn't started, show full time

    # Fetch email to display
    email = svc.getEmailRecordByUuid(session["email_id"])

    # Debugging: Log the email assignment
    print(f"User ID: {session['user_id']}, Email ID: {session['email_id']}")

    # For testing longer email text obstruction by chatbot box (DO NOT REMOVE)
    # email = svc.getEmailRecordByUuid("8e770999-7f81-4cb6-85ae-15cc2b2aaf2a")

    email_sender = email["From"].values[0]
    email_subject = email["Subject"].values[0]
    email_content = email["Email Content"].values[0]

    return render_template(
        "index.html", 
        userId=session['user_id'],
        user_id_int=int(session['user_id']),
        TIMER_LIMIT=time_left,
        email_sender=email_sender,
        email_subject=email_subject,
        email_content=email_content,
        convo_history=existing_user.conversation_history
    )


# Define the route for getting the chatbot's response
@application.route("/get")
@login_required
def get_bot_response():

    # Checking if server logged out! (Due to tab sync issues) (Can't be fixed until UI timer and Python timer are exactly the same)
    if 'user_id' not in session or 'session_token' not in session:
        return redirect(url_for('login'))  # If not logged in, redirect to login page
    
    # Checking if the session has expired
    timeout_redirect = session_timeout()
    if timeout_redirect:
        return timeout_redirect  # If session has timed out, redirect to login
    
    userText = request.args.get('msg')  # Get the user input from the request parameters.
    return str(get_response(userText))  # Pass the user input to get_response and return the chatbot's response as a string.

# Define a route for refreshing the page
@application.route('/refresh')
def refresh():
    time.sleep(600)  # Wait for 10 minutes (600 seconds).
    return redirect('/refresh')  # Redirect to the /refresh route again, creating a loop.


@application.template_filter('timer_format')
def timer_format(value_in_seconds):
    return f"{math.floor(value_in_seconds/60):02}:{(value_in_seconds%60):02}"


@application.template_filter('message_side_format')
def message_side_format(is_bot):
    return "left" if is_bot else "right"


# Save session info to file and clean up the "in use" list
def save_user_session_data():
    for user_id, data in user_sessions.items():
        if 'start_time' not in data:
            print(f"User {user_id} is missing start_time")
            continue  # Skip saving if start_time is missing
        
        start_time = data['start_time']
        user_dir = data['user_dir']
        chat_history = data['chat_history']

        elapsed_time_seconds = math.floor((datetime.datetime.now(datetime.timezone.utc) - start_time).total_seconds())
        elapsed_time_minutes_seconds = time.strftime("%M:%S", time.gmtime(elapsed_time_seconds))

        # Define the JSON file path
        json_file = os.path.join(user_dir, f'user_{user_id}_info.json')

        # Create the JSON file with the session information
        session_info = {
            'User ID': user_id,
            'Elapsed Time (Minutes:Seconds)': elapsed_time_minutes_seconds,
            'Elapsed Time (Seconds)': int(elapsed_time_seconds),
            'Chat History': chat_history
        }

        try:
            # Write the JSON file
            with open(json_file, 'w') as f:
                json.dump(session_info, f, indent=4)
            print(f"JSON file created successfully: {json_file}")
        except Exception as e:
            print(f"Failed to create JSON file: {e}")


@application.route("/end-chat-session")
@login_required
def end_chat_session():
    user_id = session.get('user_id')

    session["chatbotDone"] = True

    if user_id:
        # Save user session data
        # save_user_session_data()
        
        # Fetch the user record
        user = svc.find_account_by_user_id(user_id)
        if user:
            if not user.survey_completed:
                user.timer_is_running = False  # Stop the timer
                user.save()

    # Redirect to post survey page
    return redirect(url_for('survey'))




@application.route("/survey", methods=['GET', 'POST'])
@login_required
def survey():
    user_id = session.get('user_id')
    
    # Check if the user has completed the survey
    if session.get("chatbotDone", False) and svc.find_account_by_user_id(user_id).survey_completed:
        flash("Survey already completed. Thank you!")
        return render_template("thank_you.html")  # Redirect to a thank-you page

    check_return_status = check_user_status(current_page="post_survey")
    if check_return_status != 0:
        return check_return_status


    if request.method == 'POST':
        # Retrieve survey responses and handle multiple selections
        survey_responses = {
            key: ", ".join(request.form.getlist(key)) if len(request.form.getlist(key)) > 1 else request.form[key]
            for key in request.form.keys()
        }

        # Find the user and update survey responses
        user = svc.find_account_by_user_id(user_id)
        if user:
            user.survey_responses = survey_responses
            user.survey_completed = True  # Mark survey as completed
            user.timer_is_running = False  # Ensure the timer is stopped
            user.save()

        flash("Survey responses saved successfully. Session ended.")
        session.clear()  # Clear the session fully after survey is completed

        # Redirect to the thank-you page or external link
        return render_template("redirect_after_submit.html", redirect_url="https://app.prolific.com/submissions/complete?cc=C1NOLJRJ")

    # Fetch email to display in the survey page
    email = svc.getEmailRecordByUuid(session["email_id"])
    email_sender = email["From"].values[0]
    email_subject = email["Subject"].values[0]
    email_content = email["Email Content"].values[0]

    return render_template(
        'survey.html', 
        email_sender=email_sender,
        email_subject=email_subject,
        email_content=email_content,
        user_id_int=int(user_id)
    )


@application.route("/consent", methods=['GET', 'POST'])
@login_required
def consent():
    check_return_status = check_user_status(current_page="consent")
    if check_return_status != 0:
        return check_return_status
    
    if session["consent"]:   # if already given consent, redirect to presurvey
        return redirect(url_for('pre_survey'))
    
    if request.method == 'POST':
        # consent_given = request.form.get('consent')
        
        # if consent_given != 'yes':
        #     flash("You must give consent to proceed.")
        #     return redirect(url_for('consent'))
        
        # Proceed to pre-survey after consent is given
        session["consent"] = True
        return redirect(url_for('pre_survey'))

    return render_template('consent.html')  # Ensure you create this template


def check_user_status(current_page = ""):
    # login page and default
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # reached consent
    if current_page == "consent":
        return 0
    print("HELLO")
    print(session["consent"])
    if not session["consent"]:
        return redirect(url_for('consent'))
    
    # reached pre_survey
    if current_page == "pre_survey":
        return 0
    if not session["pre_survey"]:
        return redirect(url_for('pre_survey'))
    
    # reached instructions
    if current_page == "instructions":
        return 0
    if not session["instructions"]:
        return redirect(url_for('instructions'))
    
    # reached start timer
    if current_page == "start_timer":
        return 0
    if not session["start_timer"]:
        return redirect(url_for('start_timer'))

    return 0    # default


@application.route("/pre-survey", methods=['GET', 'POST'])
@login_required
def pre_survey():
    check_return_status = check_user_status("pre_survey") # check for missing user statuses
    if check_return_status != 0:
        return check_return_status

    if session["pre_survey"]:   # if already given consent, redirect to presurvey
        return redirect(url_for('instructions'))

    if request.method == 'POST':
        # Save pre-survey responses to DB
        pre_survey_responses = {
            key: ", ".join(request.form.getlist(key)) if len(request.form.getlist(key)) > 1 else request.form[key]
            for key in request.form.keys()
        }

        # Save pre-survey responses to DB
        #pre_survey_responses = request.form.to_dict()
        # Collect multiple checkbox values for 'computer-literacy' field
        #pre_survey_responses['computer-literacy'] = request.form.getlist('computer-literacy')
        
        #pre_survey_responses['features'] = request.form.getlist('features')
        
        # Save pre-survey responses in the user's document
        svc.store_survey_response(session['user_id'], pre_survey_responses, is_pre_survey=True)

        session["pre_survey"] = True
        
        # Redirect to instructions page
        return redirect(url_for('instructions'))

    return render_template('pre_survey.html', user_id = int(session['user_id']))


@application.route("/instructions", methods=['GET', 'POST'])
@login_required
def instructions():
    check_return_status = check_user_status("instructions")
    if check_return_status != 0:
        return check_return_status

    if session["instructions"]:
        return redirect(url_for('start_timer'))

    if request.method == 'POST':
        # consent_given = request.form.get('consent')
        
        # if consent_given != 'yes':
        #     flash("You must give consent to proceed.")
        #     return redirect(url_for('consent'))
        
        # Proceed to pre-survey after consent is given
        session["instructions"] = True
        return redirect(url_for('start_timer'))
    

    # next button in the template
    # redirects to url_for("start_timer")
    # should be here but whatev
    return render_template('instructions.html', user_id = int(session['user_id']))



@application.route("/start-timer", methods=['GET', 'POST'])
@login_required
def start_timer():
    # Starts the timer on the backend and redirects you to chatbot.
    check_return_status = check_user_status("start_timer")
    if check_return_status != 0:
        return check_return_status

    if session["start_timer"]:
        return redirect(url_for('chatbot'))

    # Start the timer only when the "Next" button is clicked on the instructions page
    if not session["start_timer"]:
        svc.start_timer_by_User(svc.find_account_by_user_id(session['user_id']))

    session["start_timer"] = True

    # Redirect to chatbot
    return redirect(url_for('chatbot'))


# Applies no-cache headers to every route
@application.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "-1"
    return response


# Register the save_user_session_data function to be called when the program exits
atexit.register(save_user_session_data)
# atexit.register(lambda: scheduler.shutdown())

if __name__ == "__main__":
    application.run(host="0.0.0.0", port=5000)  # Run the application
