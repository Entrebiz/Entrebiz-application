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
from utils.models import Industrytypes

filepath = 'entrebiz/initial_data/files/industrytypes.json'
f = open(filepath)
INDUSTRY_TYPES_JSON = json.load(f)


def create_countries():
    for industry_type in INDUSTRY_TYPES_JSON.get("IndustryTypes"):
        Industrytypes.objects.get_or_create(name=industry_type.get('Name'))


if __name__ == '__main__':
    print("Starting ...")
    create_countries()
    print("Complete!")
