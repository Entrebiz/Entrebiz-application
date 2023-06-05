"""
    To be deleted
"""

import django
import sys
import os


project_dir_path = os.path.abspath(os.getcwd())
sys.path.append(project_dir_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'entrebiz.settings')
django.setup()
from utils.models import Transactions

def remove_existing_affiliate_tr_note():
    for tr in Transactions.objects.filter(transactiontype__name="Affiliate Fee"):
        if tr.note == "Affiliate fee":
            tr.note = ""
            tr.save()


if __name__ == '__main__':
    print("Starting ...")
    remove_existing_affiliate_tr_note()
    print("Complete!")
