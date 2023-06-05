from asyncore import read
import datetime
import re

from rest_framework import serializers
from utils.models import Accounts

from Transactions.mixins import checkNonAsciiChracters
import logging
from django.conf import settings

logger = logging.getLogger('lessons')






class AccountToAccountApiSerilaizer(serializers.ModelSerializer):
    beneficiary_account=serializers.CharField(required=True)
    debit_account=serializers.CharField(required=True)
    amount=serializers.CharField(required=True)


    class Meta:
        model = Accounts
        fields = ('beneficiary_account','debit_account','amount','balance')

    def validate_amount(self,data):
        amount =data
        try:
            float(amount)
        except:
            raise serializers.ValidationError("Amount should be a number")
        if float(amount) <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return data

    def validate_beneficiary_account(self,data):
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
            raise serializers.ValidationError("Invalid beneficiary account!")
        return accountnumber
    def validate_debit_account(self,data):
        debit_account=data
        try:
            Accounts.objects.get(accountno=debit_account, isdeleted=False)
        except Exception as e:
            logger.info(e)
            raise serializers.ValidationError('Invalid debit account!')
        return data