
"""
    create currency conversion margin.
    *Must create currency conversion margin data before running the application.
"""


import django
import sys
import os
import json


project_dir_path = os.path.abspath(os.getcwd())
sys.path.append(project_dir_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'entrebiz.settings')
django.setup()
from utils.models import Currencyconversionmargins,Currencies


filepath = 'entrebiz/initial_data/files/currency_conversion_margins.json'

def create_currency_conversions():
    f = open(filepath)
    CURRENCY_CONVERSION_MARGIN = json.load(f)
    for c_margin in CURRENCY_CONVERSION_MARGIN.get("CurrencyConversionMargins"):
        try:
            Currencyconversionmargins.objects.get_or_create(
                fromcurrency=Currencies.active.get(code=c_margin.get("FromCurrency")),
                tocurrency=Currencies.active.get(code=c_margin.get("ToCurrency")),
                marginpercent=0,
            )
        except:
            pass


if __name__ == '__main__':
    print("Starting ...")
    create_currency_conversions()
    print("Complete!")
