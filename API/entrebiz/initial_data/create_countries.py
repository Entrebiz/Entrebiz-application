"""
    create countries.
    *Must create countries before running the application.
"""


import django
import sys
import os
import json


project_dir_path = os.path.abspath(os.getcwd())
sys.path.append(project_dir_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'entrebiz.settings')
django.setup()
from utils.models import Countries


filepath = 'entrebiz/initial_data/files/countries.json'
f = open(filepath)
COUNTRIES_JSON = json.load(f)
def create_countries():
    for country in COUNTRIES_JSON.get("Countries"):
        if country.get('PhoneCode') and country.get('Name') and country.get('ShortForm'):
            Countries.objects.get_or_create(name=country.get('Name'),
                                            shortform=country.get('ShortForm'),
                                            phonecode=country.get('PhoneCode'))


if __name__ == '__main__':
    print("Starting ...")
    create_countries()
    print("Complete!")
