from data_classes.users import User
from data_classes.conversation import Conversation
from data_classes.survey import SurveyResponse
import datetime
import pandas as pd
import numpy as np
from collections import defaultdict

# Global dictionary to track email usage counts
email_usage_counter = defaultdict(int)
email_list = []  # Holds the list of all emails

def loadEmails():
    """Load and process emails into a list for balanced assignment."""
    global email_list
    df = pd.read_csv("emails/dataset.csv")
    class_0 = df[df['Classification'] == 0]
    class_1 = df[df['Classification'] == 1]

    # Equalize proportions
    min_count = min(len(class_0), len(class_1))
    sample_0 = class_0.sample(n=min_count, random_state=42)
    sample_1 = class_1.sample(n=min_count, random_state=42)
    balanced_sample = pd.concat([sample_0, sample_1])

    # Shuffle and extract UniqueIDs
    email_list = balanced_sample["UniqueID"].tolist()

def pickBalancedEmailUuid() -> str:
    """Pick an email with the least usage count to ensure balance."""
    global email_usage_counter, email_list

    # If email list is empty, reload
    if not email_list:
        loadEmails()

    # Sort emails by their usage count and select the least used one
    least_used_email = sorted(email_list, key=lambda email: email_usage_counter[email])[0]

    # Increment its usage count
    email_usage_counter[least_used_email] += 1
    return least_used_email


# # Global tracker for email assignments
# email_tracker = {
#     "used_emails": set(),  # Keep track of emails that have been assigned to valid pairs
#     "current_email": None,  # Current email being used
#     "assigned_groups": {"experimental": None, "control": None},  # Track assigned groups
# }

def create_account_with_email(user_id: str, email_id: str) -> User:
    user = User()
    user.user_id = user_id
    user.timer_is_running = False  # Is only true after login
    user.email_id = email_id  # Assign the specific email
    user.save()
    return user


# def pickRandomEmailUuid() -> str:
#     global email_tracker

#     # Read and process the emails
#     df = pd.read_csv("emails/dataset.csv")
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
#     balanced_sample = balanced_sample.sample(frac=1, random_state=np.random.randint(1000)).reset_index(drop=True)

#     # Log the size of the balanced sample
#     print(f"Balanced sample size: {len(balanced_sample)}")

#     # Loop until an unused email is found
#     while True:
#         random_row = balanced_sample.sample(n=1, random_state=np.random.randint(1000))
#         random_email = random_row["UniqueID"].values[0]

#         # Log each email selection attempt
#         print(f"Attempting to use email: {random_email}")
#         if random_email not in email_tracker["used_emails"]:
#             email_tracker["current_email"] = random_email
#             email_tracker["assigned_groups"] = {"experimental": False, "control": False}
#             print(f"Selected new email: {random_email}")
#             break
#     return email_tracker["current_email"]


def create_account(user_id: str) -> User:
    global email_tracker

    user = User()
    user.user_id = user_id
    user.timer_is_running = False  # Is only true after login

    # Determine the user's group
    is_experimental = int(user_id) % 2 == 1  # Odd IDs are experimental
    group_key = "experimental" if is_experimental else "control"

    print(f"Creating account for user {user_id} in group {group_key}")

    while True:
        current_email = pickRandomEmailUuid()

        # Check if the current email is already fully assigned
        if all(email_tracker["assigned_groups"].values()):
            print(f"Email {current_email} fully assigned. Marking as used.")
            email_tracker["used_emails"].add(email_tracker["current_email"])
            email_tracker["current_email"] = None  # Reset current email
            email_tracker["assigned_groups"] = {"experimental": False, "control": False}
        else:
            # If this email is not yet assigned to the user's group, assign it
            if not email_tracker["assigned_groups"][group_key]:
                user.email_id = current_email
                email_tracker["assigned_groups"][group_key] = True
                print(f"Assigned email {current_email} to user {user_id} in group {group_key}")
                break

    # Save the user
    user.save()
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