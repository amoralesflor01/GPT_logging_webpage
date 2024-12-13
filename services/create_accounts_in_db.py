import services.data_service as svc

# user_ids = ['24080', '12442', '23492', '66612', '10800', '19237', '95123', '81739', '46791', '68315']

user_ids = ['31501', '27241', '58577', '56699', '99550', '66428', '95445', '70905', '86471', '50574', '82434', '28477', '85634', '56566', '55212', '61269', '37190', '50845', '12086', '31154']

def run_create_accounts():
    # Separate users into experimental and control groups
    experimental_users = [user_id for user_id in user_ids if int(user_id) % 2 == 1]  # Odd IDs
    control_users = [user_id for user_id in user_ids if int(user_id) % 2 == 0]  # Even IDs

    # Check if the user counts match (should always be even)
    if len(experimental_users) != len(control_users):
        raise ValueError("Mismatch in experimental and control user counts. Ensure an even number of users.")

    # Pair users and assign emails
    for exp_user, ctrl_user in zip(experimental_users, control_users):
        # Check if experimental user already exists
        existing_exp_user = svc.find_account_by_user_id(exp_user)
        if not existing_exp_user:
            # Fetch the next email for the pair
            current_email = svc.pickRandomEmailUuid()
            print(f"Selected email {current_email} for pair ({exp_user}, {ctrl_user})")

            # Assign the email to the experimental user
            print(f"Creating account for experimental user {exp_user}")
            svc.create_account_with_email(exp_user, current_email)

        # Check if control user already exists
        existing_ctrl_user = svc.find_account_by_user_id(ctrl_user)
        if not existing_ctrl_user:
            # Assign the same email to the control user
            print(f"Creating account for control user {ctrl_user}")
            svc.create_account_with_email(ctrl_user, current_email)
