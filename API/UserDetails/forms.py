import re

from django.forms import ModelForm, forms
from Transactions.mixins import checkNonAsciiChracters

from utils.models import Useraccounts


class UserDetailsForm(ModelForm):

    class Meta:
        model = Useraccounts
        fields = ('street_address',
                  'city',
                  'region',
                  'zipcode',
                  'phonenumber',
                  'countrycode'
                  )

    def clean_phonenumber(self):
        phonenumber = self.cleaned_data.get("phonenumber")
        if phonenumber and not phonenumber.isdigit():
            raise forms.ValidationError("Invalid phone number format")
        return phonenumber
    def clean_street_address(self):
        street_address = self.cleaned_data.get("street_address")
        if not checkNonAsciiChracters(street_address):
            raise forms.ValidationError("Fancy characters are not allowed")
        elif not street_address:
            raise forms.ValidationError("This field is required.")
        return street_address
    def clean_city(self):
        city = self.cleaned_data.get("city")
        if not checkNonAsciiChracters(city):
            raise forms.ValidationError("Fancy characters are not allowed")
        elif not city:
            raise forms.ValidationError("This field is required.")
        return city
    def clean_region(self):
        region = self.cleaned_data.get("region")
        if not checkNonAsciiChracters(region):
            raise forms.ValidationError("Fancy characters are not allowed")
        elif not region:
            raise forms.ValidationError("This field is required.")
        return region
