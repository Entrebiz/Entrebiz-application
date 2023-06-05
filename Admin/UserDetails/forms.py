import re

from django.forms import ModelForm, forms

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
