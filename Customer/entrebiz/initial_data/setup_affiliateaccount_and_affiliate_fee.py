"""
    1 time query to setup affiliate account and affiliate fee
"""

import django
import sys
import os



project_dir_path = os.path.abspath(os.getcwd())
sys.path.append(project_dir_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'entrebiz.settings')
django.setup()
from utils.models import Useraccounts

def show_referee_field_true_for_existing_users():
    for useraccount in Useraccounts.objects.all():
        for user in useraccount.user_referred_by.all():
            user.show_referee =True
            user.save()
    if int(input("should I run setup_affiliateaccount_and_affiliate_fee ?Please enter 0/1  ")) == 1:
        setup_affiliateaccount_and_affiliate_fee()

def setup_affiliateaccount_and_affiliate_fee():
    for useraccount in Useraccounts.objects.all():
        if useraccount.referred_by and useraccount.customer.customertype == 2:
            for affiliate_useraccount in Useraccounts.objects.filter(added_by=useraccount.added_by):
                affiliate_useraccount.referred_by = useraccount.referred_by
                affiliate_useraccount.customer.outgoingtansactionfee = useraccount.added_by.outgoingtansactionfee
                affiliate_useraccount.save()
                affiliate_useraccount.customer.save()
    update_reference_count()
    
def update_reference_count():
    for useraccount in Useraccounts.objects.all():     
        ref_count = useraccount.user_referred_by.filter(show_referee=True).count()
        useraccount.referencecount = ref_count
        useraccount.save()



if __name__ == '__main__':
    print("Starting ...")
    show_referee_field_true_for_existing_users()
    print("Complete!")
