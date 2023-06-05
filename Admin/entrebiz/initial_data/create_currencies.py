"""
    create currency.
    *Must create currency data before running the application.
"""

import json
import django
import sys
import os
import logging

logger = logging.getLogger('lessons')
project_dir_path = os.path.abspath(os.getcwd())
sys.path.append(project_dir_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'entrebiz.settings')
django.setup()
from utils.models import Currencies

filepath = 'entrebiz/initial_data/files/currencies.json'
f = open(filepath)
CURRENCIES_JSON = json.load(f)
def create_currencies():
    for currency in CURRENCIES_JSON.get("Currencies"):
        if currency.get('Code') and currency.get('Name') and currency.get('MarginPercent'):
            Currencies.objects.get_or_create(code=currency.get('Code'),
                                            name=currency.get('Name'),
                                            marginpercent=currency.get('MarginPercent'))
            

if __name__ == '__main__':
    print("Starting ...")
    create_currencies()
    print("Complete!")
