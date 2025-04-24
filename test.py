import re
from email_validator import validate_email, EmailNotValidError
'''
hash_table = {}
hash_table['topic'] = ''
hash_table['description'] = 'adad'
hash_table['email'] = ''
fields = ["topic","description","phone","email"]
for i in fields:
    try:
        hash_table[i]
    except KeyError as e:
        print(f"Field {e} not exist")

from email_validator import validate_email, EmailNotValidError
def is_email_valid(email):
    heloo = 1
    try:
        validate_email(email,check_deliverability=True)
        print('valid')
    except EmailNotValidError as e:
        print(e)
        return False
'''
def validate_email_(email):
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if re.match(pattern,email) and validate_email(email,check_deliverability=True):
        return email
    else:
        print("invalid email")
        return False
    
validate_email_(input())

