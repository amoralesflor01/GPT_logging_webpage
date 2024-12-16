import services.data_service as svc

# user_ids = ['24080', '12442', '23492', '66612', '10800', '19237', '95123', '81739', '46791', '68315']

user_ids = ['7926068', '4974123', '6759496', '8483881', '1448006', '1245123', '6008293', '5818218', '6740057', '8887228']

def run_create_accounts():
    # Separate users into experimental and control groups
    experimental_users = [user_id for user_id in user_ids if int(user_id) % 2 == 1]  # Odd IDs
    control_users = [user_id for user_id in user_ids if int(user_id) % 2 == 0]  # Even IDs

    # Check if the user counts match (should always be even)
    if len(experimental_users) != len(control_users):
        raise ValueError("Mismatch in experimental and control user counts. Ensure an even number of users.")

    # Pair users and assign emails
    for exp_user, ctrl_user in zip(experimental_users, control_users):
        # Fetch the next balanced email for the pair
        current_email = svc.pickBalancedEmailUuid()
        print(f"Selected email {current_email} for pair ({exp_user}, {ctrl_user})")

        # Check and create experimental user
        existing_exp_user = svc.find_account_by_user_id(exp_user)
        if not existing_exp_user:
            print(f"Creating account for experimental user {exp_user}")
            svc.create_account_with_email(exp_user, current_email)

        # Check and create control user
        existing_ctrl_user = svc.find_account_by_user_id(ctrl_user)
        if not existing_ctrl_user:
            print(f"Creating account for control user {ctrl_user}")
            svc.create_account_with_email(ctrl_user, current_email)
