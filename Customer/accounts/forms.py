import re
import logging

from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.db.models import Q
from Transactions.mixins import checkNonAsciiChracters

from utils.models import Currencies, Externalbeneficiaries, Countries, Internalbeneficiaries, Accounts, DomesticBeneficiary
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
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(ExternalBeneficiaryForm, self).__init__(*args, **kwargs)
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
    def clean_city(self):
        city = self.cleaned_data.get("city")
        if not checkNonAsciiChracters(city):
            raise forms.ValidationError("Fancy characters are not allowed")
        return city
    def clean_swiftcode(self):
        swiftcode = self.cleaned_data.get("swiftcode")
        if not checkNonAsciiChracters(swiftcode):
            raise forms.ValidationError("Fancy characters are not allowed")
        return swiftcode
    def clean_bankname(self):
        bankname = self.cleaned_data.get("bankname")
        if not checkNonAsciiChracters(bankname):
            raise forms.ValidationError("Fancy characters are not allowed")
        return bankname
    def clean_name(self):
        name = self.cleaned_data.get("name")
        user = self.request.user
        customer = user.customer_details.all()[0]
        if self.instance:
            if Externalbeneficiaries.active.filter(~Q(slug=self.instance.slug), customer=customer, name=name):
                raise forms.ValidationError('Beneficiary name already exist!')
        else:
            if Externalbeneficiaries.active.filter(customer=customer,name=name):
                raise forms.ValidationError('Beneficiary name already exist!')
        if not checkNonAsciiChracters(name):
            raise forms.ValidationError("Fancy characters are not allowed")
        return name
    def clean_accountnumber(self):
        accountnumber = self.cleaned_data.get("accountnumber")
        user = self.request.user
        customer = user.customer_details.all()[0]
        if not checkNonAsciiChracters(accountnumber):
            raise forms.ValidationError("Fancy characters are not allowed")
        if not accountnumber.isalnum():
            raise forms.ValidationError("Special characters are not allowed")
        if self.instance:
            if Externalbeneficiaries.active.filter(~Q(slug=self.instance.slug), customer=customer, accountnumber=accountnumber):
                raise forms.ValidationError('Beneficiary account already exist!')
        else:
            if Externalbeneficiaries.active.filter(customer=customer,accountnumber=accountnumber):
                raise forms.ValidationError('Beneficiary account already exist!')
        return accountnumber
    
    
class DomesticBeneficiaryForm(ModelForm):
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(DomesticBeneficiaryForm, self).__init__(*args, **kwargs)
        
    class Meta:
        model = DomesticBeneficiary
        fields = ('domestic_name',
                  'domestic_accountnumber',
                  'routing_number',
                  'domestic_city',
                  'domestic_bankname',
                  'domestic_email',
                  'country',
                  'currency'
                  )

    def clean_domestic_email(self):
        email_regex = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
        domestic_email = self.cleaned_data.get("domestic_email")
        if domestic_email and not re.match(email_regex, domestic_email):
            raise forms.ValidationError("Invalid email format")
        return domestic_email

    def clean_domestic_city(self):
        domestic_city = self.cleaned_data.get("domestic_city")
        if not checkNonAsciiChracters(domestic_city):
            raise forms.ValidationError("Fancy characters are not allowed")
        return domestic_city
    def clean_routing_number(self):
        routing_number = self.cleaned_data.get("routing_number")
        if not checkNonAsciiChracters(routing_number):
            raise forms.ValidationError("Fancy characters are not allowed")
        return routing_number
    def clean_domestic_bankname(self):
        domestic_bankname = self.cleaned_data.get("domestic_bankname")
        if not checkNonAsciiChracters(domestic_bankname):
            raise forms.ValidationError("Fancy characters are not allowed")
        return domestic_bankname
    def clean_domestic_name(self):
        domestic_bankname = self.cleaned_data.get("domestic_bankname")
        domestic_name = self.cleaned_data.get("domestic_name")
        user = self.request.user
        customer = user.customer_details.all()[0]
        if self.instance:
            if DomesticBeneficiary.active.filter(~Q(slug=self.instance.slug), customer=customer, domestic_name=domestic_name):
                raise forms.ValidationError('Beneficiary name already exist!')
        else:
            if DomesticBeneficiary.active.filter(customer=customer,domestic_name=domestic_name):
                raise forms.ValidationError('Beneficiary name already exist!')
        if not checkNonAsciiChracters(domestic_name):
            raise forms.ValidationError("Fancy characters are not allowed")
        return domestic_name
    def clean_domestic_accountnumber(self):
        domestic_accountnumber = self.cleaned_data.get("domestic_accountnumber")
        user = self.request.user
        customer = user.customer_details.all()[0]
        if not checkNonAsciiChracters(domestic_accountnumber):
            raise forms.ValidationError("Fancy characters are not allowed")
        if not domestic_accountnumber.isalnum():
            raise forms.ValidationError("Special characters are not allowed")
        if self.instance:
            if DomesticBeneficiary.active.filter(~Q(slug=self.instance.slug), customer=customer, domestic_accountnumber=domestic_accountnumber):
                raise forms.ValidationError('Beneficiary account already exist!')
        else:
            if DomesticBeneficiary.active.filter(customer=customer,domestic_accountnumber=domestic_accountnumber):
                raise forms.ValidationError('Beneficiary account already exist!')
        return domestic_accountnumber
