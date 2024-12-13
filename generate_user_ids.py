import random

def generate_random_numbers(digits, user_ids):
    if digits <= 0 or user_ids <= 0:
        raise ValueError("Digits and user_ids must be positive integers.")
    
    if user_ids % 2 != 0:
        raise ValueError("The total number of user IDs must be even to split evenly into half even and half odd.")
    
    # Ensure that we can generate the required user_ids of numbers with the given constraints
    max_possible = 9 * (10 ** (digits - 1)) // 2
    if user_ids > max_possible * 2:
        raise ValueError("Not enough unique numbers possible with the given constraints.")
    
    even_numbers = set()
    odd_numbers = set()

    # Generate unique even and odd numbers until the desired count is met
    while len(even_numbers) < user_ids // 2:
        num = random.randint(10**(digits-1), 10**digits - 1)
        if num % 2 == 0:
            even_numbers.add(num)

    while len(odd_numbers) < user_ids // 2:
        num = random.randint(10**(digits-1), 10**digits - 1)
        if num % 2 != 0:
            odd_numbers.add(num)
    
    # Combine the even and odd numbers
    final_numbers = list(even_numbers | odd_numbers)
    random.shuffle(final_numbers)

    # Prepare the output format
    user_ids_list = [str(num) for num in final_numbers]
    
    # Print summary
    print(f"Total number of user IDs generated: {len(final_numbers)}")
    print(f"Even ID numbers: {len(even_numbers)}")
    print(f"Odd ID numbers: {len(odd_numbers)}")
    print("user_ids =", user_ids_list)

# Enter the desired amount of digits in User ID and the amount of User IDs you wish to generate
generate_random_numbers(digits=5, user_ids=20)
