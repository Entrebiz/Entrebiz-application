import re
import logging
from Transactions.mixins import checkNonAsciiChracters
from rest_framework import serializers
from utils.models import Accounts, Businessdetails, Countries, Currencies, Internalbeneficiaries, Externalbeneficiaries
from rest_framework.serializers import ReadOnlyField
from django.db.models import Q
logger = logging.getLogger('lessons')


class InternalbeneficySerializer(serializers.ModelSerializer):
    accountnumber = serializers.CharField(source="account.accountno")
    first_name = serializers.CharField(source="account.user_account.firstname")
    last_name = serializers.CharField(source="account.user_account.lastname")
    currency_code = ReadOnlyField(source="account.currency.code")
    slug = ReadOnlyField()
    
    def __init__(self, *args, **kwargs):
        super(InternalbeneficySerializer, self).__init__(*args, **kwargs)
        if 'context' in kwargs:
            if 'is_company' in kwargs['context']:
                is_company = kwargs['context'].get('is_company')
                if is_company:
                    self.fields.pop('last_name')
            if 'user_type' in kwargs['context']:
                user_type = kwargs['context'].get('user_type')
                if user_type == 'company' and 'last_name' in self.fields:
                    self.fields.pop('last_name')


    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.account.user_account.customer.customertype == 1:
            representation['first_name'] = instance.account.user_account.firstname
            representation['last_name'] = instance.account.user_account.lastname
            representation['is_company'] = False
        else:
            try:
                representation['first_name'] = Businessdetails.objects.get(customer=instance.account.user_account.customer).companyname
            except:
                representation['first_name'] = ""
            representation['last_name'] = ""
            representation['is_company'] = True
        return representation

    def create(self, validated_data):
        accountnumber = validated_data["account"].get('accountno')
        receivername = validated_data.get('receivername')
        user =  self.context['request'].user
        customer = user.customer_details.all()[0]
        account_obj = Accounts.objects.get(accountno=accountnumber,isdeleted=False)
        internalben_obj, created = Internalbeneficiaries.objects.get_or_create(receivername=receivername, account=account_obj, createdby=user, modifiedby=user,
                                                            customer=customer,isdeleted=False)
        return internalben_obj

    def update(self, instance, validated_data):
        instance.account = Accounts.active.get(accountno=validated_data["account"].get('accountno',instance.account.accountno))
        instance.receivername = validated_data.get('receivername',instance.receivername)
        instance.save()
        return instance
    def validate_accountnumber(self,data):
        try:
            account_obj = Accounts.active.get(accountno=data)
            user =  self.context['request'].user
        except Exception as e:
            logger.info(e)
            raise serializers.ValidationError('Account number does not exists!')
        if account_obj.createdby == user:
                raise serializers.ValidationError("Can't add own account as beneficiary!")
        if self.instance:
            if Internalbeneficiaries.objects.filter(~Q(slug=self.instance.slug), account=account_obj,
                                                    createdby=user, isdeleted=False):
                raise serializers.ValidationError('Beneficiary account already exist!')
        else:
            if Internalbeneficiaries.objects.filter(account=account_obj, createdby=user, isdeleted=False):
                raise serializers.ValidationError('Beneficiary account already exist!')
        return data
    def validate_receivername(self,data):
        user =  self.context['request'].user
        if self.instance:
            if Internalbeneficiaries.objects.filter(~Q(slug=self.instance.slug), createdby=user,
                                                                receivername=data, isdeleted=False):
                raise serializers.ValidationError('Nick name already exist!')
        elif not checkNonAsciiChracters(data):
            raise serializers.ValidationError('Fancy characters are not allowed')
        elif Internalbeneficiaries.objects.filter(createdby=user,receivername=data, isdeleted=False):
                raise serializers.ValidationError('Nick name already exist!')
        return data
    def validate(self, data):
        user =  self.context['request'].user
        first_name = data["account"]['user_account'].get('firstname')
        last_name = data["account"]['user_account'].get('lastname')
        accountnumber = data["account"].get('accountno')
        receivername = data.get('receivername')
        nick_name_check = self.context.get('nick_name_check')
        user_type = self.context.get('user_type')
        account_obj = Accounts.objects.get(accountno=accountnumber,isdeleted=False)
        try:
            customer = user.customer_details.all()[0]
        except Exception as e:
            logger.info(e)
            raise serializers.ValidationError('Customer details not found')
        user_acc = account_obj.user_account
        if user_type == "personal":
            if user_acc.customer.customertype == 2:
                raise serializers.ValidationError({'first_name': "First Name doesn't match"})
            elif  user_acc.firstname != first_name:
                raise serializers.ValidationError({'first_name': "First Name doesn't match"})
            elif not last_name or last_name == "":
                raise serializers.ValidationError({"last_name": "This field may not be blank."})
            elif user_acc.lastname != last_name:
                raise serializers.ValidationError({"last_name": "Last Name doesn't match"})
        elif user_type == "company":
            try:
                company_name = Businessdetails.objects.get(customer=user_acc.customer).companyname
            except Exception as e:
                logger.info(e)
                raise serializers.ValidationError({'first_name': "Company Name doesn't match"})
            if company_name != first_name:
                raise serializers.ValidationError({'first_name': "Company Name doesn't match"})
        if not checkNonAsciiChracters(first_name):
            raise serializers.ValidationError({"first_name": "Fancy characters are not allowed"})
        elif not checkNonAsciiChracters(last_name):
            raise serializers.ValidationError({"last_name": "Fancy characters are not allowed"})
        elif nick_name_check and Internalbeneficiaries.objects.filter(account=account_obj, createdby=user,
                                                        receivername=receivername, isdeleted=False):
            raise serializers.ValidationError({"receivername": "Nick name already exist"})
        return data

    class Meta:
        model = Internalbeneficiaries
        fields = ("slug","accountnumber","first_name","last_name","currency_code","receivername")

class ExternalbeneficiarySerializer(serializers.ModelSerializer):
    currency_code = serializers.CharField(source="currency.code")
    country_code = serializers.CharField(source="country.shortform")
    slug = ReadOnlyField()
    account_type = serializers.CharField(default="Personal")

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['country_name'] = Countries.objects.get(shortform=instance.country.shortform).name
        representation["is_country_of_external_beneficiary_deleted"] = instance.country.isdeleted
        return representation

    def create(self, validated_data):
        accountnumber = validated_data.get('accountnumber')
        name = validated_data.get('name')
        currency_code = validated_data["currency"].get('code')
        swiftcode = validated_data.get('swiftcode')
        city = validated_data.get('city')
        bankname = validated_data.get('bankname')
        country_code = validated_data["country"].get('shortform')
        email = validated_data.get('email')
        account_type = validated_data['account_type'] if validated_data.get('account_type') else "Personal"
        user =  self.context['request'].user
        customer = user.customer_details.all()[0]
        externalben_obj, created = Externalbeneficiaries.objects.get_or_create(name=name, accountnumber=accountnumber, currency=Currencies.objects.get(code=currency_code),
                                   swiftcode=swiftcode,country=Countries.objects.get(shortform=country_code),city=city,bankname=bankname,
                                   createdby=user,customer=customer,email=email,isdeleted=False, account_type=account_type)
        return externalben_obj

    def update(self, instance, validated_data):
        instance.currency = Currencies.active.get(code=validated_data["currency"].get('code',instance.currency.code))
        instance.country = Countries.objects.get(shortform=validated_data["country"].get('shortform',instance.country.shortform))
        instance.accountnumber = validated_data.get('accountnumber',instance.accountnumber)
        instance.name = validated_data.get('name',instance.name)
        instance.swiftcode = validated_data.get('swiftcode',instance.swiftcode)
        instance.city = validated_data.get('city',instance.city)
        instance.bankname = validated_data.get('bankname',instance.bankname)
        instance.account_type = validated_data.get('account_type',instance.account_type)
        instance.email = validated_data.get('email',instance.email)
        instance.save()
        return instance
    
    def validate_email(self,data):
        email_regex = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
        email = data
        if email and not re.match(email_regex, email):
            raise serializers.ValidationError("Invalid email format")
        return email
    def validate_currency_code(self,data):
        try:
            currency_code = data
            Currencies.active.get(code=currency_code)
        except Exception as e:
            logger.info(f"{e}")
            raise serializers.ValidationError("Currency does not exists")
        return currency_code
    def validate_country_code(self,data):
        try:
            shortform = data
            Countries.objects.get(shortform=shortform)
        except Exception as e:
            logger.info(f"{e}")
            raise serializers.ValidationError("Country does not exists")
        return shortform
    def validate_city(self,data):
        city = data
        if not checkNonAsciiChracters(city):
            raise serializers.ValidationError("Fancy characters are not allowed")
        return city
    def validate_swiftcode(self,data):
        swiftcode = data
        if not checkNonAsciiChracters(swiftcode):
            raise serializers.ValidationError("Fancy characters are not allowed")
        return swiftcode
    def validate_bankname(self,data):
        bankname = data
        if not checkNonAsciiChracters(bankname):
            raise serializers.ValidationError("Fancy characters are not allowed")
        return bankname
    def validate_name(self,data):
        name = data
        user =  self.context['request'].user
        customer = user.customer_details.all()[0]
        if not checkNonAsciiChracters(name):
            raise serializers.ValidationError("Fancy characters are not allowed")
        if self.instance:
            if Externalbeneficiaries.objects.filter(~Q(slug=self.instance.slug), customer=customer,
                                                                name=name, isdeleted=False):
                raise serializers.ValidationError('Beneficiary name already exist!')
        return name
    def validate_accountnumber(self,data):
        user =  self.context['request'].user
        customer = user.customer_details.all()[0]
        accountnumber = data
        if not checkNonAsciiChracters(accountnumber):
            raise serializers.ValidationError("Fancy characters are not allowed")
        if not accountnumber.isalnum():
            raise serializers.ValidationError("Special characters are not allowed")
        if self.instance:
            if Externalbeneficiaries.objects.filter(~Q(slug=self.instance.slug), customer=customer,
                                                                accountnumber=accountnumber, isdeleted=False):
                raise serializers.ValidationError('Beneficiary account already exist!')
        return accountnumber
    def validate(self, data):
        user =  self.context['request'].user
        customer = user.customer_details.all()[0]
        accountnumber = data.get('accountnumber')
        beneficiary_check = self.context.get('beneficiary_check')
        name = data.get('name')
        if beneficiary_check and Externalbeneficiaries.objects.filter(customer=customer,name=name,isdeleted=False):
            raise serializers.ValidationError({'name':'Beneficiary name already exist!'})
        elif beneficiary_check and Externalbeneficiaries.objects.filter(customer=customer,accountnumber=accountnumber,isdeleted=False):
            raise serializers.ValidationError({'accountnumber':'Beneficiary account already exist!'})
        return data

    class Meta:
        model = Externalbeneficiaries
        fields = ("slug","accountnumber","name","currency_code","swiftcode","city","bankname","country_code","email","account_type")

class AccountBeneficiarySerailizer(serializers.Serializer):
    account_number=serializers.CharField(required=True)
    nick_name=serializers.CharField(required=True)
    account_type=serializers.CharField(default = "Personal")

