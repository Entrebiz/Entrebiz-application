import re
import logging

from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelForm

from utils.models import Currencies, Externalbeneficiaries, Countries, Internalbeneficiaries, Accounts
logger = logging.getLogger('lessons')


class InternalBeneficiaryForm(ModelForm):
    accountnumber = forms.CharField(max_length=10)
    firstname = forms.CharField(max_length=10)
    lastname = forms.CharField(max_length=10)
    user_type = forms.CharField(max_length=10)
    class Meta:
        model = Internalbeneficiaries
        fields = ('receivername',)


class ExternalBeneficiaryForm(ModelForm):
    currency = forms.CharField(max_length=10)
    country = forms.CharField(max_length=10)
    class Meta:
        model = Externalbeneficiaries
        fields = ('name',
                  'accountnumber',
                  'swiftcode',
                  'city',
                  'bankname',
                  'email',
                  )

    def clean_email(self):
        email_regex = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
        email = self.cleaned_data.get("email")
        if email and not re.match(email_regex, email):
            raise forms.ValidationError("Invalid email format")
        return email

    def clean_currency(self):
        try:
            currency = self.cleaned_data.get('currency')
            Currencies.objects.get(id=currency)
        except Exception as e:
            logger.info(f"{e}")
            raise forms.ValidationError("Currency does not exists")

    def clean_country(self):
        try:
            country = self.cleaned_data.get('country')
            Countries.objects.get(id=country)
        except Exception as e:
            logger.info(f"{e}")
            raise forms.ValidationError("Country does not exists")
