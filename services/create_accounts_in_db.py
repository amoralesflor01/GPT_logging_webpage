import services.data_service as svc

# user_ids = ['12345', '67890', '11122', '33344', '55678', '99001', '23456', '78901', '34567', '89012', '56789', '10123', '67812', '91234', '0', '1']

# For Testing the functionality of the displaying of same email to 1 user from each group.
# user_ids = ['0', '1', '2', '3']

user_ids = ['24080', '12442', '23492', '66612', '00800', '19237', '95123', '81739', '46791', '68315']

# function generate_users(n (n is even)):
# step 1: pick random uuid for email (calls pickRandomEmailUuid())
# step 2: generate one unique odd user id with the abv uuid
# step 3: generate one unique even user id with the abv uuid

def run_create_accounts():
    for user_id in user_ids:
        # Check if it already exists in the DB then skip
        existing_user = svc.find_account_by_user_id(user_id)
        if existing_user:
            # print(user_id, "Already exists, skipping.")
            continue
        else:
            svc.create_account(user_id)