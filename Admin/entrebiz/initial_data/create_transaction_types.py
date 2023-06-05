"""
    create countries.
    *Must create Transaction Types before running the application.
"""

import django
import sys
import os



project_dir_path = os.path.abspath(os.getcwd())
sys.path.append(project_dir_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'entrebiz.settings')
django.setup()
from utils.models import Transactiontypes


transaction_types = [
    'Affiliate Fee',
    'Currency Conversion',
    'Company Inward Remittance Commission',
    'Referral Outward Remittance Commission',
    'Referral Inward Remittance Commission',
    'Other Charges',
    'Refund',
    'Inward Remittance',
    'Acccount To Account Transfer',
    'Conversion',
    'Third Party Transfer'
 ]


def create_transaction_types():
    for t_type in transaction_types:
        Transactiontypes.objects.get_or_create(name=t_type)


if __name__ == '__main__':
    print("Starting ...")
    create_transaction_types()
    print("Complete!")
