"""
    It should be noted that in this model, the field that was linked to the country was not a foreign key. New fields have been added to convert it to a foreign key. We now use the previously existing value to connect the foreign key with the country model.
"""

import django
import sys
import os


project_dir_path = os.path.abspath(os.getcwd())
sys.path.append(project_dir_path)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "entrebiz.settings")
django.setup()
from utils.models import Countries, Businessdetails


def newfields_inherits_previous_values_in_business_details():
    for b in Businessdetails.objects.all():
        b.country_code = Countries.objects.filter(phonecode=b.countrycode).first()
        b.company_country = Countries.objects.filter(shortform=b.country).first()
        b.save()


if __name__ == "__main__":
    print("Starting ...")
    newfields_inherits_previous_values_in_business_details()
    print("Complete!")
