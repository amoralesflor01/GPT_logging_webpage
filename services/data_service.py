from data_classes.users import User
from data_classes.conversation import Conversation
from data_classes.survey import SurveyResponse
import datetime
import pandas as pd
import numpy as np

# Global tracker for email assignments
email_tracker = {"current_email": None, "assigned_groups": {"experimental": False, "control": False}}

def pickRandomEmailUuid() -> str:
    global email_tracker

    # Read and process the emails as you currently do
    df = pd.read_csv("emails/merged_emails.csv")
    # Separate the rows based on classification
    class_0 = df[df['Classification'] == 0]
    class_1 = df[df['Classification'] == 1]

    # Calculate the minimum count between the two classes
    min_count = min(len(class_0), len(class_1))

    # Randomly sample 'min_count' entries from both classes to get equal proportions
    sample_0 = class_0.sample(n=min_count, random_state=np.random.randint(1000))
    sample_1 = class_1.sample(n=min_count, random_state=np.random.randint(1000))

    # Combine the samples
    balanced_sample = pd.concat([sample_0, sample_1])

    # Shuffle the result to ensure randomness
    balanced_sample = balanced_sample.sample(frac=1, random_state=np.random.randint(1000)).reset_index(drop=True)

    # Check if we need a new email
    if (
        email_tracker["current_email"] is None
        or all(email_tracker["assigned_groups"].values())
    ):
        # Select a new random email
        random_row = balanced_sample.sample(n=1, random_state=np.random.randint(1000))
        email_tracker["current_email"] = random_row["UniqueID"].values[0]
        email_tracker["assigned_groups"] = {"experimental": False, "control": False}

    # Return the currently tracked email
    return email_tracker["current_email"]

# def create_account(user_id: str) -> User:
#     user = User()
#     user.user_id = user_id
#     user.timer_is_running = False   # Is only true after login

#     user.email_id = pickRandomEmailUuid()
    
#     user.save() # This will actually update Mongo db. (Mongo follows lazy execution)

#     return user

def create_account(user_id: str) -> User:
    global email_tracker

    user = User()
    user.user_id = user_id
    user.timer_is_running = False   # Is only true after login

    # Determine the user's group
    is_experimental = int(user_id) % 2 == 1  # Odd IDs are experimental
    group_key = "experimental" if is_experimental else "control"

    # Assign email only if the current email hasn't been used for this group
    if not email_tracker["assigned_groups"][group_key]:
        user.email_id = pickRandomEmailUuid()
        email_tracker["assigned_groups"][group_key] = True
    else:
        # If somehow both groups are already assigned, assign a new random email
        user.email_id = pickRandomEmailUuid()

    user.save()  # Update MongoDB
    return user


def find_account_by_user_id(user_id: str) -> User:
    user = User.objects(user_id=user_id).first()
    return user


def start_timer_by_User(existing_user: User) -> datetime.datetime:
    # Reset the start time to now, only when the timer is triggered by clicking "Next"
    start_time = datetime.datetime.now(datetime.timezone.utc)
    existing_user.start_time = start_time
    existing_user.timer_is_running = True
    existing_user.save()

    return start_time


def append_conversation(user_id, is_bot, content):
    conv_history = Conversation()

    conv_history.is_bot = is_bot
    conv_history.content = content

    existing_user = find_account_by_user_id(user_id)
    existing_user.conversation_history.append(conv_history)
    existing_user.save()


# def pickRandomEmailUuid() -> str:
#     df = pd.read_csv("emails/merged_emails.csv")
#     # Separate the rows based on classification
#     class_0 = df[df['Classification'] == 0]
#     class_1 = df[df['Classification'] == 1]

#     # Calculate the minimum count between the two classes
#     min_count = min(len(class_0), len(class_1))

#     # Randomly sample 'min_count' entries from both classes to get equal proportions
#     sample_0 = class_0.sample(n=min_count, random_state=np.random.randint(1000))
#     sample_1 = class_1.sample(n=min_count, random_state=np.random.randint(1000))

#     # Combine the samples
#     balanced_sample = pd.concat([sample_0, sample_1])

#     # Shuffle the result to ensure randomness
#     balanced_sample = balanced_sample.sample(frac=1, random_state=np.random.randint(1000)).reset_index(drop=True)
#     random_row = balanced_sample.sample(n=1, random_state=np.random.randint(1000))

#     return random_row["UniqueID"].values[0]

def getEmailRecordByUuid(uuid: str) -> pd.core.frame.DataFrame:
    df = pd.read_csv("emails/merged_emails.csv")
    single_record = df[df["UniqueID"]==uuid]

    return single_record


def store_survey_response(user_id, responses, is_pre_survey=False):
    # Find the user document
    user = find_account_by_user_id(user_id)
    
    if user:
        # If it's the pre-survey, store it separately in the user document
        if is_pre_survey:
            user.pre_survey_responses = responses
        else:
            # Otherwise, store it as the final survey
            user.survey_responses = responses
        
        user.save()  # Save the updated user document