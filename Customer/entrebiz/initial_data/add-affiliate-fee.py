"""
    1 time query to add affiliate fee for existing transaction
"""

import django
import sys
import os



project_dir_path = os.path.abspath(os.getcwd())
sys.path.append(project_dir_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'entrebiz.settings')
django.setup()
from utils.models import Internationaltransactions, Useraccounts

def add_affiliate_fee():
    for int_transaction in Internationaltransactions.objects.filter(isdeleted=False,hideforadmin=False):
        transaction = int_transaction.transaction
        if transaction.fromaccount.user_account.referred_by:
            transaction.affiliate_fee_percentage = 25
            transaction.save()

def add_refferal_fee():
    try:
        email = input('Enter email address ')
        user_account = Useraccounts.objects.get(customer__user__email=email,isdeleted=False)
        referees = user_account.user_referred_by.filter(isdeleted=False).order_by('-id')
        for referee in referees:
            referee.customer.outgoingtansactionfee = 25
            referee.customer.save()
    except:
        pass



if __name__ == '__main__':
    print("Starting ...")
    add_affiliate_fee()
    add_refferal_fee()
    print("Complete!")
