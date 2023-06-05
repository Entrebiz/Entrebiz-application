"""
    create currency conversion margin.
    *Must create currency conversion margin data before running the application.
"""

import django
import sys
import os
import logging

logger = logging.getLogger('lessons')
project_dir_path = os.path.abspath(os.getcwd())
sys.path.append(project_dir_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'entrebiz.settings')
django.setup()
from utils.models import Currencyconversionmargins, Currencies


def create_currency_conversions():
    FromCurrencyCodes = list(Currencies.objects.filter(isdeleted=False).values_list('code', flat=True))
    ToCurrencyCodes = list(Currencies.objects.filter(isdeleted=False).values_list('code', flat=True))
    for FromCurrencyCode in FromCurrencyCodes:
        for ToCurrencyCode in ToCurrencyCodes:
            try:
                if FromCurrencyCode != ToCurrencyCode:
                    conversion_obj, created = Currencyconversionmargins.objects.get_or_create(
                        fromcurrency=Currencies.active.get(code=FromCurrencyCode),
                        tocurrency=Currencies.active.get(code=ToCurrencyCode))
                    if created:
                        conversion_obj.marginpercent = 0
                        conversion_obj.save()
                    elif float(conversion_obj.marginpercent) == 0:
                        conversion_obj.marginpercent = 2
                        conversion_obj.save()

            except Exception as e:
                logger.info(e)


if __name__ == '__main__':
    print("Starting ...")
    create_currency_conversions()
    print("Complete!")
