"""
    1 time query to create full name for existing customers
"""

import django
import sys
import os



project_dir_path = os.path.abspath(os.getcwd())
sys.path.append(project_dir_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'entrebiz.settings')
django.setup()
from utils.models import Useraccounts

def create_fullname_for_existing_customers():
    for useraccount in Useraccounts.objects.all():
        fullname = ''
        if useraccount.firstname:
            fullname +=f"{useraccount.firstname} "
        if useraccount.middlename:
            fullname +=f"{useraccount.middlename} "
        if useraccount.lastname:
            fullname +=f"{useraccount.lastname}"
        useraccount.fullname = fullname
        useraccount.save()



if __name__ == '__main__':
    print("Starting ...")
    create_fullname_for_existing_customers()
    print("Complete!")
