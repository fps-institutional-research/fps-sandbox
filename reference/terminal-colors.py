RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
RESET = '\033[0m'  # Crucial to reset color back to default

# Print colored text using f-strings
print(f"{RED}This is an error message!{RESET}")
print(f"{GREEN}This is a success message!{RESET}")
print(f"This is {YELLOW}partially yellow{RESET} text.")