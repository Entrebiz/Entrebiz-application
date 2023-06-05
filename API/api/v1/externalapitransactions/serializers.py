from rest_framework import serializers
from Transactions.mixins import ModelQueries
from utils.models import Transactions
import math
from decimal import Decimal



class ExternalTransactionAPISerializer(serializers.Serializer):
    accountno=serializers.CharField(required=True)


class TrasactionsAPISerializer(serializers.ModelSerializer, ModelQueries):
    class Meta:
        model = Transactions
        fields = ["id"]

    def is_negative_balance(self, balance):
        if Decimal(balance) < 0:
            return '-' + str(balance)
        else:
            return str(balance)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context["request"]
        account = self.context["account"]
        debitcredit_amount = self.get_debitcredit_amount(instance, account.accountno)
        balance_amount = self.get_balance_amount(instance)
        is_debit_or_credit = False

        if self.is_debit_or_credit(instance, account.accountno) == 'credit':
            is_debit_or_credit = True
            amount = f'{debitcredit_amount} {account.currency.code}'
            balance = f'{format(math.ceil(instance.toaccountbalance * 100) / 100, ".2f")} {account.currency.code}'
            tr_balance = instance.toaccountbalance
        else:
            amount = f'{debitcredit_amount} {account.currency.code}'
            balance = f'{balance_amount} {account.currency.code}'
            tr_balance = balance_amount
        if representation['id']:
            representation.pop('id')
        representation["transaction_details"] = {
            "transaction_no": instance.transactionno,
            'date':instance.createdon.strftime("%b %d %Y"),
            "transaction_type":f"{self.get_transaction_type(instance)} {'(Cr)' if is_debit_or_credit else '(Dr)'}",
            "beneficiary_name": self.get_beneficiary(instance).get('name'),
            "reference_note": self.get_reference(instance),
            'amount':amount,
            "is_credit":is_debit_or_credit,
            "balance":f"{self.is_negative_balance(tr_balance)}-{account.currency.code}",
            "closing_balance":f"{round(account.balance, 2)}-{(account.currency.code)}",
        }
        return representation