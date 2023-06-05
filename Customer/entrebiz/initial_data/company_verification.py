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
from utils.models import Customerdocumentfiles

def company_verifications():
    customer_files = Customerdocumentfiles.objects.filter(customerdocument__verificationtype__verificationtype=3)
    for customer_file in customer_files:
        customer_file.document_type = "Document"
        customer_file.save()


if __name__ == '__main__':
    print("Starting ...")
    company_verifications()
    print("Complete!")
