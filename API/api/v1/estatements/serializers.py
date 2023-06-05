import math
from decimal import Decimal
from Transactions.mixins import ModelQueries
from rest_framework import serializers
from utils.models import Businessdetails, Transactions


class TrasactionsSerializer(serializers.ModelSerializer,ModelQueries):
    class Meta:
        model = Transactions
        fields = ["id"]
        
    def is_negative_balance(self, balance):
        if Decimal(balance) < 0:
            return True
        else:
            return False
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context["request"]
        account = self.context["account"]
        debitcredit_amount = self.get_debitcredit_amount(instance,account.accountno)
        balance_amount = self.get_balance_amount(instance)
        is_debit_or_credit = False
        
        if self.is_debit_or_credit(instance,account.accountno) == 'credit':
            is_debit_or_credit = True
            amount = f'+{debitcredit_amount} {account.currency.code}'
            balance = f'{format(math.ceil(instance.toaccountbalance*100)/100,".2f")} {account.currency.code}'
            tr_balance = instance.toaccountbalance
        else:
            amount = f'-{debitcredit_amount} {account.currency.code}'
            balance = f'{balance_amount} {account.currency.code}'
            tr_balance = balance_amount
        representation["Date"] = instance.createdon.strftime("%b %d %Y")
        representation["Type"] = f"{self.get_transaction_type(instance)} {'(Cr)' if is_debit_or_credit else '(Dr)'}"
        representation["Details"] = {
            "Transaction No": instance.transactionno,
            "Beneficiary Name": self.get_beneficiary(instance).get('name'),
            "Ref": self.get_reference(instance)
        }
        representation["Amount"] = amount
        representation["is_credit"] = is_debit_or_credit
        representation["Balance"] = balance
        representation["is_negative_balance"] = self.is_negative_balance(tr_balance)
        representation["Action"] = self.enable_view_action(instance, request)
        representation["Closing Balance"] = f"{round(account.balance, 2)} {(account.currency.code)}"
        return representation
    
    
class TrasactionDetailsSerializer(serializers.ModelSerializer,ModelQueries):
    class Meta:
        model = Transactions
        fields = ["id"]
        
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        transaction_amounts = self.get_transaction_amounts(instance,from_amount=True)
        if instance.fromaccount.user_account.customer.customertype == 1:
            full_name = instance.fromaccount.user_account.fullname
        else:
            full_name = Businessdetails.objects.get(customer__user=instance.fromaccount.user_account.customer.user, isdeleted=False).companyname
        if instance.transactiontype.name == 'Third Party Transfer':
            transaction_details = {
            "Transaction Type" : "International Transfer",
            "Transaction No" : instance.transactionno,
            "Date and Time" : instance.createdon.strftime("%d %b %Y, %-H:%M UTC"),
            "Sender Name" : full_name,
            "Debit Account" : f"{instance.fromaccount.accountno} {instance.fromaccount.currency.code}",
            "Credit Account" : instance.inltransaction_tr.all()[0].accountnumber,
            "Beneficiary Name" : instance.inltransaction_tr.all()[0].accountholdername,
            "Currency" : instance.inltransaction_tr.all()[0].currency.code,
            "Bank Name" : instance.inltransaction_tr.all()[0].bankname,
            "Bank SWIFT Code" : instance.inltransaction_tr.all()[0].swiftcode,
            "Bank City" : instance.inltransaction_tr.all()[0].city,
            "Bank Country" : instance.inltransaction_tr.all()[0].country.shortform,
            "Purpose of remittance" : instance.inltransaction_tr.all()[0].purpose.transactionpurpose,
            "Purpose note" : instance.inltransaction_tr.all()[0].other_purpose_note if instance.inltransaction_tr.all()[0].purpose.transactionpurpose == 'Other Remittance' else None,
            "Beneficiary Email" : instance.inltransaction_tr.all()[0].email if instance.inltransaction_tr.all()[0].email else None,
            "Box No." : instance.inltransaction_tr.all()[0].user_box_no if instance.inltransaction_tr.all()[0].user_box_no else None,
            "Street" : instance.inltransaction_tr.all()[0].user_street if instance.inltransaction_tr.all()[0].user_street else None,
            "City" : instance.inltransaction_tr.all()[0].user_city if instance.inltransaction_tr.all()[0].user_city else None,
            "State" : instance.inltransaction_tr.all()[0].user_state if instance.inltransaction_tr.all()[0].user_state else None,
            "User Country" : instance.inltransaction_tr.all()[0].user_country.shortform if instance.inltransaction_tr.all()[0].user_country else None,
            "Tel/Mob No." : instance.inltransaction_tr.all()[0].user_phone if instance.inltransaction_tr.all()[0].user_phone else None,
            "Invoice" : self.get_transaction_receipt(instance),
            "Net Amount" : f'{transaction_amounts.get("net_amount")} {instance.fromaccount.currency.code}',
            "Conversion Fee" : f'{transaction_amounts.get("conversion_fee")} {instance.fromaccount.currency.code}',
            "Wire Transfer Fee" : f'{transaction_amounts.get("wire_fee")} {instance.fromaccount.currency.code}',
            "Cable Charges" : f'{transaction_amounts.get("cable_charge")} {instance.fromaccount.currency.code}',
            "Debit Amount" : f'{self.get_debit_amount(instance,"True")} {instance.fromaccount.currency.code}',
            "Credit Amount" : f'{round(instance.toamount,2)} {instance.inltransaction_tr.all()[0].currency.code}',
            "Note" : instance.note if instance.note else None, 
        }
            representation['type'] = 'TPT'
            representation['Third Party Transfer'] = transaction_details
        elif instance.transactiontype.name in [ "Acccount To Account Transfer","Currency Conversion"]:
            if instance.transactiontype.name == "Acccount To Account Transfer":
                if instance.toaccount.user_account.customer.customertype == 1:
                    beneficairy_name = instance.toaccount.user_account.fullname
                else:
                    beneficairy_name = Businessdetails.objects.get(customer__user=instance.toaccount.user_account.customer.user, isdeleted=False).companyname
            else:
                beneficairy_name = None
            transaction_details = {
            "Transaction Type" : self.get_transaction_type(instance),
            "Transaction No" : instance.transactionno,
            "Date and Time" : instance.createdon.strftime("%d %b %Y, %-H:%M UTC"),
            "Debit Account" : f'{instance.fromaccount.accountno} ({instance.fromaccount.currency.code})',
            "Credit Account" : instance.toaccount.accountno,
            "Beneficiary Name" : beneficairy_name,
            "Currency" : instance.toaccount.currency.code,
            "Net Amount" : f'{transaction_amounts.get("net_amount")} {instance.fromaccount.currency.code}',
            "Conversion Fee" : f'{transaction_amounts.get("conversion_fee")} {instance.fromaccount.currency.code}',
            "Debit Amount" : f'{self.get_debit_amount(instance)} {instance.fromaccount.currency.code}',
            "Credit Amount" : f'{round(instance.toamount,2)} {instance.toaccount.currency.code}',
            "Note" : instance.note if instance.note else None, 
            }
            if self.get_transaction_type(instance) == "Acccount To Account Transfer":
                type = "ATAT"
            elif self.get_transaction_type(instance) == "Currency Conversion":
                type = "CC"
            representation['type'] = type
            representation[self.get_transaction_type(instance)] = transaction_details
        elif instance.transactiontype.name == 'Wallet Withdrawal Transfer':
            transaction_details = {
            "Transaction Type" : "Wallet Withdrawal Transfer",
            "Transaction No" : instance.transactionno,
            "Date and Time" : instance.createdon.strftime("%d %b %Y, %-H:%M UTC"),
            "Sender Name" : full_name,
            "Debit Account" : f"{instance.fromaccount.accountno} {instance.fromaccount.currency.code}",
            "Beneficiary Name" : instance.walletwithdrawal_tr.all()[0].accountholdername,
            "Wallet Name" : instance.walletwithdrawal_tr.all()[0].wallet_name,
            "Currency" : instance.walletwithdrawal_tr.all()[0].currency.code,
            "Net Amount" : f'{transaction_amounts.get("net_amount")} {instance.fromaccount.currency.code}',
            "Conversion Fee" : f'{transaction_amounts.get("conversion_fee")} {instance.fromaccount.currency.code}',
            "Wallet Transfer Fee" : f'{transaction_amounts.get("wallet_fee")} {instance.fromaccount.currency.code}',
            "Cable Charges" : f'{transaction_amounts.get("cable_charge")} {instance.fromaccount.currency.code}',
            "Debit Amount" : f'{self.get_debit_amount(instance,"True")} {instance.fromaccount.currency.code}',
            "Credit Amount" : f'{round(instance.toamount,2)} {instance.walletwithdrawal_tr.all()[0].currency.code}',
            "Note" : instance.note if instance.note else None, 
        }
            representation['type'] = 'WWT'
            representation['Wallet Withdrawal Transfer'] = transaction_details
        return representation