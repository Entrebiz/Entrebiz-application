from asyncore import read
import datetime
import re
import os
from unittest.util import _MAX_LENGTH
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils import timezone

from Transactions.mixins import ConfirmYourMail, checkNonAsciiChracters
from rest_framework import serializers, exceptions, status
from utils.models import Accounts, Currencies,\
Businessdetails,Countries, Industrytypes, Stripe_Customer, Transactionpurposetype, Useraccounts, Otps, Activitylog, Customers, Transactiontypes, Transactions, Incomingtracepayment, \
    Internationaltransactions, Bankdetail
from Transactions.mixins import checkNonAsciiChracters
import logging
from django.conf import settings

logger = logging.getLogger('lessons')



class UserAuthenticateSerializer(serializers.Serializer):
    email = serializers.CharField(allow_blank=True, allow_null=True)
    password = serializers.CharField(allow_blank=True, allow_null=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        if email and password:
            try:
                user = User.objects.get(email=email)
            except Exception as e:
                logger.info(e)
                message = 'Incorrect email or password'
                exc_resp = {
                    'message': message,
                }
                raise exceptions.AuthenticationFailed(exc_resp)
            if user.check_password(password):
                user_account = Useraccounts.objects.get(customer__user=user, isdeleted=False)
                now = timezone.now()
                if user_account.account_locked_for and now < user_account.account_locked_for:
                    message = "Your account has been locked out for 24 hours due to multiple failed login attempts."
                    exc_resp = {
                        'message': message,
                    }
                    raise exceptions.AuthenticationFailed(exc_resp)
            else:
                user_account = Useraccounts.active.get(customer__user=user)
                user_account.logintrycount += 0 if user_account.logintrycount > 3 else 1
                user_account.save()
                if user_account.logintrycount >= 3:
                    message = "Your account has been locked out for 24 hours due to multiple failed login attempts."
                    if not user_account.account_locked_for:
                        user_account.account_locked_for = datetime.datetime.now() + datetime.timedelta(hours=24)
                        user_account.save()
                else:
                    message = 'Incorrect email or password'
                exc_resp = {
                    'message': message,
                }
                raise exceptions.AuthenticationFailed(exc_resp)
            username = user.username

            user = authenticate(username=username, password=password)

            if user:
                if not user.is_active:
                    message = 'User account is disabled.'
                    exc_msg = {
                        'message': message,
                    }
                    raise exceptions.AuthenticationFailed(exc_msg)
                try:
                    useraccount = Useraccounts.objects.get(customer__user=user)
                    useraccount.account_locked_for = None
                    useraccount.logintrycount = 0
                    useraccount.save()
                except:
                    message = 'Customer account not found'
                    exc_msg = {
                        'message': message,
                    }
                    raise exceptions.NotFound(exc_msg)

                message = None
                status = None
                if useraccount.activestatus.lower() == "deactivated by ubo":
                    message = "Account is deactivated by UBO."
                    status = 2
                elif useraccount.activestatus.lower() == "suspended":
                    message = "Your account is suspended, please contact support@entrebiz-pte.com"
                    status = 3
                elif useraccount.activestatus.lower() == "rejected":
                    message = "Your account is rejected, please contact support@entrebiz-pte.com"
                    status = 4
                elif useraccount.islocked:
                    message = "Your account is locked, please contact support@entrebiz-pte.com"
                    status = 5
                if message and status:
                    exc_resp = {
                        'status' : status,
                        'message' : message,
                        'is_auth' : True
                    }
                    raise exceptions.AuthenticationFailed(exc_resp)
            else:
                message = 'Unable to log in with provided credentials.'
                exc_resp = {
                    'message': message,
                }
                raise exceptions.AuthenticationFailed(exc_resp)

        else:
            message = 'email and password fields are required'
            exc_resp = {
                'message': message,
            }
            exception = exceptions.APIException(exc_resp)
            exception.status_code = status.HTTP_400_BAD_REQUEST  # to override status code 500 to 400
            raise exception

        attrs['user'] = user
        return attrs


class AccountListsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Accounts
        fields = "__all__"


class CurrenciesListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Currencies
        fields = "__all__"


class CountriesListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Countries
        fields = "__all__"


class TranscationPurposeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transactionpurposetype
        fields = "__all__"
        

class EditOTPmethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Useraccounts
        fields = ('otptype')

class ChangePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(required=True,error_messages = {"blank": "Current Password is required."})
    new_password = serializers.CharField(required=True,error_messages = {"blank": "New Password is required."})
    otp=serializers.CharField(required=True,error_messages = {"blank": "This field is required."})
    confirmpassword=serializers.CharField(required=True,error_messages = {"blank": "Re Enter New Password is required."})
    
    def save(self, **kwargs):
        password = self.validated_data['new_password']
        user = self.context['request'].user
        user.set_password(password)
        user.save()
        return user
    class Meta:
        model=Useraccounts
        fields=['password','new_password','otp','confirmpassword']
   
class TwoFactUserAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model=Useraccounts
        fields=['twofactorauth']


class OtpsSerializer(serializers.ModelSerializer):
    class Meta:
        modal=Otps
        fields = "__all__"

class ActivitylogSerializer(serializers.ModelSerializer):
    class Meta:
        modal=Activitylog
        fields = "__all__"

class MobileOTPmethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Useraccounts
        fields = ['phoneverified']


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model=Customers
        fields="__all__"

class PersonalDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model=Useraccounts
        fields=['id','firstname','middlename','lastname','phonenumber','dateofbirth','street_address','city','region','country','nationality','zipcode','countrycode']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['country'] = instance.country.name if instance.country else None
        representation['country_id'] = instance.country.id if instance.country else None
        representation['nationality'] = instance.nationality.name if instance.nationality else None
        representation['nationality_id'] = instance.nationality.id if instance.nationality else None
        return representation


class UserDetailsSerializer(serializers.ModelSerializer):
    street_address = serializers.CharField(required=True)
    city=serializers.CharField(required=True)
    region=serializers.CharField(required=True)
    zipcode=serializers.CharField(required=True)
    phonenumber=serializers.CharField(required=True)
    class Meta:
        model = Useraccounts
        fields = ('street_address',
                  'city',
                  'region',
                  'zipcode',
                  'phonenumber',
                  'countrycode',
                  'country',
                  )

    def validate_countrycode(self, attrs):
        countrycode=attrs
        if not countrycode:
            raise serializers.ValidationError('This filed is required')
        return attrs
    def validate_zipcode(self,attrs):
        zipcode=attrs
        if not zipcode:
            raise serializers.ValidationError("This field is required.")
        return attrs
    def validate_street_address(self,attrs):
        street_address = attrs
        if not checkNonAsciiChracters(street_address):
            raise serializers.ValidationError("Fancy characters are not allowed")
        elif not street_address:
            raise serializers.ValidationError("This field is required.")
        return attrs
    def validate_city(self,attrs):
        city = attrs
        if not checkNonAsciiChracters(city):
            raise serializers.ValidationError("Fancy characters are not allowed")
        elif not city:
            raise serializers.ValidationError("This field is required.")
        return attrs
    def validate_region(self,attrs):
        region =attrs
        if not checkNonAsciiChracters(region):
            raise serializers.ValidationError("Fancy characters are not allowed")
        elif not region:
            raise serializers.ValidationError("This field is required.")
        return attrs
    def validate_phonenumber(self,attrs):
        phonenumber = attrs
        if phonenumber and not phonenumber.isdigit():
            raise serializers.ValidationError("Phone number must be numbers only")
        if not phonenumber:
            raise serializers.ValidationError("This field is required.")
        try:
            if phonenumber and not phonenumber.isalpha():
                min_length = 3
                max_length = 15
                ph_length = str(phonenumber)
                if len(ph_length) < min_length or len(ph_length) > max_length:
                    raise serializers.ValidationError('Phone number must be a valid number')
        except (ValueError, TypeError):
            raise serializers.ValidationError('Please enter a valid phone number')
        return attrs
    def validate_country(self,data):
        country = data
        if not country:
            raise serializers.ValidationError("Please enter a valid country field")
        return country

class CountryNameSerializer(serializers.ModelSerializer):

    class Meta:
        model = Countries
        fields = ['name']


class CurrencyConversionSerializer(serializers.ModelSerializer):
    debit_account = serializers.CharField(required=True)
    credit_account = serializers.CharField(required=True)
    debit_acc_curr_code = serializers.CharField(source="debit_account.currency.code",required=True)
    net_amount = serializers.DecimalField(max_digits=18, decimal_places=4,required=True)
    note = serializers.CharField(max_length=1000,required=False, allow_null=True,allow_blank=True)
    otp =serializers.CharField(required=True,error_messages = {"blank": "This field is required."})
    transaction_no=serializers.CharField(max_length=20,required=True)
    
    def __init__(self, *args, **kwargs):
        super(CurrencyConversionSerializer, self).__init__(*args, **kwargs)
        if 'context' in kwargs:
            if 'email_send' in kwargs['context']:
                is_type = kwargs['context'].get('email_send')
                if is_type:
                    self.fields.pop('credit_account')
                    self.fields.pop('note')
                    self.fields.pop('otp')
                    self.fields.pop('debit_account')
                    self.fields.pop('net_amount')
                    self.fields.pop('debit_acc_curr_code')

            elif 'currencyconversion' in kwargs['context']:
                is_type = kwargs['context'].get('currencyconversion')
                if is_type:
                    self.fields.pop('debit_acc_curr_code')
                    self.fields.pop('otp')
                    self.fields.pop('transaction_no')
            elif 'otpvalidate' in kwargs['context']:
                is_type = kwargs['context'].get('otpvalidate')
                if is_type:
                    self.fields.pop('debit_acc_curr_code')
                    self.fields.pop('note')
                    self.fields.pop('transaction_no')
          
                               
         
    def validate(self,data,**kwargs):
        if not self.context.get('email_send'):
            debit_account_balance = Accounts.objects.get(accountno=int(data["debit_account"])).balance
            if data['debit_account']==data['credit_account']:
                message="Both accounts cannot be the same!"
                raise serializers.ValidationError({'credit_account':message})
            if data['net_amount'] > debit_account_balance: 
                message="Insufficient Balance"
                raise serializers.ValidationError({'net_amount':message})
            if data['net_amount'] == 0:
                message="amount must be greater than 0"
                raise serializers.ValidationError({'net_amount':message})
            if not checkNonAsciiChracters(data.get('note')):
                message="Fancy Characters are not allowed"
                raise serializers.ValidationError({'note':message}) 
        if self.context.get('email_send'):
            if not data.get('transaction_no'):
                message="Invalid transcation number"
                raise serializers.ValidationError({'transaction_no':message}) 



        return data
    class Meta:
        model=Transactions
        fields = ('debit_account', 'credit_account', 'net_amount','note', 'debit_acc_curr_code','otp','transaction_no')


class ForgotPasswordSerializer(serializers.Serializer,ConfirmYourMail):
    email = serializers.EmailField()

    def validate(self, data):
        email = data.get('email')
        if not Useraccounts.objects.filter(customer__user__email=email, isdeleted=False).exists():
            raise serializers.ValidationError({"email": "Email does not exist"})
        return data

    def save(self):
        email = self.validated_data['email']
        try:
            user = User.objects.get(email=email)
            user_account = Useraccounts.objects.get(customer__user=user, isdeleted=False)
            full_name = f"{user_account.firstname} {user_account.lastname}"
            mail_status = self.send_confirm_mail(full_name, email,createdby=user,transaction_type=2, dev_type=1)
        except Exception as e:
            logger.info(f"{e}")
            exc_resp = {
                    'message': 'Error Occured',
                }
            exception = exceptions.APIException(exc_resp)
            exception.status_code = status.HTTP_200_OK
            raise exception


class AccountToAccountSerilaizer(serializers.ModelSerializer):
    beneficiary_accountnumber=serializers.CharField(required=True)
    debit_account=serializers.CharField(required=True)
    amount=serializers.CharField(required=True)


    class Meta:
        model = Accounts
        fields = ('beneficiary_accountnumber','debit_account','amount','balance')

    def validate_amount(self,data):
        amount =data
        try:
            float(amount)
        except:
            raise serializers.ValidationError("Amount should be a number")
        if float(amount) <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return data

    def validate_beneficiary_accountnumber(self,data):
        accountnumber = data
        if not accountnumber:
            raise serializers.ValidationError("This field may not be blank.")
        elif not checkNonAsciiChracters(accountnumber):
            raise serializers.ValidationError("Fancy characters are not allowed")
        elif not accountnumber.isalnum():
            raise serializers.ValidationError("Special characters not allowed.")
        try:
            Accounts.objects.get(accountno=accountnumber, isdeleted=False)
        except Exception as e:
            raise serializers.ValidationError("Invalid credit account!")
        return accountnumber
    def validate_debit_account(self,data):
        debit_account=data
        try:
            Accounts.objects.get(accountno=debit_account, isdeleted=False)
        except Exception as e:
            logger.info(e)
            raise serializers.ValidationError('Invalid debit account!')
        return data

class AccountToAccountValidateSerilaizer(serializers.ModelSerializer):
    beneficiary_accountnumber = serializers.CharField(required=True)
    debit_account_number = serializers.CharField(required=True)
    net_amount = serializers.CharField(required=True)
    conversion_fee=serializers.CharField(required=True)
    credit_amount=serializers.CharField(required=True)
    otp=serializers.CharField(required=True)


    class Meta:
        model=Accounts
        fields=('accountno','currency','beneficiary_accountnumber','debit_account_number','net_amount','conversion_fee','credit_amount','otp')

class AccountToAccountEmailSerializer(serializers.Serializer):

    transaction_number=serializers.CharField(required=True)

class InternationalWireTransferSerializer(serializers.Serializer):
    debit_account = serializers.CharField(required=True)
    debit_acc_curr_code=serializers.CharField(required=True)
    beneficiary_account = serializers.CharField(required=True)
    beneficiaryname = serializers.CharField(required=True)
    debit_amount = serializers.DecimalField(max_digits=18, decimal_places=4,required=True)
    bankname = serializers.CharField(required=True)
    swiftcode = serializers.CharField(required=True)
    city = serializers.CharField(required=True)
    country = serializers.CharField(required=True)
    otp = serializers.CharField(required=True,error_messages = {"blank": "This field is required."})
    Currency = serializers.CharField(required=True)
    user_box_no = serializers.CharField(required=True,error_messages = {"blank": "This field is required."})
    user_street = serializers.CharField(required=True,error_messages = {"blank": "This field is required."})
    user_city = serializers.CharField(required=True,error_messages = {"blank": "This field is required."})
    user_state = serializers.CharField(required=True,error_messages = {"blank": "This field is required."})
    user_country = serializers.CharField(required=True)
    user_phone = serializers.RegexField(required=True,regex = r"^\+{0,1}[0-9]{10,13}")
    purpose = serializers.CharField(required=True) 
    note = serializers.CharField(max_length=1000,required=False, allow_null=True,allow_blank=True)
    email = serializers.EmailField(max_length=100,required=False, allow_null=True,allow_blank=True)
    purpose_note = serializers.CharField(max_length=1000,required=False, allow_null=True,allow_blank=True)
    invoice_doc=serializers.FileField(required=False)
    has_invoice=serializers.CharField()


    

    def __init__(self, *args, **kwargs):
        super(InternationalWireTransferSerializer, self).__init__(*args, **kwargs)
        data = dict(kwargs['data'])
        if 'context' in kwargs:
            if 'otp_validate' in kwargs['context']:
                is_type = kwargs['context'].get('otp_validate')
                if is_type:
                    self.fields.pop('debit_acc_curr_code')
            elif 'email_send' in kwargs['context']:
                is_type = kwargs['context'].get('email_send')
                if is_type:
                    self.fields.pop('debit_acc_curr_code')
                    self.fields.pop('debit_account')
                    self.fields.pop('beneficiary_account')
                    self.fields.pop('Currency')
                    self.fields.pop('bankname')
                    self.fields.pop('swiftcode')
                    self.fields.pop('email')
                    self.fields.pop('user_phone')
                    self.fields.pop('note')
                    self.fields.pop('city')
                    self.fields.pop('user_street')
                    self.fields.pop('debit_amount')
                    self.fields.pop('purpose')
                    self.fields.pop('user_state')
                    self.fields.pop('user_box_no')
                    self.fields.pop('country')
                    self.fields.pop('beneficiaryname')
                    self.fields.pop('user_country')
                    self.fields.pop('user_city')
                    self.fields.pop('purpose_note')
                    self.fields.pop('otp')


                   
            elif 'InternationalWireTransfer' in kwargs['context']:
                is_type = kwargs['context'].get('InternationalWireTransfer')
                if is_type:
                    self.fields.pop('debit_acc_curr_code')
                    self.fields.pop('otp')
        if 'ownaccount' in data:
            if data['ownaccount'][0] == '1':
                self.fields.pop('user_country')
                self.fields.pop('user_city')
                self.fields.pop('user_street')
                self.fields.pop('user_state')
                self.fields.pop('user_box_no')
                self.fields.pop('user_phone')   
               

    def validate(self,data,**kwargs):
        if not self.context.get('email_send'):
           
            if data['debit_account']==data['beneficiary_account']:
                message="Both accounts cannot be the same!"
                raise serializers.ValidationError({'debit_account':message})
            if not checkNonAsciiChracters(data.get('note')):
                message="Fancy Characters are not allowed"
                raise serializers.ValidationError({'note':message}) 
            if data['purpose']=='Other Remittance' and 'purpose_note' not in dict(data):
                message="This field is required"
                raise serializers.ValidationError({'purpose_note':message}) 
            if data['purpose']=='Other Remittance' and data['purpose_note'] == '':
                message="This field may not be blank."
                raise serializers.ValidationError({'purpose_note':message}) 
            if data['purpose']!='Other Remittance':
                if 'purpose_note' in data:
                    message="This field  not required"
                    raise serializers.ValidationError({'purpose_note':message}) 
            if data['beneficiary_account'].isalnum() == False:
                message="only alphanumeric characters are allowed"
                raise serializers.ValidationError({'beneficiary_account':message})
            if data['debit_account']:
                account_exist= Accounts.objects.filter(accountno=data['debit_account']).exists()
                if not account_exist:
                    raise serializers.ValidationError({'debit_account':"The account not exists"})
            if data['has_invoice']=='1':
                if 'invoice_doc' not in data:
                    message= "This field is required."
                    raise serializers.ValidationError({'invoice_doc':message}) 
            if data['has_invoice']=='0':
                if 'invoice_doc'  in data:
                    message= "This field not required."
                    raise serializers.ValidationError({'invoice_doc':message}) 



        return data


    class Meta:
        model=Internationaltransactions

        fields = ('debit_account','beneficiary_account','otp','beneficiaryname','debit_amount','bankname','swiftcode','city','country','Currency','user_box_no','user_street','user_city','user_state','user_country','user_phone','purpose','note','email','debit_acc_curr_code','purpose_note','invoice_doc','has_invoice','transactionno')   
 
class InwardRemittanceSerializer(serializers.Serializer):
    bank_id=serializers.CharField(required=True)
    account_id=serializers.CharField(required=True)
    amount=serializers.CharField(required=True)
    sender_acc_number=serializers.CharField(required=False)
    invoice_doc=serializers.FileField(required=False)
    sender_name=serializers.CharField(required=False)
    sender_bank_name=serializers.CharField(required=False)
    sender_country=serializers.CharField(required=False)
    swift_code=serializers.CharField(required=False)
    reference=serializers.CharField(required=False)

    def validate_sender_acc_number(self, data):
        sender_acc_number=data
        if sender_acc_number and not sender_acc_number.isalnum():
            raise serializers.ValidationError('Special characters not allowed.')
        elif not checkNonAsciiChracters(sender_acc_number):
            raise serializers.ValidationError('Fancy characters not allowed')
        return sender_acc_number

    def validate_invoice_doc(self, data):
        invoice_doc=data
        if invoice_doc:
            ext = os.path.splitext(invoice_doc.name)[1]
            filesize = invoice_doc.size
            if not ext in settings.ALLOWED_FORMATS:
                raise serializers.ValidationError('Incorrect file format')
            elif filesize > settings.MAX_FILE_SIZE:
                raise serializers.ValidationError('Maximum file size allowed is 10 MB')
            elif not all(ord(c) < 128 for c in invoice_doc.name):
                raise serializers.ValidationError('Special characters should not be in file name')
        return invoice_doc

    def validate_sender_name(self, data):
        sender_name=data
        if not checkNonAsciiChracters(sender_name):
            raise serializers.ValidationError('Fancy characters not allowed')
        return data

    def validate_sender_bank_name(self, attrs):
        sender_bank_name = attrs
        if not checkNonAsciiChracters(sender_bank_name):
            raise serializers.ValidationError('Fancy characters not allowed')
        return attrs

    def validate_sender_country(self, attrs):
        sender_country = attrs
        if not checkNonAsciiChracters(sender_country):
            raise serializers.ValidationError('Fancy characters not allowed')
        return attrs

    def validate_swift_code(self, attrs):
        swift_code = attrs
        if not checkNonAsciiChracters(swift_code):
            raise serializers.ValidationError('Fancy characters not allowed')
        return attrs

    def validate_reference(self, attrs):
        reference = attrs
        if not checkNonAsciiChracters(reference):
            raise serializers.ValidationError('Fancy characters not allowed')
        return attrs


class InwardAccountSerializer(serializers.Serializer):

    account_id=serializers.CharField(required=True)


class BankdetailSerializer(serializers.ModelSerializer):
    class Meta:
        model=Bankdetail
        fields="__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['currency'] = instance.currency.name
        representation['country'] = instance.country.name
        representation['reference'] = instance.reference if instance.reference else ''
        return representation

  
class ReferfrndSerializer(serializers.Serializer):
    firstname= serializers.CharField(required= True)
    lastname= serializers.CharField(required= True)
    email= serializers.CharField(required= True)
    
    
    def validate(self, attrs):
        firstName= attrs.get("firstname")
        lastName= attrs.get("lastname")
        email_regex= r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email= attrs.get('email')
        if email and not re.search(email_regex, email):
            raise serializers.ValidationError({"email":"Invalid Email format"})

        elif not checkNonAsciiChracters([firstName,lastName]):
            raise serializers.ValidationError("Fancy Charecters are not allowed")
        return attrs


class CompanyPermissionSerializer(serializers.ModelSerializer):
    firstname = serializers.CharField(required=True, error_messages={"blank": "This field is required."})
    lastname = serializers.CharField(required=True, error_messages={"blank": "This field is required."})
    middlename = serializers.CharField(required=False)
    emailaddress = serializers.EmailField(required=True, error_messages={"blank": "This field is required."})
    class Meta:
        model=Businessdetails
        fields =('firstname','lastname','middlename','emailaddress')



class UpdateCurrencyStatusSerializer(serializers.Serializer):

    acc_id=serializers.CharField(required=True)
    acc_status=serializers.CharField(required=True)


def checkNonAsciiChracters(input_field):
    if input_field and isinstance(input_field, list):
        if not all(ord(ch) < 128  for input in input_field for ch in input):
            return False
    elif input_field and not all(ord(c) < 128 for c in input_field):
        return False
    return True


class ReportMissingSerializer(serializers.ModelSerializer):

    class Meta:
        model= Incomingtracepayment
        fields= ['sendername', 'senderbank', 'senderaccountno', 'amount', 'bookingdate', 'paymentattachment', 'currency', 'reference']
    
        extra_kwargs = {
            'currency': {'required': True},            
            }
        
    def validate(self, attrs):
        if attrs.get('paymentattachment'):
            filename ,size= attrs.get('paymentattachment'),attrs.get('paymentattachment').size
            formatname= str(filename).split(".")[1]
            if size > settings.MAX_FILE_SIZE:
                raise serializers.ValidationError({'paymentattachment': "Maximum file size allowed is 10 MB"})
            elif "."+formatname not in settings.ALLOWED_FORMATS:
                raise serializers.ValidationError({'paymentattachment': "File format is not acceptable"})
            elif not all(ord(c) < 128 for c in str(filename)):
                raise serializers.ValidationError({'paymentattachment': "Special characters should not be in file name"})
        if attrs.get('sendername'):
            if not checkNonAsciiChracters([attrs.get('sendername')]):
                raise serializers.ValidationError({'sendername': "Fancy characters are not allowed"})
        if attrs.get('senderbank'):
            if not checkNonAsciiChracters([attrs.get('senderbank')]):
               raise serializers.ValidationError({'senderbank': "Fancy characters are not allowed"})
        if attrs.get('senderaccountno'):
            if not checkNonAsciiChracters([attrs.get('senderaccountno')]):
                raise serializers.ValidationError({'senderaccountno': "Fancy characters are not allowed"})
        if attrs.get('reference'):
            if not checkNonAsciiChracters([attrs.get('reference')]):
                raise serializers.ValidationError({'reference': "Fancy characters are not allowed"})
        if attrs.get('senderaccountno'):
            if not attrs.get('senderaccountno').isalnum():
                raise serializers.ValidationError({'senderaccountno': "Account number should not contain any special characters"})
        
        return attrs


class ReportMissingSerializerList(serializers.ModelSerializer):
    class Meta:
        model= Incomingtracepayment
        fields= ['id','sendername', 'senderaccountno', 'senderbank','currency', 'amount', 'status']
        
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.currency.code == '':
            representation['currency'] = None
        else:
            representation['currency'] = instance.currency.code
        if instance.amount == '':
            representation['amount'] = None
        else:
            representation['amount'] = str(round(instance.amount, 2))
        if instance.sendername == '':
            representation['sendername'] = None
        if instance.senderaccountno == '':
            representation['senderaccountno'] = None
        if instance.senderbank == '':
            representation['senderbank'] = None
        return representation
    
class IndustrytypesSerializer(serializers.ModelSerializer):
    class Meta:
        model= Industrytypes
        fields= ["id", "name", "description"]
 
class OTPVerifyPersonalDetailSerializer(serializers.Serializer):
    otp=serializers.CharField(required=True)

class TwoStepVerificationSerializer(serializers.Serializer):
    otp=serializers.CharField(required=True)
    
class ImageUploadSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(error_messages={"invalid_image": "Incorrect image format."})

    class Meta:
        model = Useraccounts
        fields = ["image"]
        
    def validate_image(self, data):
        image = data
        if image:
            ext = os.path.splitext(image.name)[1]
            if not ext in settings.ALLOWED_FORMATS:
                raise serializers.ValidationError(
                    {"message": "Incorrect image format"}
                    )
            elif image.size > settings.MAX_FILE_SIZE:
                raise serializers.ValidationError(
                     {"message": "Maximum image size allowed is 10 MB"}
                )
            elif not all(ord(c) < 128 for c in image.name):
                raise serializers.ValidationError(
                    {"message": "Special characters should not be in image name"}
                )
        else:
            raise serializers.ValidationError(
                {"message": "Invalid file"}
                )
        return data


class GetaccountSerializer(serializers.ModelSerializer):
    
    class Meta:
        model=Accounts
        

class CheckoutSerializer(serializers.ModelSerializer):
    card_number = serializers.IntegerField(required = True,error_messages = {"invalid": "This field is required."})
    exp_month = serializers.IntegerField(required = True,error_messages = {"invalid": "This field is required."})
    exp_year = serializers.IntegerField(required = True,error_messages = {"invalid": "This field is required."})
    cvc = serializers.IntegerField(required = True,error_messages = {"invalid": "This field is required."})
    amount = serializers.IntegerField(required = True,error_messages = {"invalid": "This field is required."})
    currency = serializers.CharField(required = True,error_messages = {"blank": "This field is required."})
    email=serializers.CharField(required = True,error_messages = {"blank": "This field is required."})
    class Meta:
        model = Stripe_Customer
        fields = ('card_number','exp_month','exp_year','cvc','email','customer_id','token_id','amount','currency')
        





