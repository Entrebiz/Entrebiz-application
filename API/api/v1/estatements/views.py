import csv
import datetime
import logging
import math
from Transactions.mixins import ModelQueries, TransactionMail
from Transactions.views import create_directory, render_pdf
from api.v1.estatements.serializers import TrasactionDetailsSerializer, TrasactionsSerializer
from api.v1.utils.pagination import CustomPagination
from entrebiz import settings
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from utils.mixins import UtilMixins
from utils.models import Accounts, Businessdetails, Transactions
from django.db.models import Q

logger = logging.getLogger("lessons")


class EStatementsAPIView(APIView,ModelQueries,CustomPagination):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        action_type = request.data.get("action_type")
        if action_type == "gettransactiondetails":
            accountid = request.data.get("accountid")
            transaction_no = request.data.get("transaction_no")
            beneficiary_name = request.data.get("beneficiary_name")
            from_date = request.data.get("from_date")
            to_date = request.data.get("to_date")
            creditdebit = request.data.get("creditdebit")
            account = Accounts.objects.get(id=accountid)
            if not from_date and not to_date:
                current_date = datetime.datetime.now()
                prev_date = (datetime.datetime.now() - datetime.timedelta(days=30))
                from_date = datetime.datetime.strftime(prev_date, "%Y-%m-%d")
                to_date = datetime.datetime.strftime(current_date, "%Y-%m-%d")
            transactions = Transactions.active.filter(Q(fromaccount__id=accountid)|Q(toaccount__id=accountid), isdeleted=False) \
                .order_by('-id')
            transactions = self.get_transactions_filtered(transactions, accountid=accountid,
                                                          transaction_no=transaction_no,
                                                          beneficiary_name=beneficiary_name,
                                                          from_date=from_date, to_date=to_date, creditdebit=creditdebit)
            if not account.createdby.customer_details.all()[0].useracc_customer.all()[0].ismaster_account:
                transactions = transactions.filter(~Q(amount_type="Conversion Fee")).exclude(
                    Q(toaccount__user_account__ismaster_account=True) &
                    ~Q(transactiontype__name="Third Party Transfer"))
            transactions = transactions.order_by("-id")
            transactions = self.paginate_queryset(transactions,request)
            serializer = TrasactionsSerializer(transactions , many=True, context={'account': Accounts.objects.get(id=accountid), 'request':request})

        if action_type == "gettransactionbyaccount":
            accountid = request.data.get("accountid")
            transaction_no = request.data.get("transaction_no")
            beneficiary_name = request.data.get("beneficiary_name")
            from_date = request.data.get("from_date")
            to_date = request.data.get("to_date")
            if not from_date and not to_date:
                current_date = datetime.datetime.now()
                prev_date = (datetime.datetime.now() - datetime.timedelta(days=30))
                from_date = datetime.datetime.strftime(prev_date, "%Y-%m-%d")
                to_date = datetime.datetime.strftime(current_date, "%Y-%m-%d")
            creditdebit = request.data.get("creditdebit")
            transactions = Transactions.active.filter(Q(fromaccount__id=accountid) | Q(toaccount__id=accountid),
                                                       isdeleted=False)
            transactions = self.get_transactions_filtered(transactions,accountid=accountid,
                                                          transaction_no=transaction_no,
                                                          beneficiary_name=beneficiary_name,
                                                          from_date=from_date,to_date=to_date,creditdebit=creditdebit)
            if not Accounts.objects.get(id=accountid).createdby.customer_details.all()[0].useracc_customer.all()[0].ismaster_account:
                transactions = transactions.filter(~Q(amount_type="Conversion Fee")).exclude(
                    Q(toaccount__user_account__ismaster_account=True) &
                    ~Q(transactiontype__name="Third Party Transfer"))
            transactions = transactions.order_by("-id")
            transactions = self.paginate_queryset(transactions,request)
            serializer = TrasactionsSerializer(transactions, many=True, context={'account': Accounts.objects.get(id=accountid), 'request':request})

        elif action_type == "export_statement":
            content = {"status": 1, "message": "success"}
            accountid = request.data.get("accountid")
            from_date = request.data.get("from_date")
            to_date = request.data.get("to_date")
            if not from_date and not to_date:
                current_date = datetime.datetime.now()
                prev_date = (datetime.datetime.now() - datetime.timedelta(days=30))
                from_date = datetime.datetime.strftime(prev_date, "%Y-%m-%d")
                to_date = datetime.datetime.strftime(current_date, "%Y-%m-%d")
            creditdebit = request.data.get("creditdebit")
            account = Accounts.objects.get(id=accountid)
            transactions = Transactions.active.filter(Q(fromaccount=account) | Q(toaccount=account),
                                                       isdeleted=False)
            transactions = self.get_transactions_filtered(transactions, accountid=accountid,from_date=from_date,
                                                          to_date=to_date, creditdebit=creditdebit)
            if not account.createdby.customer_details.all()[0].useracc_customer.all()[0].ismaster_account:
                transactions = transactions.filter(~Q(amount_type="Conversion Fee")).exclude(
                    Q(toaccount__user_account__ismaster_account=True) &
                    ~Q(transactiontype__name="Third Party Transfer"))
            transactions = transactions.order_by("-id")
            if transactions:
                filename = f"{account.accountno} - Statement.{request.data.get('export_type')}"
                folder = f"statements/{request.data.get('export_type')}/"
                filepath = settings.MEDIA_ROOT + settings.MEDIA_URL + folder
                create_directory(filepath)
                if request.data.get("export_type") == 'pdf':
                    context = {}
                    context['transactions'] = transactions
                    context['account'] = account
                    context['from_date'] = datetime.datetime.strptime(from_date, settings.DATE_FORMAT)
                    context['to_date'] = datetime.datetime.strptime(to_date, settings.DATE_FORMAT)
                    context['account_balance'] = "{:,}".format(round(account.balance, 2))
                    file = render_pdf('transactions/e-statements/statement-pdf.html', context, filename, filepath=folder)
                else:
                    header = ['Date', 'Type', 'Details', 'Amount','Balance']
                    with open(filepath+filename, 'w', encoding='UTF8', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=header)
                        # write the header
                        writer.writeheader()
                        for transaction in transactions:
                            # write the data
                            date = transaction.createdon.strftime("%d/%m/%Y")
                            transaction_type = self.get_transaction_type(transaction)
                            details = f"Transaction No: {transaction.transactionno}, Beneficiary Name: {self.get_beneficiary(transaction).get('name')}, Ref:{self.get_reference(transaction)}"
                            debitcredit_amount = self.get_debitcredit_amount(transaction,account.accountno)
                            balance_amount = self.get_balance_amount(transaction)
                            if self.is_debit_or_credit(transaction,account.accountno) == 'credit':
                                amount = f'+{debitcredit_amount} {account.currency.code}'
                                balance = f'{format(math.ceil(transaction.toaccountbalance*100)/100,".2f")} {account.currency.code}'
                            else:
                                amount = f'-{debitcredit_amount} {account.currency.code}'
                                balance = f'{balance_amount} {account.currency.code}'
                            writer.writerow({
                                'Date':date,
                                'Type':transaction_type,
                                'Details':details,
                                'Amount':amount,
                                'Balance':balance
                            })
                fileToUpload = open(filepath+filename)
                cloudfilename = folder+filename
                UtilMixins().upload_to_s3(fileToUpload,cloudfilename)
                content['data'] = settings.AWS_S3_BUCKET_URL + folder + filename
            else:
                content['data'] = {}
            return Response(content, status=status.HTTP_200_OK)
        return self.get_paginated_response(serializer.data)
    
class GetTransactionDetailsView(APIView,ModelQueries,TransactionMail,UtilMixins):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self,request):
        action_type = request.data.get('action_type')
        if action_type == "get_trasnactiondetailsby_id":
            transaction = Transactions.objects.get(id=request.data.get("transaction_id"))
            if request.user.customer_details.all()[0].useracc_customer.all()[0].ismaster_account:
                try:
                    tr_objs = Transactions.objects.filter(transactionno=transaction.parenttransaction.transactionno,isdeleted=False)
                except:
                    tr_objs = []
                for tr_obj in tr_objs:
                    if tr_obj.amount_type == "Net Amount":
                        transaction = tr_obj
            serializer = TrasactionDetailsSerializer(instance=transaction, context={'request':request})
            content = {"status": 1, "data": serializer.data, "message": "success"}
            return Response(content, status=status.HTTP_200_OK)
        elif action_type == "export_pdf":
            transaction = Transactions.objects.get(id=request.data.get("transaction_id"))
            invoice = f"transaction{ transaction.transactionno}.pdf"
            file = f"invoices/{invoice}"
            filepath = settings.MEDIA_ROOT + settings.MEDIA_URL + file
            if transaction.fromaccount.user_account.customer.customertype == 1:
                full_name = transaction.fromaccount.user_account.fullname
            else:
                full_name = Businessdetails.objects.get(customer__user=transaction.fromaccount.user_account.customer.user, isdeleted=False).companyname
            transaction_amounts = self.get_transaction_amounts(transaction,from_amount=True)
            isExist = self.check_cloudfile_exists(file)
            if not isExist:
                if transaction.transactiontype.name == "Third Party Transfer":
                    context = {
                        'wire_transfer': True,
                        'transactionno': transaction.transactionno,
                        'transaction_datetime_utc': transaction.createdon.strftime("%d %b %Y, %-H:%M UTC"),
                        'sender_name': full_name,
                        'from_currency_code': transaction.fromaccount.currency.code,
                        'fromaccount': transaction.fromaccount.accountno,
                        'beneficiary_accno': transaction.inltransaction_tr.all()[0].accountnumber,
                        'beneficiary_name': transaction.inltransaction_tr.all()[0].accountholdername,
                        'bank_name': transaction.inltransaction_tr.all()[0].bankname,
                        'swift_code': transaction.inltransaction_tr.all()[0].swiftcode,
                        'city': transaction.inltransaction_tr.all()[0].city,
                        'country': transaction.inltransaction_tr.all()[0].country.shortform,
                        'currency': transaction.inltransaction_tr.all()[0].currency.code,
                        'purpose_type': transaction.inltransaction_tr.all()[0].purpose.transactionpurpose,
                        'purpose_note': transaction.inltransaction_tr.all()[0].other_purpose_note if transaction.inltransaction_tr.all()[0].other_purpose_note else "",
                        'email': transaction.inltransaction_tr.all()[0].email,
                        'box_no': transaction.inltransaction_tr.all()[0].user_box_no if transaction.inltransaction_tr.all()[0].user_box_no else None,
                        'street': transaction.inltransaction_tr.all()[0].user_street if transaction.inltransaction_tr.all()[0].user_street else None,
                        'user_city': transaction.inltransaction_tr.all()[0].user_city if transaction.inltransaction_tr.all()[0].user_city else None,
                        'state': transaction.inltransaction_tr.all()[0].user_state if transaction.inltransaction_tr.all()[0].user_state else None,
                        'user_counrty': transaction.inltransaction_tr.all()[0].user_country.shortform if transaction.inltransaction_tr.all()[0].user_country else None,
                        'phone_no': transaction.inltransaction_tr.all()[0].user_phone if transaction.inltransaction_tr.all()[0].user_phone else None,
                        'amount': transaction_amounts.get("net_amount"),
                        'conversion_fee': transaction_amounts.get("conversion_fee"),
                        'wire_tr_fee': transaction_amounts.get("wire_fee"),
                        'cable_charge': transaction_amounts.get("cable_charge"),
                        'debit_amount': self.get_debit_amount(transaction,"True"),
                        'credit_amount': round(transaction.toamount,2),
                        'note': transaction.note,
                        'year': str(datetime.date.today().year),

                    }
                    context.update({
                        'invoice': self.get_transaction_receipt(transaction)
                    })
                    file = render_pdf('accounts/wire_transfer/transaction-pdf-template.html', context, invoice)
                elif transaction.transactiontype.name in[ "Acccount To Account Transfer","Currency Conversion"]:
                    if transaction.transactiontype.name == "Acccount To Account Transfer":
                        if transaction.toaccount.user_account.customer.customertype == 1:
                            beneficiary_name = transaction.toaccount.user_account.fullname
                        else:
                            beneficiary_name = Businessdetails.objects.get(customer=transaction.toaccount.user_account.customer,isdeleted=False).companyname
                    else:
                        beneficiary_name = None
                    context = {
                        'transaction_number': transaction.transactionno,
                        'debit_account': transaction.fromaccount.accountno,
                        'debit_currency_code':transaction.fromaccount.currency.code,
                        'credit_account': transaction.toaccount.accountno,
                        'credit_currency_code':transaction.toaccount.currency.code,
                        'beneficiary_name': beneficiary_name,
                        'net_amount': transaction_amounts.get("net_amount"),
                        'conversion_fee':  transaction_amounts.get("conversion_fee"),
                        'debit_amount': self.get_debit_amount(transaction),
                        'credit_amount': round(transaction.toamount,2),
                        'note': transaction.note,
                        'Date_and_Time': transaction.createdon.strftime("%d %b %Y, %-H:%M UTC")
                    }
                    file = render_pdf('accounttoaccount/transaction-invoice.html', context, invoice)
                elif transaction.transactiontype.name == "Wallet Withdrawal Transfer":
                    context = {
                        'wallet_transfer': True,
                        'transactionno': transaction.transactionno,
                        'transaction_datetime_utc': transaction.createdon.strftime("%d %b %Y, %-H:%M UTC"),
                        'sender_name': full_name,
                        'Wallet_name': transaction.walletwithdrawal_tr.all()[0].wallet_name,
                        'from_currency_code': transaction.fromaccount.currency.code,
                        'fromaccount': transaction.fromaccount.accountno,
                        'beneficiary_name': transaction.walletwithdrawal_tr.all()[0].accountholdername,
                        'currency': transaction.walletwithdrawal_tr.all()[0].currency.code,
                        'amount': transaction_amounts.get("net_amount"),
                        'conversion_fee': transaction_amounts.get("conversion_fee"),
                        'wallet_tr_fee': transaction_amounts.get("wallet_fee"),
                        'cable_charge': transaction_amounts.get("cable_charge"),
                        'debit_amount': self.get_debit_amount(transaction,"True"),
                        'credit_amount': round(transaction.toamount,2),
                        'note': transaction.note,
                        'year': str(datetime.date.today().year),
                    }
                    file = render_pdf('wallet-withdrawal/wallettransfer_transaction-pdf-template.html', context, invoice)
            content = {"status": 1, "data": settings.AWS_S3_BUCKET_URL+'invoices/' + invoice, "message": "success"}
            if request.data.get("send_mail"):
                context = {
                    'user': full_name.title(),
                    'mail_attach': True,
                    'from_currency_code': transaction.fromaccount.currency.code,
                    'amount': transaction_amounts.get("net_amount"),
                    'year': str(datetime.date.today().year),
                }
                self.transaction_success_or_failure_mail(email=request.user.email, email_data=context, status=True,
                                                         attach=filepath)
                content['message'] = "Email sent successfully!"
                content['data'] = {}
            return Response(content, status=status.HTTP_200_OK)

