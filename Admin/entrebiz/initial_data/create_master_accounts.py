"""
    create master user and accounts in all currencies.
    *Do not add any master user/accounts manually.
"""


import django
import sys
import os
project_dir_path = os.path.abspath(os.getcwd())
sys.path.append(project_dir_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'entrebiz.settings')
django.setup()

master_acc_email = "ebzmaster@testmail.com"


def create_master_user():
    from django.contrib.auth.models import User
    from utils.models import Useraccounts, Customers
    try:
        user_account = Useraccounts.objects.get(ismaster_account=True)
    except:
        try:
            user = User.objects.get(email=master_acc_email)
        except:
            user = User.objects.create(email=master_acc_email, username=randomword(10),
                                       first_name="Entrebiz", last_name="Master")
        customer = Customers.objects.create(
            user=user, customertype=1, isactive=True)
        user_account = Useraccounts.objects.create(
            slug=randomword(10),
            customer=customer,
            ismaster_account=True, firstname="Entrebiz", middlename="Master",
            lastname="Account", activestatus="Verified"

        )
    return user_account

def create_master_accounts():
    from utils.models import Accounts, Currencies
    user_account = create_master_user()
    MASTER_ACC_NO = 20000100
    for currency in Currencies.active.all():
        try:
            account = Accounts.objects.get(user_account=user_account,currency=currency)
        except:

            account = Accounts.objects.create(slug=randomword(10),user_account=user_account,currency=currency,
                                              accounttype=1,balance=0,createdby=user_account.customer.user)
        while Accounts.objects.filter(accountno=MASTER_ACC_NO):
            MASTER_ACC_NO += 1
        if not account.accountno:
            account.accountno = MASTER_ACC_NO
            account.save()
    return True

def randomword(length):
    import string
    str_letters = string.ascii_lowercase
    import random
    return ''.join(random.choice(str_letters) for i in range(length))


if __name__ == '__main__':
    print("Starting ...")
    create_master_accounts()
    print("Complete!")
