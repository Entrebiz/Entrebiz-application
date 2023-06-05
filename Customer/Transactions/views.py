import logging
import math
import os
from os.path import exists

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q
from django.shortcuts import render, redirect
from django.template.loader import get_template, render_to_string
from django.views import View
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import logout
from django.contrib import messages
from django.conf import settings

from django.db import transaction
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required

from utils.mixins import UtilMixins
from utils.models import (Currencies, Currencyconversionmargins, Externalbeneficiaries, Transactionpurposetype,
                          Countries,
                          Accounts, Useraccounts, Otps, Transactiontypes, Businessdetails, Transactions,
                          Internationaltransactions, InvoiceDocument, Cablecharges, Customers,
                          Currencyconversionratescombined,
                          Cryptobeneficiaries, WalletWithdrawalTransactions, DomesticBeneficiary, DomesticTransaction)
from Transactions.mixins import OTP, FindAccount, TransactionMail, ModelQueries, add_log_action, checkNonAsciiChracters, transaction_lock_fn
from secrets import token_urlsafe
import json
import datetime
from decimal import Decimal
import re
import pdfkit
import csv
from EntrebizAdmin.decorators import template_decorator, transaction_status
logger = logging.getLogger('lessons')

def logout_view(request):
    logout(request)
    return redirect('login')


#domestic transaction
@method_decorator(login_required, name='dispatch')
@method_decorator(template_decorator(title="Domestic Transfer"),name='dispatch')
@method_decorator(transaction_status, name='dispatch')
class DomesticTransfer(View):
    def get(self,request):
        if request.GET.get('Edit'):
            prevData = request.session['domesticTransaction']
            try:
                prevInvoice = request.session['invoice_document']
            except Exception as e:
                logger.info(e)
                prevInvoice = None
        else:
            if request.session.get('invoice_document'):
                del request.session['invoice_document']
            prevData = None
            prevInvoice = None
        accounts = Accounts.objects.filter(user_account__customer__user=request.user, isdeleted=False)
        currencies = Currencies.objects.filter(Q(code='USD') | Q(code='INR') | Q(code='SGD'), isdeleted=False).order_by('name', '-code')
        domesticbeneficiary = DomesticBeneficiary.objects.filter(createdby=request.user, isdeleted=False)
        transactionpurposetypes = Transactionpurposetype.objects.filter(isdeleted=False)
        countries = Countries.active.all().order_by('name')
        user_details = Useraccounts.objects.get(isdeleted=False,customer__user=request.user)
        context = {
            'accounts' : accounts,
            'currencies' : currencies,
            'countries' : countries,
            'domesticbeneficiaries' : domesticbeneficiary,
            'transactionpurposetypes' : transactionpurposetypes,
            'prevData' : prevData,
            'prevInvoice' : prevInvoice,
            'user_details' : user_details
        }
        if request.session.get('cancelDomesticTrMsg'):
            context['message'] = request.session.get('cancelDomesticTrMsg')
            logger.info(f"{request.user.email} cancel domestic transfer")
            context['status'] = True
            del request.session['cancelDomesticTrMsg']
        if request.session.get('domesticTrdeclinedMsg'):
            context['message'] = request.session.get('domesticTrdeclinedMsg')
            context['status'] = False
            del request.session['domesticTrdeclinedMsg']
        return render(request, 'accounts/domestic_transaction/domestic-transfer.html', context)

    def post(self, request):

        def context_function():
            prevData = request.POST.dict()
            accounts = Accounts.objects.filter(user_account__customer__user=request.user, isdeleted=False)
            currencies = Currencies.objects.filter(isdeleted=False)
            domesticbeneficiaries = DomesticBeneficiary.objects.filter(createdby=request.user, isdeleted=False)
            transactionpurposetypes = Transactionpurposetype.objects.filter(isdeleted=False)
            countries = Countries.active.all().order_by('name')
            self.context = {
                'accounts': accounts,
                'currencies': currencies,
                'countries': countries,
                'domesticbeneficiaries': domesticbeneficiaries,
                'transactionpurposetypes': transactionpurposetypes,
                'prevData': prevData,
                'user_details': Useraccounts.objects.get(isdeleted=False, customer__user=request.user)
            }
            return True

        if not request.POST.get('BeneficiaryACNo').isalnum():
            if context_function():
                self.context['message'] = 'Account number should not contain any special characters'
                self.context['status'] = False
                logger.info(
                    f"{request.user.email} enter BeneficiaryACNo have special characters.BeneficiaryACNo contains only alphanumeric charachers")
                return render(request, 'accounts/domestic_transaction/domestic-transfer.html', self.context)
        email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if request.POST.get('Email') and not re.search(email_regex, request.POST.get('Email')):
            if context_function():
                self.context['message'] = 'Invalid Email'
                self.context['status'] = False
                logger.info(f"{request.user.email} entered invalid email {request.POST.get('Email')}")
                return render(request, 'accounts/domestic_transaction/domestic-transfer.html', self.context)
      
                                
        phone_regex = r"^\+{0,1}[0-9]{10,13}"
        if request.POST.get('Phoneno') and not re.search(phone_regex, request.POST.get('Phoneno')):
            if context_function():
                self.context['message'] = 'Invalid Phone number'
                self.context['status'] = False
                logger.info(f"{request.user.email} entered invalid Phone number")
                return render(request, 'accounts/domestic_transaction/domestic-transfer.html', self.context)
        if request.FILES.get('invoice-doc'):
            ext = os.path.splitext(request.FILES.get('invoice-doc').name)[1]
            if not ext in settings.ALLOWED_FORMATS:
                if context_function():
                    self.context['message'] = 'Incorrect file format'
                    self.context['status'] = False
                    logger.info(
                        f"{request.user.email} try to upload {request.FILES.get('invoice-doc').name}  Incorrect file format")
                    return render(request, 'accounts/domestic_transaction/domestic-transfer.html', self.context)
            elif not all(ord(c) < 128 for c in request.FILES.get('invoice-doc').name):
                if context_function():
                    self.context['message'] = 'Special characters should not be in file name'
                    self.context['status'] = False
                    logger.info(
                        f"{request.user.email} uploaded invoice file name hve special characters.Special characters should not be in file name ")
                    return render(request, 'accounts/domestic_transaction/domestic-transfer.html', self.context)
        if not checkNonAsciiChracters([request.POST.get('Email'), request.POST.get('BankName'),
                                       request.POST.get('RoutingNumber'), request.POST.get('City'),
                                       request.POST.get('Note'), request.POST.get('Boxno', ''),
                                       request.POST.get('Street', ''), request.POST.get('userCity', ''),
                                       request.POST.get('State', '')]):
            if context_function():
                self.context['message'] = 'Fancy characters are not allowed'
                self.context['status'] = False
                logger.info(f"Fancy characters are not allowed")
                return render(request, 'accounts/domestic_transaction/domestic-transfer.html', self.context)
            


        if not request.POST.get('RoutingNumber').isalnum():
        # Check if value is None or contains non-alphanumeric characters
            if request.POST.get('Currency') == 'INR':
                if context_function():
                    self.context['message'] = 'IFSC CODE should not contain any special characters'
                    self.context['status'] = False
                    logger.info('IFSC CODE should not contain any special characters')
                    return render(request, 'accounts/domestic_transaction/domestic-transfer.html', self.context)
            else:
                if context_function():
                    self.context['message'] = 'ABA/ACH Routing number should not contain any special characters'
                    self.context['status'] = False
                    logger.info('ABA/ACH Routing number should not contain any special characters')
                    return render(request, 'accounts/domestic_transaction/domestic-transfer.html', self.context)

                
        
        
        
        
        
        # if not request.POST.get('Note').isalnum():
        #    # Check if value is None or contains non-alphanumeric characters
        #     if context_function():
        #         self.context['message'] = 'Notes - Recipient Account Number should not contain any special characters'
        #         self.context['status'] = False
        #         logger.info(f"Notes - Recipient Account Number should not contain any special characters ")
        #         return render(request, 'accounts/domestic_transaction/domestic-transfer.html', self.context)
       
        if request.session.get('domesticTransaction'):
            del request.session['domesticTransaction']
        if request.session.get('token'):
            del request.session['token']
        request.session['domesticTransaction'] = request.POST.dict()

        amount = round(Decimal(request.POST.get('Amount')), 2)
        from_amount = amount
        from_account = Accounts.objects.get(accountno=request.POST.get('FromAccount'), isdeleted=False)
        from_account_balance = Decimal(from_account.balance)

        def conversion_charges(amount):
            if amount < 1000:
                self.domestic_transfer_fee = Decimal(10.00)
                self.cable_charge = Decimal(49.00)

            elif amount >= 1000 and amount < 6900:
                self.total_tr_charge = Decimal(69.00)
                self.domestic_transfer_fee = round(amount * Decimal((1 / 100)), 2)
                self.cable_charge = round(self.total_tr_charge - self.domestic_transfer_fee, 2)

            elif amount >= 6900:
                self.domestic_transfer_fee = round(amount * Decimal((1 / 100)), 2)
                self.cable_charge = Decimal(0.00)

        def conversion_rates(amount, from_currency_code, conversion_fee, domestic_transfer_fee, cable_charge):
            to_dollar = Currencyconversionratescombined.objects.get(fromcurrency__code='USD',
                                                                    tocurrency__code=from_currency_code,
                                                                    isdeleted=False)
            currency_conversion = Currencyconversionratescombined.objects.get(fromcurrency__code=from_currency_code,
                                                                              tocurrency__code=request.POST.get(
                                                                                  'Currency'), isdeleted=False)
            conversionrate = round(currency_conversion.conversionrate, 4)
            try:
                currency_margin = Currencyconversionmargins.objects.get(fromcurrency__code=from_currency_code,
                                                                        tocurrency__code=request.POST.get('Currency'),
                                                                        isdeleted=False)
                margin_rate = currency_margin.marginpercent
                conversionrate = conversionrate - (conversionrate * Decimal(float(margin_rate) / 100))
            except Exception as e:
                logger.info(e)
                pass

            self.min_tr_amount = Decimal(100) * to_dollar.conversionrate
            self.conversion_fee = conversion_fee
            self.domestic_transfer_fee = round(domestic_transfer_fee * to_dollar.conversionrate, 2)
            self.cable_charge = round(cable_charge * to_dollar.conversionrate, 2)
            self.credit_amount = round(from_amount * conversionrate, 2)
            self.conversionrate = conversionrate

        from_currency_code = from_account.currency.code
        if request.POST.get('Currency') == from_currency_code:
            if from_currency_code == 'USD':
                amount = Decimal(amount)
            else:
                to_dollar = Currencyconversionratescombined.objects.get(fromcurrency__code='USD',
                                                                        tocurrency__code=from_currency_code,
                                                                        isdeleted=False)
                amount = Decimal(amount) / to_dollar.conversionrate
            conversion_fee = Decimal(0.00)
            conversion_charges(amount)
        else:
            if from_currency_code == 'USD':
                amount = Decimal(amount)
            else:
                to_dollar = Currencyconversionratescombined.objects.get(fromcurrency__code='USD',
                                                                        tocurrency__code=from_currency_code,
                                                                        isdeleted=False)
                amount = Decimal(amount) / to_dollar.conversionrate
            conversion_fee = round(from_amount * Decimal(0.5 / 100), 2)
            conversion_charges(amount)
        conversion_rates(amount, from_currency_code, conversion_fee, self.domestic_transfer_fee, self.cable_charge)
        debit_amount = self.domestic_transfer_fee + self.cable_charge + self.conversion_fee + from_amount
        commission_charges = round((self.domestic_transfer_fee + self.cable_charge + self.conversion_fee), 2)
        if from_account_balance < debit_amount:
            if context_function():
                self.context['message'] = "You don't have enough funds to make this transaction"
                self.context['status'] = False
                logger.info(
                    f"{request.user.email}  account balance {from_account_balance}. so user don't have enough funds to make this transaction ")
                return render(request, 'accounts/domestic_transaction/domestic-transfer.html', self.context)
        elif from_amount < self.min_tr_amount:
            if context_function():
                self.context[
                    'message'] = f'Minimum amount required for the transaction is {format(self.min_tr_amount, ".2f")} {from_currency_code}'
                self.context['status'] = False
                logger.info(
                    f"the amount {from_amount} to be transaction is lowerthan  Minimum amount. {self.min_tr_amount} required for the transaction ")
                return render(request, 'accounts/domestic_transaction/domestic-transfer.html', self.context)
        is_dom_ben = DomesticBeneficiary.objects.filter(
            Q(domestic_accountnumber=request.POST.get('BeneficiaryACNo')) | Q(domestic_name=request.POST.get('BeneficiaryName')),
            isdeleted=False, createdby=request.user).exists()
        request.session['domesticTransaction'].update({
            'cable_charge': format(self.cable_charge, ".2f"),
            'domestic_transfer_fee': format(self.domestic_transfer_fee, ".2f"),
            'conversion_fee': format(self.conversion_fee, ".2f"),
            'debit_amount': format(debit_amount, ".2f"),
            'commission_charges': format(commission_charges, ".2f"),
            'credit_amount': format(self.credit_amount, ".2f"),
            'from_currency_code': from_currency_code,
            'recipient_currency_code': request.POST.get('Currency'),
            'conversionrate': format(self.conversionrate, ".2f"),
            'is_dom_ben': is_dom_ben,
        })

        try:
            if request.POST.get('companyTr') == 'on' and request.FILES.get('invoice-doc'):
                invoice_file = InvoiceDocument.objects.create(invoice_doc=request.FILES.get('invoice-doc'))
                request.session['invoice_document'] = {
                    'invoice_doc': request.FILES['invoice-doc'].name,
                    'invoice_doc_id': invoice_file.id
                }
            elif not request.POST.get('companyTr') and not request.FILES.get('invoice-doc') and request.session[
                'invoice_document']:
                del request.session['invoice_document']
        except Exception as e:
            logger.info(f"No file was uploaded! -> {e}")

        request.session['token'] = token_urlsafe(30)
        return redirect('domestic-transfer-confirm', request.session['token'])

@method_decorator(login_required, name='dispatch')
@method_decorator(transaction_status, name='dispatch')
class DomesticTransferConfirm(View):
    def get(self,request,token):
        if  not token or token != request.session.get('token') or not request.session['domesticTransaction']:
            logger.info(f"{request.user.email} generated token -{token} is not equal token from session -{request.session.get('token')}.re-direct to dashboard" )
            # logout here
            return redirect('/')
        if token == request.session.get('token'):
            return render(request,'accounts/domestic_transaction/domestic-transfer-confirm.html')

    def post(self, request,token):
        if request.POST.get('action_type') == 'resent otp' :
            user_account = Useraccounts.objects.get(customer__user=request.user)
            full_name = f"{user_account.firstname} {user_account.lastname}"
            otp_status = OTP()
            if request.session.get('prevToken'):
                del request.session['prevToken']
            request.session['prevToken'] = request.session['token']
            # del request.session['token']
            # request.session['token'] = token_urlsafe(30)
            return JsonResponse({
                'message' : 'OTP sent, Please verify!'
                })

        elif request.POST.get('otp_sent') == 'otp_sent':
            if token == request.session.get('token'):
                if request.POST.get('save_ben') == 'on':
                    external_ben, status = DomesticBeneficiary.objects.get_or_create(
                        domestic_name=request.session['domesticTransaction']['BeneficiaryName'],
                        domestic_accountnumber=request.session['domesticTransaction']['BeneficiaryACNo'],
                        currency=Currencies.objects.get(code=request.session['domesticTransaction']['Currency']),
                        routing_number=request.session['domesticTransaction']['RoutingNumber'],
                        country=Countries.active.get(name=request.session['domesticTransaction']['Country']),
                        domestic_city=request.session['domesticTransaction']['City'],
                        account_type=request.session['domesticTransaction']['AccountType'],
                        domestic_bankname=request.session['domesticTransaction']['BankName'],
                        createdby=request.user,
                        customer=Customers.objects.get(user=request.user)
                    )
                    external_ben.domestic_email = request.session['domesticTransaction']['Email']
                    external_ben.save()
                user_account = Useraccounts.objects.get(customer__user=request.user)
                full_name = f"{user_account.firstname} {user_account.lastname}"
                otp_status = OTP()
                if otp_status:
                    messages.success(request, 'OTP sent, Please verify!')
                    if request.session.get('prevToken'):
                        del request.session['prevToken']
                    request.session['prevToken'] = request.session['token']
                    del request.session['token']
                    request.session['token'] = token_urlsafe(30)
                    return redirect('domestic-transfer-domesticOtp', request.session['token'])
                else:
                    messages.error(request, 'Could not send OTP')
                    return redirect('domestic-transfer-confirm', request.session['token'])
            else:
                logger.info(
                    f"{request.user.email} generated token -{token} is not equal token from session -{request.session.get('token')}.re-direct to dashboard")
                # logout here
                return redirect('/')


@method_decorator(login_required, name='dispatch')
@method_decorator(transaction_status, name='dispatch')
class CancelDomesticTransfer(View):
    def get(self,request):
        if request.session.get('domesticTransaction'):
            del request.session['domesticTransaction']
        if request.session.get('token'):
            del request.session['token']
        if request.session.get('invoice_document'):
            del request.session['invoice_document']
        request.session['cancelDomesticTrMsg'] = 'Last transaction canceled'

        return redirect('domestic-transfer/')
#

@method_decorator(login_required, name='dispatch')
@method_decorator(transaction_status, name='dispatch')
class DomesticTransferOtp(View):
    def get(self, request, token):
        if not token or token != request.session.get('token') or not request.session['domesticTransaction']:
            logger.info(
                f"{request.user.email} generated token -{token} is not equal token from session -{request.session.get('token')}.re-direct to dashboard")
            # logout here
            return redirect('/')
        if token == request.session.get('token'):
            return render(request, 'accounts/domestic_transaction/domestic-transfer-otp.html')

    def post(self, request, token):
        def validation_fn():
            if token != request.session.get('token'):
                logger.info(
                    f"{request.user.email} generated token -{token} is not equal token from session - {request.session.get('token')}.re-direct to dashboard")
                return {
                    'status': False,
                    'error': 'Your Transaction has been declined due to Security reason'
                }

            try:
                
                otp = Otps.objects.get(code=request.POST.get('otp'),
                                       transactiontype='Domestic Transaction',
                                       validated=False,
                                       createdby=request.user, token=request.session['prevToken'], isdeleted=False)
                transaction_lock_fn(request, is_lock=False)
            except Exception as e:
                logger.info(e)
                transaction_state = transaction_lock_fn(request)
                return {
                    'otp_error': True,
                    'status': False,
                    'error': transaction_state.get("message")
                }
            valid_till = datetime.datetime.now()
            valid_till = valid_till.date().strftime(settings.DATE_FORMAT)
            valid_date = datetime.datetime.strptime(valid_till, settings.DATE_FORMAT)
            # if valid_till <= otp.validtill:
            if valid_date.date() <= otp.validtill:
                otp.validated = True
                otp.save()
            else:
                logger.info(f"{request.user.email} entered otp invalid or it expired otp")
                return {
                    'otp_error': True,
                    'status': False,
                    'error': 'Verification failed, expired otp'
                }
            try:
                customer_type = Customers.objects.get(user=request.user, isdeleted=False).customertype
                if customer_type == 1:
                    user = Useraccounts.objects.get(customer__user=request.user, isdeleted=False)
                    sender_name = f'{user.firstname} {user.lastname}'
                else:
                    sender_name = Businessdetails.objects.get(customer__user=request.user, isdeleted=False).companyname
            except Exception as e:
                logger.info(e)
                return {
                    'status': False,
                    'error': 'Your Transaction has been declined due to invalid Customer or Business details'
                }
            request.session['domesticTransaction'].update({
                'sender_name': sender_name
            })

            try:
                # last_transactionno = Transactions.objects.latest('id').id + 10000000
                last_transactionno = Transactions.objects.latest('transactionno').transactionno
            except Exception as e:
                logger.info(e)
                last_transactionno = 10000000

            def transaction_fn(last_transactionno, fromamount, charge, parent_tr=None, toamount=None, dom_tr=None,
                               commission_charges=None, cable_charge=None, last_transaction=None):
                try:
                    try:
                        # account = Accounts.objects.get(createdby=request.user, accountno=request.session['internationalTransaction']['FromAccount'],isdeleted=False)
                        account = Accounts.objects.get(
                            accountno=request.session['domesticTransaction']['FromAccount'], isdeleted=False)
                    except Exception as e:
                        logger.info(e)
                        return {
                            'status': False,
                            'error': 'Your Transaction has been declined due to invalid source account'
                        }
                    if account.balance < Decimal(fromamount):
                        raise Exception()
                    account_balance = account.balance - Decimal(fromamount)
                    account.balance = account_balance
                    account.save()
                except Exception as e:
                    logger.info(e)
                    return {
                        'status': False,
                        'error': 'Your Transaction has been declined due to insufficient fund'
                    }
                if cable_charge:
                    cablecharge_obj = Cablecharges.objects.create(
                        parenttransaction=parent_transaction,
                        chargeamount=Decimal(request.session['domesticTransaction']['cable_charge']),
                        currency=Currencies.objects.get(code=request.session['domesticTransaction']['Currency'],
                                                        isdeleted=False),
                        createdby=request.user,
                        transaction=last_transaction
                    )
                    add_log_action(request, cablecharge_obj,
                                   status=f'cable charge created for transaction {parent_transaction.transactionno}',
                                   status_id=1)
                    return {
                        'status': True,
                    }

                else:
                    if commission_charges:
                        try:
                            toaccount = Accounts.objects.get(user_account__ismaster_account=True,
                                                             currency__code=request.session['domesticTransaction'][
                                                                 'from_currency_code'], isdeleted=False)
                        except Exception as e:
                            logger.info(e)
                            toaccount = None
                    else:
                        toaccount = None

                    to_account_balance = None
                    charge_type = None
                    if charge == 1:
                        charge_type = 'Net Amount'
                    elif charge == 2:
                        charge_type = 'Conversion Fee'
                    elif charge == 3:
                        charge_type = 'Domestic Transfer Fee'
                    try:
                        self.transaction = Transactions.objects.create(
                            transactionno=int(last_transactionno) + 1,
                            # fromaccount=Accounts.objects.get(user_account__customer__user=request.user,accountno=request.session['internationalTransaction']['FromAccount'], isdeleted=False),
                            fromaccount=Accounts.objects.get(
                                accountno=request.session['domesticTransaction']['FromAccount'], isdeleted=False),
                            toaccount=None,
                            fromamount=fromamount,
                            toamount=toamount,
                            initiatedby=request.user,
                            transactiontype=Transactiontypes.objects.get(name='Domestic Transfer'),
                            createdby=request.user,
                            note=request.session['domesticTransaction']['Note'],
                            recipientname=request.session['domesticTransaction']['BeneficiaryName'],
                            conversionrate=request.session.get('domesticTransaction').get('conversionrate'),
                            fromaccountbalance=account_balance,
                            toaccountbalance=to_account_balance,
                            parenttransaction=parent_tr,
                            amount_type=charge_type,
                            affiliate_fee_percentage=Customers.objects.get(isdeleted=False,
                                                                           user=request.user).outgoingtansactionfee
                        )
                        add_log_action(request, self.transaction,
                                       status=f"transaction(Domestic transfer : amount type {self.transaction.amount_type}) created for account {str(self.transaction.fromaccount.accountno)}",
                                       status_id=1)
                        if dom_tr:
                            try:
                                invoice_doc = InvoiceDocument.objects.get(
                                    id=request.session['invoice_document']['invoice_doc_id'])

                                invoice_doc.transaction = self.transaction
                                invoice_doc.save()
                            except Exception as e:
                                logger.info(e)
                                pass
                            dom_tr = DomesticTransaction.objects.create(
                                transaction=self.transaction,
                                bankname=request.session['domesticTransaction']['BankName'],
                                routing_number=request.session['domesticTransaction']['RoutingNumber'],
                                accountnumber=request.session['domesticTransaction']['BeneficiaryACNo'],
                                accountholdername=request.session['domesticTransaction']['BeneficiaryName'],
                                currency=Currencies.objects.get(
                                    code=request.session['domesticTransaction']['Currency'], isdeleted=False),
                                createdby=request.user,
                                city=request.session['domesticTransaction']['City'],
                                country=Countries.active.get(
                                    name=request.session['domesticTransaction']['Country']),
                                email=request.session['domesticTransaction']['Email'],
                                purpose=Transactionpurposetype.objects.get(
                                    transactionpurpose=request.session['domesticTransaction']['PurposeType'],
                                    isdeleted=False),
                                other_purpose_note=request.session['domesticTransaction']['PurposeNote'],
                                note=request.session['domesticTransaction']['Note'],
                                user_box_no=request.session['domesticTransaction']['Boxno'] if request.session[
                                    'domesticTransaction'].get('Boxno') else None,
                                user_street=request.session['domesticTransaction']['Street'] if request.session[
                                    'domesticTransaction'].get('Street') else None,
                                user_city=request.session['domesticTransaction']['userCity'] if request.session[
                                    'domesticTransaction'].get('userCity') else None,
                                user_state=request.session['domesticTransaction']['State'] if request.session[
                                    'domesticTransaction'].get('State') else None,
                                user_country=Countries.objects.get(
                                    name=request.session['domesticTransaction']['userCountry']) if request.session[
                                    'domesticTransaction'].get('userCountry') else None,
                                user_phone=request.session['domesticTransaction']['Phoneno'] if request.session[
                                    'domesticTransaction'].get('Phoneno') else None
                            )
                            add_log_action(request, dom_tr,
                                           status=f'domestic transaction created for account {str(self.transaction.fromaccount.accountno)}',
                                           status_id=1)
                    except Exception as e:
                        logger.info(e)
                        return {
                            'status': False,
                            'error': 'Your Transaction has been declined due to some error'
                        }

            response = transaction_fn(last_transactionno, request.session['domesticTransaction']['Amount'],
                                      toamount=request.session['domesticTransaction']['credit_amount'], charge=1,
                                      dom_tr=True)
            if response and not response.get('status'):
                return response
            parent_transaction = self.transaction
            charge = 3
            response = transaction_fn(last_transactionno,
                                      request.session['domesticTransaction']['domestic_transfer_fee'], charge,
                                      parent_transaction,
                                      toamount=request.session['domesticTransaction']['domestic_transfer_fee'],
                                      commission_charges=True)
            if response and not response.get('status'):
                return response
            charge = 2
            response = transaction_fn(last_transactionno, request.session['domesticTransaction']['conversion_fee'],
                                      charge, parent_transaction,
                                      toamount=request.session['domesticTransaction']['conversion_fee'],
                                      commission_charges=True)
            if response and not response.get('status'):
                return response
            last_transaction = self.transaction
            #
            response = transaction_fn(last_transactionno, request.session['domesticTransaction']['cable_charge'],
                                      parent_transaction, cable_charge=True, last_transaction=last_transaction)
            if response and not response.get('status'):
                return response
            # cable_charge_fn(parent_transaction, last_transaction)
            request.session['domesticTransaction'].update({
                'transactionno': parent_transaction.transactionno,
                'transaction_id': parent_transaction.id,
                'transaction_datetime_utc': datetime.datetime.utcnow().strftime("%d %b %Y, %-H:%M UTC"),
            })
            if request.session['prevToken']:
                del request.session['prevToken']
            if request.session.get('token'):
                del request.session['token']
                request.session['token'] = token_urlsafe(30)
            return {
                'status': True,
            }

        response = validation_fn()
        if response and not response.get('status'):
            if response.get('otp_error') == True:
                context = {
                    'statust': False,
                    'message': response.get('error')
                }
                return render(request, 'accounts/domestic_transaction/domestic-transfer-otp.html', context)
            # messages.error(request,response.get('error'))
            user_account = Useraccounts.objects.get(customer__user=request.user)
            full_name = f"{user_account.firstname} {user_account.lastname}"
            context = {
                'user': full_name.title(),
                'error': True,
                'message': response.get('error'),
                'year': str(datetime.date.today().year),
            }
            transaction_mail_status = TransactionMail().transaction_success_or_failure_mail(email=request.user.email,
                                                                                            email_data=context,
                                                                                            status=False)
            request.session['domesticTrdeclinedMsg'] = response.get('error')
            logger.info(f"{request.user.email} transaction declained redirect to domestic transfer page")
            return redirect('domestic-transfer')
        elif response.get('status'):
            customer_account = Useraccounts.objects.get(customer__user=request.user)
            context = {
                'domestic_transfer': True,
                'domestic_success': True,
                'test_user': customer_account.test_account,
                'transactionno': request.session['domesticTransaction']['transactionno'],
                'transaction_datetime_utc': request.session['domesticTransaction']['transaction_datetime_utc'],
                'sender_name': request.session['domesticTransaction']['sender_name'],
                'from_currency_code': request.session['domesticTransaction']['from_currency_code'],
                'fromaccount': request.session['domesticTransaction']['FromAccount'],
                'beneficiary_accno': request.session['domesticTransaction']['BeneficiaryACNo'],
                'beneficiary_name': request.session['domesticTransaction']['BeneficiaryName'],
                'bank_name': request.session['domesticTransaction']['BankName'],
                'routing_number': request.session['domesticTransaction']['RoutingNumber'],
                'city': request.session['domesticTransaction']['City'],
                'country': request.session['domesticTransaction']['Country'],
                'currency': request.session['domesticTransaction']['Currency'],
                'purpose_type': request.session['domesticTransaction']['PurposeType'],
                'purpose_note': request.session['domesticTransaction']['PurposeNote'],
                'email': request.session['domesticTransaction']['Email'],
                'box_no': request.session['domesticTransaction']['Boxno'] if request.session[
                    'domesticTransaction'].get('Boxno') else None,
                'street': request.session['domesticTransaction']['Street'] if request.session[
                    'domesticTransaction'].get('Street') else None,
                'user_city': request.session['domesticTransaction']['userCity'] if request.session[
                    'domesticTransaction'].get('userCity') else None,
                'state': request.session['domesticTransaction']['State'] if request.session[
                    'domesticTransaction'].get('State') else None,
                'user_counrty': request.session['domesticTransaction']['userCountry'] if request.session[
                    'domesticTransaction'].get('userCountry') else None,
                'phone_no': request.session['domesticTransaction']['Phoneno'] if request.session[
                    'domesticTransaction'].get('Phoneno') else None,
                'amount': request.session['domesticTransaction']['Amount'],
                'conversion_fee': request.session['domesticTransaction']['conversion_fee'],
                'domestic_tr_fee': request.session['domesticTransaction']['domestic_transfer_fee'],
                'cable_charge': request.session['domesticTransaction']['cable_charge'],
                'debit_amount': request.session['domesticTransaction']['debit_amount'],
                'credit_amount': request.session['domesticTransaction']['credit_amount'],
                'note': request.session['domesticTransaction']['Note'],
                'year': str(datetime.date.today().year),

            }
            try:
                context.update({
                    'invoice': request.session['invoice_document']['invoice_doc']
                })
            except Exception as e:
                logger.info(e)
                context.update({
                    'invoice': None
                })
            transaction_mail_status = TransactionMail().transaction_success_or_failure_mail(email=request.user.email,
                                                                                            email_data=context,
                                                                                            status=True)
            return redirect('domestic-transfer-success', request.session['token'])
#######
@method_decorator(login_required, name='dispatch')
@method_decorator(transaction_status, name='dispatch')
class DomesticTransferSuccess(View):
    def get(self,request,token):
        if request.GET.get("export_pdf"):
            response = {}
            invoice = f"transaction{request.session['domesticTransaction'].get('transactionno')}.pdf"
            context = {
                    'domestic_transfer' : True,
                    'transactionno':request.session['domesticTransaction']['transactionno'],
                    'transaction_datetime_utc':request.session['domesticTransaction']['transaction_datetime_utc'],
                    'sender_name':request.session['domesticTransaction']['sender_name'],
                    'from_currency_code':request.session['domesticTransaction']['from_currency_code'],
                    'fromaccount':request.session['domesticTransaction']['FromAccount'],
                    'beneficiary_accno':request.session['domesticTransaction']['BeneficiaryACNo'],
                    'beneficiary_name':request.session['domesticTransaction']['BeneficiaryName'],
                    'bank_name':request.session['domesticTransaction']['BankName'],
                    'routing_number':request.session['domesticTransaction']['RoutingNumber'],
                    'city':request.session['domesticTransaction']['City'],
                    'country':request.session['domesticTransaction']['Country'],
                    'currency':request.session['domesticTransaction']['Currency'],
                    'purpose_type':request.session['domesticTransaction']['PurposeType'],
                    'purpose_note':request.session['domesticTransaction']['PurposeNote'],
                    'email':request.session['domesticTransaction']['Email'],
                    'box_no':request.session['domesticTransaction']['Boxno'] if request.session['domesticTransaction'].get('Boxno') else None,
                    'street':request.session['domesticTransaction']['Street'] if request.session['domesticTransaction'].get('Street') else None,
                    'user_city':request.session['domesticTransaction']['userCity'] if request.session['domesticTransaction'].get('userCity') else None,
                    'state':request.session['domesticTransaction']['State'] if request.session['domesticTransaction'].get('State') else None,
                    'user_counrty':request.session['domesticTransaction']['userCountry'] if request.session['domesticTransaction'].get('userCountry') else None,
                    'phone_no':request.session['domesticTransaction']['Phoneno'] if request.session['domesticTransaction'].get('Phoneno') else None,
                    'amount':request.session['domesticTransaction']['Amount'],
                    'conversion_fee':request.session['domesticTransaction']['conversion_fee'],
                    'domestic_tr_fee': request.session['domesticTransaction']['domestic_transfer_fee'],
                    'cable_charge':request.session['domesticTransaction']['cable_charge'],
                    'debit_amount':request.session['domesticTransaction']['debit_amount'],
                    'credit_amount':request.session['domesticTransaction']['credit_amount'],
                    'note':request.session['domesticTransaction']['Note'],
                    'year':str(datetime.date.today().year),

                }
            try:
                context.update({
                    'invoice':request.session['invoice_document']['invoice_doc']
                })
            except Exception as e:
                logger.info(e)

                context.update({
                    'invoice':None
                })
            file = render_pdf('accounts/domestic_transaction/transaction-pdf-template.html', context, invoice)
            response['filepath'] = settings.AWS_S3_BUCKET_URL+'invoices/'+invoice
            return HttpResponse(json.dumps(response),content_type='application/json')
        else:
            if  token != request.session.get('token') or not token or not request.session['domesticTransaction']:
                logger.info(f"{request.user.email} generated token -{token} is not equal token from session -{request.session.get('token')}.re-direct to dashboard" )

                # logout here
                return redirect('/')
            if token == request.session.get('token'):
                return render(request, 'accounts/domestic_transaction/domestic-transaction-success.html')
    def post(self,request,token):
        user_account = Useraccounts.objects.get(customer__user=request.user)
        full_name = f"{user_account.firstname} {user_account.lastname}"
        email_data = {
                'user' : full_name.title(),
                'mail_attach' : True,
                'from_currency_code':request.session['domesticTransaction']['from_currency_code'],
                'amount':request.session['domesticTransaction']['Amount'],
                'year':str(datetime.date.today().year),
            }
        response = {}
        invoice = f"transaction{request.session['domesticTransaction'].get('transactionno')}.pdf"
        context = {
                'domestic_transfer' : True,
                'transactionno':request.session['domesticTransaction']['transactionno'],
                'transaction_datetime_utc':request.session['domesticTransaction']['transaction_datetime_utc'],
                'sender_name':request.session['domesticTransaction']['sender_name'],
                'from_currency_code':request.session['domesticTransaction']['from_currency_code'],
                'fromaccount':request.session['domesticTransaction']['FromAccount'],
                'beneficiary_accno':request.session['domesticTransaction']['BeneficiaryACNo'],
                'beneficiary_name':request.session['domesticTransaction']['BeneficiaryName'],
                'bank_name':request.session['domesticTransaction']['BankName'],
                'routing_number':request.session['domesticTransaction']['RoutingNumber'],
                'city':request.session['domesticTransaction']['City'],
                'country':request.session['domesticTransaction']['Country'],
                'currency':request.session['domesticTransaction']['Currency'],
                'purpose_type':request.session['domesticTransaction']['PurposeType'],
                'purpose_note':request.session['domesticTransaction']['PurposeNote'],
                'email':request.session['domesticTransaction']['Email'],
                'box_no':request.session['domesticTransaction']['Boxno'] if request.session['domesticTransaction'].get('Boxno') else None,
                'street':request.session['domesticTransaction']['Street'] if request.session['domesticTransaction'].get('Street') else None,
                'user_city':request.session['domesticTransaction']['userCity'] if request.session['domesticTransaction'].get('userCity') else None,
                'state':request.session['domesticTransaction']['State'] if request.session['domesticTransaction'].get('State') else None,
                'user_counrty':request.session['domesticTransaction']['userCountry'] if request.session['domesticTransaction'].get('userCountry') else None,
                'phone_no':request.session['domesticTransaction']['Phoneno'] if request.session['domesticTransaction'].get('Phoneno') else None,
                'amount':request.session['domesticTransaction']['Amount'],
                'conversion_fee':request.session['domesticTransaction']['conversion_fee'],
                'domestic_tr_fee':request.session['domesticTransaction']['domestic_transfer_fee'],
                'cable_charge':request.session['domesticTransaction']['cable_charge'],
                'debit_amount':request.session['domesticTransaction']['debit_amount'],
                'credit_amount':request.session['domesticTransaction']['credit_amount'],
                'note':request.session['domesticTransaction']['Note'],
                'year':str(datetime.date.today().year),

            }
        try:
            context.update({
                'invoice':request.session['invoice_document']['invoice_doc']
            })
        except Exception as e:
            logger.info(e)
            context.update({
                'invoice':None
            })
        file = render_pdf('accounts/domestic_transaction/transaction-pdf-template.html', context, invoice)
        response['filepath'] = settings.AWS_S3_BUCKET_URL+'invoices/'+invoice
        transaction_mail_status=TransactionMail().transaction_success_or_failure_mail(email=request.user.email,email_data=email_data,status=True, attach=file)
        context = {
            'status' : True,
            'message' : 'Mail sent successfully!'
        }
        return render(request, 'accounts/domestic_transaction/domestic-transaction-success.html',context)



@method_decorator(login_required, name='dispatch')
@method_decorator(template_decorator(title="International Wire Transfer"),name='dispatch')
@method_decorator(transaction_status, name='dispatch')
class InternationalWireTransfer(View):
    def get(self,request):
        if request.GET.get('Edit'):
            prevData = request.session['internationalTransaction']
            try:
                prevInvoice = request.session['invoice_document']
            except Exception as e:
                logger.info(e)
                prevInvoice = None
        else:
            if request.session.get('invoice_document'):
                del request.session['invoice_document'] 
            prevData = None
            prevInvoice = None
        accounts = Accounts.objects.filter(user_account__customer__user=request.user, isdeleted=False)
        currencies = Currencies.objects.filter(isdeleted=False)
        externalbeneficiaries = Externalbeneficiaries.objects.filter(createdby=request.user, isdeleted=False)
        transactionpurposetypes = Transactionpurposetype.objects.filter(isdeleted=False)
        countries = Countries.active.all().order_by('name')
        user_details = Useraccounts.objects.get(isdeleted=False,customer__user=request.user)
        context = {
            'accounts' : accounts,
            'currencies' : currencies,
            'countries' : countries,
            'externalbeneficiaries' : externalbeneficiaries,
            'transactionpurposetypes' : transactionpurposetypes,
            'prevData' : prevData,
            'prevInvoice' : prevInvoice,
            'user_details' : user_details
        }
        if request.session.get('cancelWireTrMsg'):
            context['message'] = request.session.get('cancelWireTrMsg')
            logger.info(f"{request.user.email} cancel international wire transfer")
            context['status'] = True
            del request.session['cancelWireTrMsg']
        if request.session.get('wireTrdeclinedMsg'):
            context['message'] = request.session.get('wireTrdeclinedMsg')
            context['status'] = False
            del request.session['wireTrdeclinedMsg']
        return render(request, 'accounts/wire_transfer/international-wire-transfer.html', context)

    def post(self,request):
        
        def context_function():
            prevData = request.POST.dict()
            accounts = Accounts.objects.filter(user_account__customer__user=request.user, isdeleted=False)
            currencies = Currencies.objects.filter(isdeleted=False)
            externalbeneficiaries = Externalbeneficiaries.objects.filter(createdby=request.user, isdeleted=False)
            transactionpurposetypes = Transactionpurposetype.objects.filter(isdeleted=False)
            countries = Countries.active.all().order_by('name')
            self.context = {
                'accounts' : accounts,
                'currencies' : currencies,
                'countries' : countries,
                'externalbeneficiaries' : externalbeneficiaries,
                'transactionpurposetypes' : transactionpurposetypes,
                'prevData' : prevData,
                'user_details' : Useraccounts.objects.get(isdeleted=False,customer__user=request.user)
            }
            return True
        if not request.POST.get('BeneficiaryACNo').isalnum():
            if context_function():
                self.context['message'] = 'Account number should not contain any special characters'
                self.context['status'] = False
                logger.info(f"{request.user.email} enter BeneficiaryACNo have special characters.BeneficiaryACNo contains only alphanumeric charachers")
                return render(request, 'accounts/wire_transfer/international-wire-transfer.html', self.context)
        email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if request.POST.get('Email') and not re.search(email_regex, request.POST.get('Email')):
            if context_function():
                self.context['message'] = 'Invalid Email'
                self.context['status'] = False
                logger.info(f"{request.user.email} entered invalid email {request.POST.get('Email')}")
                return render(request, 'accounts/wire_transfer/international-wire-transfer.html', self.context)
        phone_regex = r"^\+{0,1}[0-9]{10,13}"
        if request.POST.get('Phoneno') and not re.search(phone_regex, request.POST.get('Phoneno')):
            if context_function():
                self.context['message'] = 'Invalid Phone number'
                self.context['status'] = False
                logger.info(f"{request.user.email} entered invalid Phone number")
                return render(request, 'accounts/wire_transfer/international-wire-transfer.html', self.context)
        if request.FILES.get('invoice-doc'):
            ext = os.path.splitext(request.FILES.get('invoice-doc').name)[1]
            if not ext in settings.ALLOWED_FORMATS:
                if context_function():
                    self.context['message'] = 'Incorrect file format'
                    self.context['status'] = False
                    logger.info(f"{request.user.email} try to upload {request.FILES.get('invoice-doc').name}  Incorrect file format")
                    return render(request, 'accounts/wire_transfer/international-wire-transfer.html', self.context)
            elif not all(ord(c) < 128 for c in request.FILES.get('invoice-doc').name):
                if context_function():
                    self.context['message'] = 'Special characters should not be in file name'
                    self.context['status'] = False
                    logger.info(f"{request.user.email} uploaded invoice file name hve special characters.Special characters should not be in file name ")
                    return render(request, 'accounts/wire_transfer/international-wire-transfer.html', self.context)
        if not checkNonAsciiChracters([request.POST.get('Email'),request.POST.get('BankName'),
        request.POST.get('SwiftCode'),request.POST.get('City'),request.POST.get('Note'),request.POST.get('Boxno',''),
        request.POST.get('Street',''),request.POST.get('userCity',''),request.POST.get('State','')]):
            if context_function():
                    self.context['message'] = 'Fancy characters are not allowed'
                    self.context['status'] = False
                    logger.info(f"Fancy characters are not allowed")
                    return render(request, 'accounts/wire_transfer/international-wire-transfer.html', self.context)

        if request.session.get('internationalTransaction'):
            del request.session['internationalTransaction'] 
        if request.session.get('token'):
            del request.session['token']
        request.session['internationalTransaction'] = request.POST.dict()

        amount = round(Decimal(request.POST.get('Amount')),2)
        from_amount = amount
        from_account = Accounts.objects.get(accountno=request.POST.get('FromAccount'), isdeleted=False)
        from_account_balance = Decimal(from_account.balance)
        def conversion_charges(amount):
            if amount < 1000:
                self.wire_transfer_fee =Decimal(10.00) 
                self.cable_charge =Decimal(49.00)
                
            elif amount >= 1000 and amount <6900 :
                self.total_tr_charge =Decimal(69.00)
                self.wire_transfer_fee = round(amount * Decimal((1/100)),2)
                self.cable_charge =round(self.total_tr_charge - self.wire_transfer_fee,2)
                
            elif amount >=6900:
                self.wire_transfer_fee =round(amount * Decimal((1/100)),2)
                self.cable_charge =Decimal(0.00) 

        def conversion_rates(amount, from_currency_code,conversion_fee, wire_transfer_fee, cable_charge):
            
            to_dollar = Currencyconversionratescombined.objects.get(fromcurrency__code='USD',tocurrency__code=from_currency_code, isdeleted=False)
            currency_conversion = Currencyconversionratescombined.objects.get(fromcurrency__code=from_currency_code,tocurrency__code=request.POST.get('Currency'), isdeleted=False)
            
            conversionrate = round(currency_conversion.conversionrate,4)
            try:
                currency_margin = Currencyconversionmargins.objects.get(fromcurrency__code=from_currency_code,tocurrency__code=request.POST.get('Currency'),isdeleted=False)
                margin_rate = currency_margin.marginpercent
                conversionrate = conversionrate - (conversionrate* Decimal(float(margin_rate)/100))
            except Exception as e:
                logger.info(e)
                pass
            
            self.min_tr_amount = Decimal(100) * to_dollar.conversionrate
            self.conversion_fee = conversion_fee
            self.wire_transfer_fee = round(wire_transfer_fee * to_dollar.conversionrate,2)
            self.cable_charge = round(cable_charge * to_dollar.conversionrate,2)
            self.credit_amount = round(from_amount * conversionrate,2)
            self.conversionrate = conversionrate
        from_currency_code = from_account.currency.code
        if request.POST.get('Currency') == from_currency_code:
            if from_currency_code == 'USD':
                amount =Decimal(amount)
            else:
                to_dollar = Currencyconversionratescombined.objects.get(fromcurrency__code='USD',tocurrency__code=from_currency_code, isdeleted=False)
                amount =Decimal(amount) / to_dollar.conversionrate
            conversion_fee =Decimal(0.00)
            conversion_charges(amount)
        else:
            if from_currency_code == 'USD':
                amount =Decimal(amount)
            else:
                to_dollar = Currencyconversionratescombined.objects.get(fromcurrency__code='USD',tocurrency__code=from_currency_code, isdeleted=False)
                amount =Decimal(amount) / to_dollar.conversionrate
            conversion_fee = round(from_amount * Decimal(0.5/100),2)
            conversion_charges(amount)
        conversion_rates(amount, from_currency_code, conversion_fee, self.wire_transfer_fee, self.cable_charge)
        debit_amount = self.wire_transfer_fee + self.cable_charge + self.conversion_fee + from_amount
        commission_charges = round((self.wire_transfer_fee + self.cable_charge + self.conversion_fee),2)
        if from_account_balance < debit_amount:
            if context_function():
                self.context['message'] = "You don't have enough funds to make this transaction"
                self.context['status'] = False
                logger.info(f"{request.user.email}  account balance {from_account_balance}. so user don't have enough funds to make this transaction ")
                return render(request, 'accounts/wire_transfer/international-wire-transfer.html', self.context)
        elif from_amount < self.min_tr_amount:
            if context_function():
                self.context['message'] = f'Minimum amount required for the transaction is {format(self.min_tr_amount, ".2f")} {from_currency_code}'
                self.context['status'] = False
                logger.info(f"the amount {from_amount} to be transaction is lowerthan  Minimum amount. {self.min_tr_amount} required for the transaction ")
                return render(request, 'accounts/wire_transfer/international-wire-transfer.html', self.context)
        is_ext_ben = Externalbeneficiaries.objects.filter(Q(accountnumber=request.POST.get('BeneficiaryACNo')) | Q(name=request.POST.get('BeneficiaryName')),isdeleted=False,createdby=request.user).exists()
        request.session['internationalTransaction'].update({
                'cable_charge' : format(self.cable_charge, ".2f"),
                'wire_transfer_fee' : format(self.wire_transfer_fee, ".2f"),
                'conversion_fee' : format(self.conversion_fee, ".2f"),
                'debit_amount' : format(debit_amount, ".2f"),
                'commission_charges' : format(commission_charges, ".2f"),
                'credit_amount' : format(self.credit_amount, ".2f"),
                'from_currency_code' : from_currency_code,
                'recipient_currency_code' : request.POST.get('Currency'),
                'conversionrate' : format(self.conversionrate, ".2f"),
                'is_ext_ben' : is_ext_ben,
                })

        try:
            if  request.POST.get('companyTr') == 'on' and request.FILES.get('invoice-doc'):
                invoice_file=InvoiceDocument.objects.create(invoice_doc=request.FILES.get('invoice-doc'))
                request.session['invoice_document'] = {
                'invoice_doc' : request.FILES['invoice-doc'].name,
                'invoice_doc_id' : invoice_file.id
                }
            elif not request.POST.get('companyTr') and not request.FILES.get('invoice-doc') and request.session['invoice_document']:
                del request.session['invoice_document']
        except Exception as e:
            logger.info(f"No file was uploaded! -> {e}")
        
        request.session['token'] = token_urlsafe(30)
        return redirect('wire-transfer-confirm', request.session['token'])

@method_decorator(login_required, name='dispatch')
@method_decorator(transaction_status, name='dispatch')
class WireTransferConfirm(View):
    def get(self,request,token):
        if  not token or token != request.session.get('token') or not request.session['internationalTransaction']:
            logger.info(f"{request.user.email} generated token -{token} is not equal token from session -{request.session.get('token')}.re-direct to dashboard" )
            # logout here
            return redirect('/')
        if token == request.session.get('token'):
            return render(request,'accounts/wire_transfer/wire-transfer-confirm.html')
    def post(self, request,token):
        if request.POST.get('action_type') == 'resent otp' :
            user_account = Useraccounts.objects.get(customer__user=request.user)
            full_name = f"{user_account.firstname} {user_account.lastname}"
            otp_status = OTP()
            if request.session.get('prevToken'):
                del request.session['prevToken']
            request.session['prevToken'] = request.session['token']
            # del request.session['token']
            # request.session['token'] = token_urlsafe(30)
            return JsonResponse({
                'message' : 'OTP sent, Please verify!'
                })

        elif request.POST.get('otp_sent') == 'otp_sent':
            if token == request.session.get('token'):
                if  request.POST.get('save_ben') == 'on':
                    external_ben, status = Externalbeneficiaries.objects.get_or_create(
                        name = request.session['internationalTransaction']['BeneficiaryName'],
                        accountnumber = request.session['internationalTransaction']['BeneficiaryACNo'],
                        currency = Currencies.objects.get(code=request.session['internationalTransaction']['Currency']),
                        swiftcode = request.session['internationalTransaction']['SwiftCode'],
                        country = Countries.objects.get(name=request.session['internationalTransaction']['Country']),
                        city = request.session['internationalTransaction']['City'],
                        account_type = request.session['internationalTransaction']['AccountType'],
                        bankname = request.session['internationalTransaction']['BankName'],
                        createdby = request.user,
                        customer = Customers.objects.get(user=request.user)
                    )
                    external_ben.email = request.session['internationalTransaction']['Email']
                    external_ben.save()
                user_account = Useraccounts.objects.get(customer__user=request.user)
                full_name = f"{user_account.firstname} {user_account.lastname}"
                otp_status = OTP()
                if otp_status:
                    messages.success(request,'OTP sent, Please verify!')
                    if request.session.get('prevToken'):
                        del request.session['prevToken']
                    request.session['prevToken'] = request.session['token']
                    del request.session['token']
                    request.session['token'] = token_urlsafe(30)
                    return redirect('international-wire-transfer-wireOtp', request.session['token'])
                else:
                    messages.error(request,'Could not send OTP')
                    return redirect('wire-transfer-confirm', request.session['token'])
            else:
                logger.info(f"{request.user.email} generated token -{token} is not equal token from session -{request.session.get('token')}.re-direct to dashboard" )
                # logout here
                return redirect('/')

@method_decorator(login_required, name='dispatch')
@method_decorator(transaction_status, name='dispatch')
class WireTransferOtp(View):
    def get(self, request, token):
        if not token or  token != request.session.get('token') or not request.session['internationalTransaction']:
            logger.info(f"{request.user.email} generated token -{token} is not equal token from session -{request.session.get('token')}.re-direct to dashboard" )
            # logout here
            return redirect('/')
        if  token == request.session.get('token'):
            return render(request, 'accounts/wire_transfer/wire-transfer-otp.html')
    def post(self, request, token):
        def validation_fn():
            if token != request.session.get('token'):
                logger.info(f"{request.user.email} generated token -{token} is not equal token from session - {request.session.get('token')}.re-direct to dashboard" )
                return {
                    'status' : False,
                    'error' : 'Your Transaction has been declined due to Security reason'
                }

            try:
                otp = Otps.objects.get(code=request.POST.get('otp'),
                                transactiontype='International Wire Transfer',
                                validated=False,
                                createdby=request.user,token=request.session['prevToken'],isdeleted=False)
                transaction_lock_fn(request,is_lock=False)
            except Exception as e:
                logger.info(e)
                transaction_state = transaction_lock_fn(request)
                return {
                    'otp_error' : True,
                    'status' : False,
                    'error' : transaction_state.get("message")
                    }
            valid_till = datetime.datetime.now()
            valid_till = valid_till.date().strftime(settings.DATE_FORMAT)
            valid_date = datetime.datetime.strptime(valid_till, settings.DATE_FORMAT)
            # if valid_till <= otp.validtill:
            if valid_date.date() <= otp.validtill:
                otp.validated = True
                otp.save()
            else:
                logger.info(f"{request.user.email} entered otp invalid or it expired otp")
                return {
                    'otp_error' : True,
                    'status' : False,
                    'error' : 'Verification failed, expired otp'
                }
            try:
                customer_type = Customers.objects.get(user=request.user,isdeleted=False).customertype
                if customer_type == 1:
                    user = Useraccounts.objects.get(customer__user=request.user, isdeleted=False)
                    sender_name = f'{user.firstname} {user.lastname}'
                else:
                    sender_name = Businessdetails.objects.get(customer__user=request.user,isdeleted=False).companyname
            except Exception as e:
                logger.info(e)
                return {
                    'status' : False,
                    'error' : 'Your Transaction has been declined due to invalid Customer or Business details'
                }
            request.session['internationalTransaction'].update({
                'sender_name' : sender_name
                    })
            
            try:
                # last_transactionno = Transactions.objects.latest('id').id + 10000000
                last_transactionno = Transactions.objects.latest('transactionno').transactionno
            except Exception as e:
                logger.info(e)
                last_transactionno = 10000000

            def transaction_fn(last_transactionno, fromamount,charge,parent_tr=None,toamount=None, inl_tr=None, commission_charges=None,cable_charge=None,last_transaction=None):
                try:
                    try:
                        # account = Accounts.objects.get(createdby=request.user, accountno=request.session['internationalTransaction']['FromAccount'],isdeleted=False)
                        account = Accounts.objects.get(accountno=request.session['internationalTransaction']['FromAccount'],isdeleted=False)
                    except Exception as e:
                        logger.info(e)
                        return {
                        'status' : False,
                        'error' : 'Your Transaction has been declined due to invalid source account'
                    }
                    if account.balance < Decimal(fromamount):
                        raise Exception()
                    account_balance = account.balance - Decimal(fromamount)
                    account.balance = account_balance
                    account.save()
                except Exception as e:
                    logger.info(e)
                    return {
                        'status' : False,
                        'error' : 'Your Transaction has been declined due to insufficient fund'
                    }
                if cable_charge:
                    cablecharge_obj = Cablecharges.objects.create(
                                parenttransaction=parent_transaction,
                                chargeamount=Decimal(request.session['internationalTransaction']['cable_charge']),
                                currency=Currencies.objects.get(code=request.session['internationalTransaction']['Currency'], isdeleted=False),
                                createdby=request.user,
                                transaction=last_transaction
                            )
                    add_log_action(request, cablecharge_obj, status=f'cable charge created for transaction {parent_transaction.transactionno}', status_id=1)
                    return {
                        'status' : True,
                    }

                else:
                    if commission_charges:
                        try:
                            toaccount = Accounts.objects.get(user_account__ismaster_account=True,currency__code=request.session['internationalTransaction']['from_currency_code'],isdeleted=False)
                        except Exception as e:
                            logger.info(e)
                            toaccount = None
                    else:
                        toaccount = None

                    to_account_balance = None
                    charge_type = None
                    if charge == 1:
                        charge_type = 'Net Amount'
                    elif charge == 2:
                        charge_type = 'Conversion Fee'
                    elif charge == 3:
                        charge_type = 'Wire Transfer Fee'
                    try:
                        self.transaction=Transactions.objects.create(
                                                    transactionno=int(last_transactionno)+1,
                                                    # fromaccount=Accounts.objects.get(user_account__customer__user=request.user,accountno=request.session['internationalTransaction']['FromAccount'], isdeleted=False),
                                                    fromaccount=Accounts.objects.get(accountno=request.session['internationalTransaction']['FromAccount'], isdeleted=False),
                                                    toaccount=None,
                                                    fromamount=fromamount,
                                                    toamount=toamount,
                                                    initiatedby=request.user,
                                                    transactiontype=Transactiontypes.objects.get(name='Third Party Transfer'),
                                                    createdby=request.user,
                                                    note=request.session['internationalTransaction']['Note'],
                                                    recipientname=request.session['internationalTransaction']['BeneficiaryName'],
                                                    conversionrate = request.session.get('internationalTransaction').get('conversionrate'),
                                                    fromaccountbalance=account_balance,
                                                    toaccountbalance=to_account_balance,
                                                    parenttransaction=parent_tr,
                                                    amount_type = charge_type,
                                                    affiliate_fee_percentage = Customers.objects.get(isdeleted=False,user=request.user).outgoingtansactionfee
                                                    )
                        add_log_action(request, self.transaction, status=f"transaction(International Wire transfer : amount type {self.transaction.amount_type}) created for account {str(self.transaction.fromaccount.accountno)}", status_id=1)
                        if inl_tr:
                            try:
                                invoice_doc=InvoiceDocument.objects.get(id=request.session['invoice_document']['invoice_doc_id'])
                                
                                invoice_doc.transaction=self.transaction
                                invoice_doc.save()
                            except Exception as e:
                                logger.info(e)
                                pass
                            inl_tr = Internationaltransactions.objects.create(
                                                        transaction=self.transaction,
                                                        bankname=request.session['internationalTransaction']['BankName'],
                                                        swiftcode=request.session['internationalTransaction']['SwiftCode'],
                                                        accountnumber=request.session['internationalTransaction']['BeneficiaryACNo'],
                                                        accountholdername=request.session['internationalTransaction']['BeneficiaryName'],
                                                        currency=Currencies.objects.get(code=request.session['internationalTransaction']['Currency'], isdeleted=False),
                                                        createdby=request.user,
                                                        city=request.session['internationalTransaction']['City'],
                                                        country=Countries.objects.get(name=request.session['internationalTransaction']['Country']),
                                                        email=request.session['internationalTransaction']['Email'],
                                                        purpose=Transactionpurposetype.objects.get(transactionpurpose=request.session['internationalTransaction']['PurposeType'], isdeleted=False),
                                                        other_purpose_note=request.session['internationalTransaction']['PurposeNote'],
                                                        user_box_no=request.session['internationalTransaction']['Boxno'] if request.session['internationalTransaction'].get('Boxno') else None,
                                                        user_street=request.session['internationalTransaction']['Street'] if request.session['internationalTransaction'].get('Street') else None,
                                                        user_city=request.session['internationalTransaction']['userCity'] if request.session['internationalTransaction'].get('userCity') else None,
                                                        user_state=request.session['internationalTransaction']['State'] if request.session['internationalTransaction'].get('State') else None,
                                                        user_country=Countries.objects.get(name=request.session['internationalTransaction']['userCountry']) if request.session['internationalTransaction'].get('userCountry') else None,
                                                        user_phone=request.session['internationalTransaction']['Phoneno'] if request.session['internationalTransaction'].get('Phoneno') else None
                                                        )
                            add_log_action(request, inl_tr, status=f'international transaction created for account {str(self.transaction.fromaccount.accountno)}', status_id=1)
                    except Exception as e:
                        logger.info(e)
                        return {
                            'status' : False,
                            'error' : 'Your Transaction has been declined due to some error'
                        }
            response = transaction_fn(last_transactionno, request.session['internationalTransaction']['Amount'],toamount=request.session['internationalTransaction']['credit_amount'], charge=1, inl_tr= True)
            if response and not response.get('status'):
                return response
            parent_transaction =  self.transaction
            charge = 3
            response = transaction_fn(last_transactionno, request.session['internationalTransaction']['wire_transfer_fee'], charge, parent_transaction,toamount=request.session['internationalTransaction']['wire_transfer_fee'], commission_charges=True)
            if response and not response.get('status'):
                return response
            charge = 2
            response = transaction_fn(last_transactionno, request.session['internationalTransaction']['conversion_fee'], charge,parent_transaction,toamount=request.session['internationalTransaction']['conversion_fee'], commission_charges=True)
            if response and not response.get('status'):
                return response
            last_transaction =  self.transaction
            # 
            response = transaction_fn(last_transactionno, request.session['internationalTransaction']['cable_charge'],parent_transaction, cable_charge=True, last_transaction=last_transaction)
            if response and not response.get('status'):
                return response
            # cable_charge_fn(parent_transaction, last_transaction)
            request.session['internationalTransaction'].update({
                'transactionno' : parent_transaction.transactionno,
                'transaction_id' : parent_transaction.id,
                'transaction_datetime_utc' : datetime.datetime.utcnow().strftime("%d %b %Y, %-H:%M UTC"),
            })
            if request.session['prevToken']:
                del request.session['prevToken']
            if request.session.get('token'):
                del request.session['token']
                request.session['token'] = token_urlsafe(30)
            return {
                        'status' : True,
                    }

        response = validation_fn()
        if response and not response.get('status'):
            if response.get('otp_error') == True:
                context = {
                    'statust' : False,
                    'message' : response.get('error')
                }
                return render(request, 'accounts/wire_transfer/wire-transfer-otp.html',context)
            # messages.error(request,response.get('error'))
            user_account = Useraccounts.objects.get(customer__user=request.user)
            full_name = f"{user_account.firstname} {user_account.lastname}"
            context = {
                'user' : full_name.title(), 
                'error' : True,
                'message' : response.get('error'),
                'year':str(datetime.date.today().year),
            }
            transaction_mail_status=TransactionMail().transaction_success_or_failure_mail(email=request.user.email,email_data=context,status=False)
            request.session['wireTrdeclinedMsg'] = response.get('error')
            logger.info(f"{request.user.email} transaction declained redirect to international wire transfer page")
            return redirect('international-wire-transfer')
        elif response.get('status'):
            customer_account = Useraccounts.objects.get(customer__user=request.user)
            context = {
                    'wire_transfer' : True,
                    'wire_transfer_success' : True,
                    'test_user' : customer_account.test_account,
                    'transactionno':request.session['internationalTransaction']['transactionno'],
                    'transaction_datetime_utc':request.session['internationalTransaction']['transaction_datetime_utc'],
                    'sender_name':request.session['internationalTransaction']['sender_name'],
                    'from_currency_code':request.session['internationalTransaction']['from_currency_code'],
                    'fromaccount':request.session['internationalTransaction']['FromAccount'],
                    'beneficiary_accno':request.session['internationalTransaction']['BeneficiaryACNo'],
                    'beneficiary_name':request.session['internationalTransaction']['BeneficiaryName'],
                    'bank_name':request.session['internationalTransaction']['BankName'],
                    'swift_code':request.session['internationalTransaction']['SwiftCode'],
                    'city':request.session['internationalTransaction']['City'],
                    'country':request.session['internationalTransaction']['Country'],
                    'currency':request.session['internationalTransaction']['Currency'],
                    'purpose_type':request.session['internationalTransaction']['PurposeType'],
                    'purpose_note':request.session['internationalTransaction']['PurposeNote'],
                    'email':request.session['internationalTransaction']['Email'],
                    'box_no':request.session['internationalTransaction']['Boxno'] if request.session['internationalTransaction'].get('Boxno') else None,
                    'street':request.session['internationalTransaction']['Street'] if request.session['internationalTransaction'].get('Street') else None,
                    'user_city':request.session['internationalTransaction']['userCity'] if request.session['internationalTransaction'].get('userCity') else None,
                    'state':request.session['internationalTransaction']['State'] if request.session['internationalTransaction'].get('State') else None,
                    'user_counrty':request.session['internationalTransaction']['userCountry'] if request.session['internationalTransaction'].get('userCountry') else None,
                    'phone_no':request.session['internationalTransaction']['Phoneno'] if request.session['internationalTransaction'].get('Phoneno') else None,
                    'amount':request.session['internationalTransaction']['Amount'],
                    'conversion_fee':request.session['internationalTransaction']['conversion_fee'],
                    'wire_tr_fee':request.session['internationalTransaction']['wire_transfer_fee'],
                    'cable_charge':request.session['internationalTransaction']['cable_charge'],
                    'debit_amount':request.session['internationalTransaction']['debit_amount'],
                    'credit_amount':request.session['internationalTransaction']['credit_amount'],
                    'note':request.session['internationalTransaction']['Note'],
                    'year':str(datetime.date.today().year),

                }
            try:
                context.update({
                    'invoice':request.session['invoice_document']['invoice_doc']
                })
            except Exception as e:
                logger.info(e)
                context.update({
                    'invoice':None
                })
            transaction_mail_status=TransactionMail().transaction_success_or_failure_mail(email=request.user.email,email_data=context,status=True)
            return redirect('international-wire-transfer-success',request.session['token'])

@method_decorator(login_required, name='dispatch')
@method_decorator(transaction_status, name='dispatch')
class WireTransactionInvoiceMail(View):
    def get(self, request, token):
        user_account = Useraccounts.objects.get(customer__user=request.user)
        full_name = f"{user_account.firstname} {user_account.lastname}"
        context = {
                'user' : full_name.title(), 
                'mail_attach' : True,
                'from_currency_code':request.session['internationalTransaction']['from_currency_code'],
                'amount':request.session['internationalTransaction']['Amount'],
                'year':str(datetime.date.today().year),
            }
        transaction_mail_status=TransactionMail().transaction_success_or_failure_mail(email=request.user.email,email_data=context,status=True, attach=True)
        return redirect('international-wire-transfer-success',token)


@method_decorator(login_required, name='dispatch')
@method_decorator(transaction_status, name='dispatch')
class WireTransferSuccess(View):
    def get(self,request,token):
        if request.GET.get("export_pdf"):
            response = {}
            invoice = f"transaction{request.session['internationalTransaction'].get('transactionno')}.pdf"
            context = {
                    'wire_transfer' : True,
                    'transactionno':request.session['internationalTransaction']['transactionno'],
                    'transaction_datetime_utc':request.session['internationalTransaction']['transaction_datetime_utc'],
                    'sender_name':request.session['internationalTransaction']['sender_name'],
                    'from_currency_code':request.session['internationalTransaction']['from_currency_code'],
                    'fromaccount':request.session['internationalTransaction']['FromAccount'],
                    'beneficiary_accno':request.session['internationalTransaction']['BeneficiaryACNo'],
                    'beneficiary_name':request.session['internationalTransaction']['BeneficiaryName'],
                    'bank_name':request.session['internationalTransaction']['BankName'],
                    'swift_code':request.session['internationalTransaction']['SwiftCode'],
                    'city':request.session['internationalTransaction']['City'],
                    'country':request.session['internationalTransaction']['Country'],
                    'currency':request.session['internationalTransaction']['Currency'],
                    'purpose_type':request.session['internationalTransaction']['PurposeType'],
                    'purpose_note':request.session['internationalTransaction']['PurposeNote'],
                    'email':request.session['internationalTransaction']['Email'],
                    'box_no':request.session['internationalTransaction']['Boxno'] if request.session['internationalTransaction'].get('Boxno') else None,
                    'street':request.session['internationalTransaction']['Street'] if request.session['internationalTransaction'].get('Street') else None,
                    'user_city':request.session['internationalTransaction']['userCity'] if request.session['internationalTransaction'].get('userCity') else None,
                    'state':request.session['internationalTransaction']['State'] if request.session['internationalTransaction'].get('State') else None,
                    'user_counrty':request.session['internationalTransaction']['userCountry'] if request.session['internationalTransaction'].get('userCountry') else None,
                    'phone_no':request.session['internationalTransaction']['Phoneno'] if request.session['internationalTransaction'].get('Phoneno') else None,
                    'amount':request.session['internationalTransaction']['Amount'],
                    'conversion_fee':request.session['internationalTransaction']['conversion_fee'],
                    'wire_tr_fee':request.session['internationalTransaction']['wire_transfer_fee'],
                    'cable_charge':request.session['internationalTransaction']['cable_charge'],
                    'debit_amount':request.session['internationalTransaction']['debit_amount'],
                    'credit_amount':request.session['internationalTransaction']['credit_amount'],
                    'note':request.session['internationalTransaction']['Note'],
                    'year':str(datetime.date.today().year),

                }
            try:
                context.update({
                    'invoice':request.session['invoice_document']['invoice_doc']
                })
            except Exception as e:
                logger.info(e)

                context.update({
                    'invoice':None
                })
            file = render_pdf('accounts/wire_transfer/transaction-pdf-template.html', context, invoice)
            response['filepath'] = settings.AWS_S3_BUCKET_URL+'invoices/'+invoice
            return HttpResponse(json.dumps(response),content_type='application/json')
        else:
            if  token != request.session.get('token') or not token or not request.session['internationalTransaction']:
                logger.info(f"{request.user.email} generated token -{token} is not equal token from session -{request.session.get('token')}.re-direct to dashboard" )

                # logout here
                return redirect('/')
            if token == request.session.get('token'):
                return render(request, 'accounts/wire_transfer/wire-transaction-success.html')
    def post(self,request,token):
        user_account = Useraccounts.objects.get(customer__user=request.user)
        full_name = f"{user_account.firstname} {user_account.lastname}"
        email_data = {
                'user' : full_name.title(), 
                'mail_attach' : True,
                'from_currency_code':request.session['internationalTransaction']['from_currency_code'],
                'amount':request.session['internationalTransaction']['Amount'],
                'year':str(datetime.date.today().year),
            }
        response = {}
        invoice = f"transaction{request.session['internationalTransaction'].get('transactionno')}.pdf"
        context = {
                'wire_transfer' : True,
                'transactionno':request.session['internationalTransaction']['transactionno'],
                'transaction_datetime_utc':request.session['internationalTransaction']['transaction_datetime_utc'],
                'sender_name':request.session['internationalTransaction']['sender_name'],
                'from_currency_code':request.session['internationalTransaction']['from_currency_code'],
                'fromaccount':request.session['internationalTransaction']['FromAccount'],
                'beneficiary_accno':request.session['internationalTransaction']['BeneficiaryACNo'],
                'beneficiary_name':request.session['internationalTransaction']['BeneficiaryName'],
                'bank_name':request.session['internationalTransaction']['BankName'],
                'swift_code':request.session['internationalTransaction']['SwiftCode'],
                'city':request.session['internationalTransaction']['City'],
                'country':request.session['internationalTransaction']['Country'],
                'currency':request.session['internationalTransaction']['Currency'],
                'purpose_type':request.session['internationalTransaction']['PurposeType'],
                'purpose_note':request.session['internationalTransaction']['PurposeNote'],
                'email':request.session['internationalTransaction']['Email'],
                'box_no':request.session['internationalTransaction']['Boxno'] if request.session['internationalTransaction'].get('Boxno') else None,
                'street':request.session['internationalTransaction']['Street'] if request.session['internationalTransaction'].get('Street') else None,
                'user_city':request.session['internationalTransaction']['userCity'] if request.session['internationalTransaction'].get('userCity') else None,
                'state':request.session['internationalTransaction']['State'] if request.session['internationalTransaction'].get('State') else None,
                'user_counrty':request.session['internationalTransaction']['userCountry'] if request.session['internationalTransaction'].get('userCountry') else None,
                'phone_no':request.session['internationalTransaction']['Phoneno'] if request.session['internationalTransaction'].get('Phoneno') else None,
                'amount':request.session['internationalTransaction']['Amount'],
                'conversion_fee':request.session['internationalTransaction']['conversion_fee'],
                'wire_tr_fee':request.session['internationalTransaction']['wire_transfer_fee'],
                'cable_charge':request.session['internationalTransaction']['cable_charge'],
                'debit_amount':request.session['internationalTransaction']['debit_amount'],
                'credit_amount':request.session['internationalTransaction']['credit_amount'],
                'note':request.session['internationalTransaction']['Note'],
                'year':str(datetime.date.today().year),

            }
        try:
            context.update({
                'invoice':request.session['invoice_document']['invoice_doc']
            })
        except Exception as e:
            logger.info(e)
            context.update({
                'invoice':None
            })
        file = render_pdf('accounts/wire_transfer/transaction-pdf-template.html', context, invoice)
        response['filepath'] = settings.AWS_S3_BUCKET_URL+'invoices/'+invoice
        transaction_mail_status=TransactionMail().transaction_success_or_failure_mail(email=request.user.email,email_data=email_data,status=True, attach=file)
        context = {
            'status' : True,
            'message' : 'Mail sent successfully!'
        }
        return render(request, 'accounts/wire_transfer/wire-transaction-success.html',context)


@method_decorator(login_required, name='dispatch')
@method_decorator(transaction_status, name='dispatch')
class CancelWireTransfer(View):
    def get(self,request):
        if request.session.get('internationalTransaction'):
            del request.session['internationalTransaction']
        if request.session.get('token'):
            del request.session['token']
        if request.session.get('invoice_document'):
            del request.session['invoice_document'] 
        request.session['cancelWireTrMsg'] = 'Last transaction canceled'

        return redirect('international-wire-transfer/')


def cutomer_account_balance(request):
    # customer_account = Accounts.objects.get(user_account__customer__user=request.user,
    # accountno=request.POST.get('accountno'), isdeleted=False)
    customer_account = Accounts.objects.get(accountno=request.POST.get('accountno'), isdeleted=False)
    customer_account_balance = customer_account.balance
    customer_account_currency_code = customer_account.currency.code
    data = {
        'customer_account_balance':round(customer_account_balance,2),
        'customer_account_currency_code':customer_account_currency_code,
    }
    return JsonResponse(data)

@method_decorator(login_required, name='dispatch')
class ShowUserDetails(View):
    def post(self, request):
        context = {}
        context['countries'] = Countries.active.all().order_by('name')
        template = render_to_string('accounts/wire_transfer/user-details.html',context)
        response = {'user_details' : template}
        return JsonResponse(response)


def getbeneficiarylist(request):
    external_beneficiary = Externalbeneficiaries.objects.get(createdby=request.user, accountnumber=request.POST.get('beneficiary_accountnumber'), isdeleted=False)
    data = {
        'accountnumber' : external_beneficiary.accountnumber if external_beneficiary.accountnumber else None,
        'currency' : external_beneficiary.currency.code if external_beneficiary.currency else None,
        'swiftcode' : external_beneficiary.swiftcode if external_beneficiary.swiftcode else None,
        'bankname' : external_beneficiary.bankname if external_beneficiary.bankname else None,
        'countrycode' : external_beneficiary.country.name if external_beneficiary.country else None,
        'city' : external_beneficiary.city if external_beneficiary.city else None,
        'name' : external_beneficiary.name if external_beneficiary.name else None,
        'account_type': external_beneficiary.account_type if external_beneficiary.account_type else None,
        
    }
    return JsonResponse(data)


def getdombeneficiarylist(request):
    external_beneficiary = DomesticBeneficiary.objects.get(createdby=request.user, domestic_accountnumber=request.POST.get(
        'beneficiary_accountnumber'), isdeleted=False)
    data = {
        'accountnumber': external_beneficiary.domestic_accountnumber if external_beneficiary.domestic_accountnumber else None,
        'currency': external_beneficiary.currency.code if external_beneficiary.currency else None,
        'RoutingNumber': external_beneficiary.routing_number if external_beneficiary.routing_number else None,
        'bankname': external_beneficiary.domestic_bankname if external_beneficiary.domestic_bankname else None,
        'countrycode': external_beneficiary.country.name if external_beneficiary.country else None,
        'city': external_beneficiary.domestic_city if external_beneficiary.domestic_city else None,
        'name': external_beneficiary.domestic_name if external_beneficiary.domestic_name else None,
        'account_type': external_beneficiary.account_type if external_beneficiary.account_type else None,

    }
    return JsonResponse(data)

def getcryptobeneficiarylist(request):
    crypto_beneficiary = Cryptobeneficiaries.objects.get(createdby=request.user, name=request.POST.get('beneficiary_accountnumber'), isdeleted=False)
    data = {
        'beneficiaryName' : crypto_beneficiary.name if crypto_beneficiary.name else None,
        'currency' : crypto_beneficiary.currency.code if crypto_beneficiary.currency else None,
        'Walletname' : crypto_beneficiary.wallet_name if crypto_beneficiary.wallet_name else None,
        'name' : crypto_beneficiary.name if crypto_beneficiary.name else None
    }
    return JsonResponse(data)


def render_pdf(path, params, filename,filepath=None):
    template = get_template(path)
    html = template.render(params)
    if not filepath:
        filepath = 'invoices/'
    filepath = settings.MEDIA_ROOT + settings.MEDIA_URL+ filepath
    create_directory(filepath)
    upload_filename = filename
    filename = filepath + filename
    pdf = pdfkit.from_string(html, filename)
    fileToUpload = open(filename)
    cloudpath = 'invoices/' + upload_filename
    path_to_file = UtilMixins().upload_to_s3(fileToUpload,cloudpath)
    return filename


def create_directory(path):
    import os

    # Check whether the specified path exists or not
    isExist = os.path.exists(path)

    if not isExist:
        # Create a new directory because it does not exist
        os.makedirs(path)
    return True


@method_decorator(login_required, name='dispatch')
@method_decorator(template_decorator(title="Entrebiz"),name='dispatch')
@method_decorator(transaction_status, name='dispatch')
class CurrencyConversionView(View,OTP):
    def get(self,request):
        context = {}
        if request.session.get('currency_conversion') and not request.session.get('is_edit'):
            del request.session['currency_conversion']
        if request.session.get('is_edit'):
            del request.session['is_edit']
        if request.session.get('tr_cancel_message'):
            context['status'] = True
            context['message'] = request.session.get('tr_cancel_message')
            del request.session['tr_cancel_message']
        accounts = Accounts.objects.filter(user_account__customer__user=request.user, isdeleted=False)
        user_details = Useraccounts.active.get(customer__user=request.user,isdeleted=False)
        context['accounts'] = accounts
        context['user_details'] = user_details
        return render(request,'transactions/currency_conversion/select_currencies.html',context)

    def post(self,request):
        context = json.loads(json.dumps(request.POST))

        debit_account = Accounts.objects.get(accountno=request.POST.get("debit_account"))
        debit_acc_no = debit_account.accountno
        debit_acc_curr_code = debit_account.currency.code
        credit_account = Accounts.objects.get(accountno=request.POST.get("credit_account"))
        credit_acc_no = credit_account.accountno
        credit_acc_curr_code = credit_account.currency.code
        net_amount = round(Decimal(request.POST.get("net_amount")),2)
        note = request.POST.get("note")
        conversion_fee = round(net_amount * Decimal(0.5 / 100),2)
        debit_amount = net_amount + conversion_fee
        if request.POST.get("debit_account") == request.POST.get("credit_account"):
            accounts = Accounts.objects.filter(user_account__customer__user=request.user, isdeleted=False)
            context['accounts'] = accounts
            context['balance'] = str(round(debit_account.balance, 2))
            context['debit_acc_curr_code'] = debit_acc_curr_code
            context['status'] = False
            context['message'] = "Both accounts cannot be the same!"
            return render(request, 'transactions/currency_conversion/select_currencies.html', context)
        if debit_amount > debit_account.balance:
            accounts = Accounts.objects.filter(user_account__customer__user=request.user, isdeleted=False)
            context['accounts'] = accounts
            context['balance'] = str(round(debit_account.balance,2))
            context['debit_acc_curr_code'] = debit_acc_curr_code
            context['status'] = False
            context['user_details'] = Useraccounts.objects.get(customer__user=request.user,isdeleted=False)
            context['message'] = "Insufficient Balance"
            return render(request, 'transactions/currency_conversion/select_currencies.html', context)
        if not checkNonAsciiChracters(note):
            accounts = Accounts.objects.filter(user_account__customer__user=request.user, isdeleted=False)
            context['accounts'] = accounts
            context['balance'] = str(round(debit_account.balance,2))
            context['debit_acc_curr_code'] = debit_acc_curr_code
            context['status'] = False
            context['user_details'] = Useraccounts.objects.get(customer__user=request.user,isdeleted=False)
            context['message'] = "Fancy Characters are not allowed"
            return render(request, 'transactions/currency_conversion/select_currencies.html', context)
        currency_conversion = Currencyconversionratescombined.objects.get(fromcurrency__code=debit_acc_curr_code,
                                                                          tocurrency__code=credit_acc_curr_code,
                                                                          isdeleted=False)
        token = token_urlsafe(30)
        conversionrate = round(currency_conversion.conversionrate,4)
        
        try:
            currency_margin = Currencyconversionmargins.objects.get(fromcurrency__code=debit_acc_curr_code,tocurrency__code=credit_acc_curr_code,isdeleted=False)
            margin_rate = currency_margin.marginpercent
            conversionrate = conversionrate - (conversionrate* Decimal(float(margin_rate)/100))
        except Exception as e:
            logger.info(e)
            pass
        credit_amount = round(net_amount * conversionrate,2)
        conversion_details = {
            'debit_acc_no':debit_acc_no,
            'balance':str(round(debit_account.balance,4)),
            'debit_acc_curr_code':debit_acc_curr_code,
            'credit_acc_no':credit_acc_no,
            'credit_acc_curr_code':credit_acc_curr_code,
            'conversionrate':str(round(conversionrate,4)),
            'net_amount':str(net_amount),
            'note':note,
            'conversion_fee':str(conversion_fee),
            'debit_amount':str(debit_amount),
            'credit_amount':str(credit_amount),
            'token':token,
        }

        request.session['currency_conversion'] = context
        request.session['currency_conversion'].update(conversion_details)
        request.session['curr_conv_otp_message'] = "OTP sent, Please verify!"
        return redirect(f'/conversionConfirm?accessToken={token}')


@method_decorator(login_required, name='dispatch')
@method_decorator(transaction_status, name='dispatch')
class CurrencyConversionConfirmView(View,TransactionMail,OTP,FindAccount):
    def get(self,request):
        if not request.session.get('currency_conversion'):
            return redirect('/conversion')
        context = request.session.get('currency_conversion')
        context['otp_sent_message'] = request.session.get('curr_conv_otp_message')
        return render(request,'transactions/currency_conversion/confirm_details.html',context)

    def post(self,request):
        action_type = request.POST.get('action_type')
        if action_type == 'confirm-details':
            user_account = Useraccounts.objects.get(customer__user=request.user)
            full_name = f"{user_account.firstname} {user_account.lastname}"
            context = request.session.get('currency_conversion')
            context['isconfirm'] = True
            return render(request, 'transactions/currency_conversion/confirm_details.html', context)
        elif action_type == 'edit_page':
            request.session['is_edit'] = True
            return redirect('/conversion')
        elif request.POST.get("action") == "otpresend":
            try:
                user = request.user
                user_account = Useraccounts.objects.get(customer__user=user)
                full_name = f"{user_account.firstname} {user_account.lastname}"
                data = {
                    'status': True,
                    'message': 'OTP resent, Please verify!'
                }
                return JsonResponse(data)
            except Exception as e:
                logger.info(e)
                data = {
                    'status':False,
                    'message': 'Something went wrong! Please try again.'
                }
                return JsonResponse(data)
        token = request.GET.get('accessToken')
        if not request.session.get('currency_conversion') or request.session.get('currency_conversion') and token != request.session.get('currency_conversion').get('token'):
            return redirect('/conversion')
        otp = request.POST.get('otp')
        context = request.session.get('currency_conversion')
        context['isconfirm'] = True
        try:
            otp_obj = Otps.objects.get(code=otp, token=token, transactiontype="Currency Conversion",
                                       createdby=request.user)
            transaction_lock_fn(request,is_lock=False)
            if not otp_obj.validated:
                if otp_obj.validtill >= datetime.datetime.now().date():
                    otp_obj.validated = True
                    otp_obj.save()
                    request.session['otp_success_message'] = "OTP Verified!"
                    try:
                        account_number_prev = Transactions.objects.latest('transactionno').transactionno
                    except Exception as e:
                        logger.info(e)
                        account_number_prev = 10000000

                    try:
                        transactionno = int(account_number_prev) + 1
                        debit_accountno = request.session.get('currency_conversion').get('debit_acc_no')
                        debit_amount = request.session.get('currency_conversion').get('debit_amount')
                        credit_accountno = request.session.get('currency_conversion').get('credit_acc_no')
                        fromamount = request.session.get('currency_conversion').get('net_amount')
                        toamount = request.session.get('currency_conversion').get('credit_amount')
                        conversion_fee = request.session.get('currency_conversion').get('conversion_fee')
                        conversionrate = request.session.get('currency_conversion').get('conversionrate')
                        debit_account = Accounts.objects.get(accountno=debit_accountno)
                        credit_account = Accounts.objects.get(accountno=credit_accountno)
                        # debit_account.balance = float(debit_account.balance) - float(debit_amount)
                        debit_account.balance = float(debit_account.balance) - float(fromamount)
                        credit_account.balance = float(credit_account.balance) + float(toamount)
                        debit_account.save()
                        credit_account.save()
                        Transactiontypes.objects.get_or_create(name='Currency Conversion') #TODO: to be removed in production
                        def create_transaction(transactionno,debit_account,credit_account,fromamount,toamount,debit_balance,credit_balance,amount_type):
                            tr_obj = Transactions.objects.create(
                                transactionno=transactionno,
                                fromaccount=debit_account,
                                toaccount=credit_account,
                                fromamount=fromamount,
                                toamount=toamount,
                                transactiontype=Transactiontypes.objects.get(name='Currency Conversion'),
                                createdby=request.user,
                                conversionrate=conversionrate,
                                note=request.session.get('currency_conversion').get('note'),
                                fromaccountbalance=debit_balance,
                                toaccountbalance=credit_balance,
                                amount_type=amount_type,
                            )
                            add_log_action(request, tr_obj, status=f"transaction(Currency Conversion : amount type {tr_obj.amount_type}) created for account {str(tr_obj.fromaccount.accountno)}", status_id=1)
                            return tr_obj
                        debit_balance = debit_account.balance
                        credit_balance = credit_account.balance
                        tr_deb_amount = create_transaction(transactionno, debit_account,credit_account, fromamount, toamount, debit_balance,
                                           credit_balance,amount_type="Net Amount")

                        # Add conversion fee to corresponding currency of master account
                        try:
                            credit_account,converted_conversion_fee = self.find_master_account_convert_amount(debit_account,conversion_fee,debit_account.user_account.test_account)
                            debit_account.balance = float(debit_account.balance) - float(conversion_fee)
                            credit_account.balance = float(credit_account.balance) + float(converted_conversion_fee)
                            debit_account.save()
                            credit_account.save()
                            debit_balance = debit_account.balance
                            credit_balance = credit_account.balance
                            tr_fee_amount = create_transaction(transactionno, debit_account, credit_account, conversion_fee,
                                               converted_conversion_fee,
                                               debit_balance,
                                               credit_balance,amount_type="Conversion Fee")
                            tr_fee_amount.parenttransaction = tr_deb_amount
                            tr_fee_amount.save()
                            request.session['currency_conversion'].update({
                                'transactionnumber':transactionno,
                                'date_and_time': datetime.datetime.utcnow().strftime("%d %b %Y, %-H:%M UTC")
                            })
                            context = {
                                'debit_acc_no': request.session.get('currency_conversion').get('debit_acc_no'),
                                'debit_acc_curr_code': request.session.get('currency_conversion').get(
                                    'debit_acc_curr_code'),
                                'credit_acc_no': request.session.get('currency_conversion').get('credit_acc_no'),
                                'credit_acc_curr_code': request.session.get('currency_conversion').get(
                                    'credit_acc_curr_code'),
                                'conversionrate': request.session.get('currency_conversion').get('conversionrate'),
                                'net_amount': request.session.get('currency_conversion').get('net_amount'),
                                'note': request.session.get('currency_conversion').get('note'),
                                'conversion_fee': request.session.get('currency_conversion').get('conversion_fee'),
                                'debit_amount': request.session.get('currency_conversion').get('debit_amount'),
                                'credit_amount': request.session.get('currency_conversion').get('credit_amount'),
                                'transactionnumber': request.session.get('currency_conversion').get(
                                    'transactionnumber'),
                                'date_and_time': request.session.get('currency_conversion').get('date_and_time'),
                                'curr_conversion': True,
                                'request': request,
                                'year':str(datetime.date.today().year),
                            }
                            self.transaction_success_or_failure_mail(email=request.user.email,email_data=context,status=True,transaction_type=2)
                            return redirect('/conversionSuccess')
                        except Exception as e:
                            logger.info(e)
                            context['status'] = False
                            context['message'] = 'Something went wrong! Please try again.'
                            return render(request, 'transactions/currency_conversion/confirm_details.html', context)

                    except Exception as e:
                        logger.info(e)
                        context['status'] = False
                        context['message'] = 'Something went wrong! Please try again.'
                        return render(request, 'transactions/currency_conversion/confirm_details.html', context)
                else:
                    context['status'] = False
                    context['message'] = 'verification failed, otp expired'
            else:
                context['status'] = False
                context['message'] = 'verification failed, already validated'
        except Exception as e:
            logger.info(e)
            context['status'] = False
            transaction_state = transaction_lock_fn(request)
            context['message'] = transaction_state.get("message")
        return render(request, 'transactions/currency_conversion/confirm_details.html', context)


@method_decorator(login_required, name='dispatch')
@method_decorator(transaction_status, name='dispatch')
class ConversionSuccessView(View,TransactionMail):
    def get(self,request):
        context = {}
        return render(request,'transactions/currency_conversion/transaction-success.html',context)

    def post(self,request):
        action_type = request.POST.get('action_type')
        response = {}
        context = {
            'debit_acc_no': request.session.get('currency_conversion').get('debit_acc_no'),
            'debit_acc_curr_code': request.session.get('currency_conversion').get('debit_acc_curr_code'),
            'credit_acc_no': request.session.get('currency_conversion').get('credit_acc_no'),
            'credit_acc_curr_code': request.session.get('currency_conversion').get('credit_acc_curr_code'),
            'conversionrate': request.session.get('currency_conversion').get('conversionrate'),
            'net_amount': request.session.get('currency_conversion').get('net_amount'),
            'note': request.session.get('currency_conversion').get('note'),
            'conversion_fee': request.session.get('currency_conversion').get('conversion_fee'),
            'debit_amount': request.session.get('currency_conversion').get('debit_amount'),
            'credit_amount': request.session.get('currency_conversion').get('credit_amount'),
            'transactionnumber': request.session.get('currency_conversion').get('transactionnumber'),
            'date_and_time': request.session.get('currency_conversion').get('date_and_time'),
            'request': request,
            'year':str(datetime.date.today().year),
        }
        if action_type == 'export_pdf':

            invoice = f"transaction{request.session.get('currency_conversion').get('transactionnumber')}.pdf"
            file = render_pdf('transactions/currency_conversion/transaction-invoice.html', context, invoice)
            response['filepath'] = settings.AWS_S3_BUCKET_URL+'invoices/' + invoice
        elif action_type == 'email_send':
            context['mail_attach'] = True
            invoice = f"transaction{request.session.get('currency_conversion').get('transactionnumber')}.pdf"
            filepath = 'invoices/'+invoice
            if exists(filepath):
                attach = open(filepath, "r")
            else:
                attach = render_pdf('transactions/currency_conversion/transaction-invoice.html', context, invoice)
            self.transaction_success_or_failure_mail(email=request.user.email, email_data=context, status=True,attach=attach,
                                                     transaction_type=2)
            return render(request, 'transactions/currency_conversion/transaction-success.html', context)
        return HttpResponse(json.dumps(response), content_type='application/json')


@method_decorator(login_required, name='dispatch')
@method_decorator(transaction_status, name='dispatch')
class ConversionCancelView(View):
    def get(self,request):
        if request.session.get('currency_conversion'):
            del request.session['currency_conversion']
        if request.session.get('currency_conversion'):
            del request.session['is_edit']
        request.session['tr_cancel_message'] = 'Your last transaction is cancelled!'
        return redirect('/conversion')


@method_decorator(login_required, name='dispatch')
class EStatementsView(View,ModelQueries):
    def get(self,request):
        context = {}
        user_status = False
        try:
            user_det = request.user.customer_details.all()[0].useracc_customer.all()[0] if request.user.customer_details.all() and request.user.customer_details.all()[0].useracc_customer.all() else None
            if user_det.added_by:
                user_det = user_det.added_by.useracc_customer.all()[0]
                user_status = True
            else:
                user_det = request
        except Exception as e:
            logger.info(e)
            user_det = None
        accounts = self.get_accounts(user_det,user_status)
 
        sessiondata = request.session.get("transaction_details_postdata")
        current_date = datetime.datetime.now()
        prev_date = (datetime.datetime.now() - datetime.timedelta(days=30))
        if sessiondata:
            accountid = int(sessiondata.get("accountid")) if sessiondata.get("accountid") else None
            from_date = sessiondata.get("from_date") if sessiondata.get("from_date") else datetime.datetime.strftime(prev_date, "%Y-%m-%d")
            to_date = sessiondata.get("to_date") if sessiondata.get("from_date") else datetime.datetime.strftime(current_date, "%Y-%m-%d")
            transaction_no = sessiondata.get("transaction_no") if sessiondata.get("from_date") else ""
            beneficiary_name = sessiondata.get("beneficiary_name") if sessiondata.get("from_date") else ""
            creditdebit = sessiondata.get("creditdebit")
            per_page = sessiondata.get("per_page") if sessiondata.get("per_page") else 10
            page = sessiondata.get("page") if sessiondata.get("page") else 1
            account = Accounts.objects.get(id=sessiondata.get("accountid"), isdeleted=False)
            del request.session['transaction_details_postdata']
        else:
            account = accounts[0] if accounts else None
            accountid = account.id if account else None
            transaction_no = ''
            beneficiary_name = ''
            creditdebit = ''
            to_date = datetime.datetime.strftime(current_date, "%Y-%m-%d")
            from_date = datetime.datetime.strftime(prev_date, "%Y-%m-%d")
            per_page = 10
            page = 1
        try:
            if request.GET.get("accountNo"):
                accountno = request.GET.get("accountNo")
                account = Accounts.objects.get(accountno=accountno)
                accountid = account.id
                transaction_no = ''
                beneficiary_name = ''
                creditdebit = ''
                to_date = datetime.datetime.strftime(current_date, "%Y-%m-%d")
                from_date = datetime.datetime.strftime(prev_date, "%Y-%m-%d")
                per_page = 10
                page = 1
        except Exception as e:
            logger.info(e)
            return redirect('/statements')
        context = {
            'accounts':accounts,
            'accountid':accountid,
            'transaction_no':transaction_no,
            'beneficiary_name':beneficiary_name,
            'creditdebit':creditdebit,
            'to_date':to_date,
            'from_date':from_date,
            'per_page':per_page,
            'account':account,
        }
        try:
            transactions = Transactions.objects.filter(Q(fromaccount=account) | Q(toaccount=account),
                                                       isdeleted=False) \
                .order_by('-id')
            transactions = self.get_transactions_filtered(transactions, accountid=accountid,
                                                          transaction_no=transaction_no,
                                                          beneficiary_name=beneficiary_name,
                                                          from_date=from_date, to_date= to_date,
                                                          creditdebit=creditdebit)
            if not account.createdby.customer_details.all()[0].useracc_customer.all()[0].ismaster_account:
                transactions = transactions.filter(~Q(amount_type="Conversion Fee")).exclude(
                    Q(toaccount__user_account__ismaster_account=True) &
                    ~Q(transactiontype__name="Third Party Transfer"))
            transactions = transactions.order_by("-id")
            transactions = self.paginate(transactions, page=page,
                                         per_page=per_page)
        except Exception as e:
            logger.info(e)
            transactions = []
        context['transactions'] = transactions
        return render(request,'transactions/e-statements/base.html',context)

    def post(self,request):
        response = {}
        context = {}
        action_type = request.POST.get("action_type")
        if action_type == "gettransactiondetails":
            accountid = request.POST.get("accountid")
            transaction_no = request.POST.get("transaction_no")
            beneficiary_name = request.POST.get("beneficiary_name")
            from_date = request.POST.get("from_date")
            to_date = request.POST.get("to_date")
            creditdebit = request.POST.get("creditdebit")
            account = Accounts.objects.get(id=accountid)
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
            transactions = self.paginate(transactions, page=request.POST.get("page", 1),
                                         per_page=request.POST.get("per_page", 10))
            response['record_status'] = True
            if not transactions:
                response['record_status'] = False
            context['request'] = request
            context['transactions'] = transactions
            context['accountid'] = accountid
            context['account'] = account
            if request.POST.get('from_page'):
                context['from_page'] = request.POST.get('from_page')
            if request.POST.get('slug'):
                context['slug'] = request.POST.get('slug')

            response['statementtable_html'] = render_to_string('transactions/e-statements/includes/statement_table.html',context)

            # response['account_balance'] = "{:,}".format(round(account.balance,2))
            response['account_balance'] = str(round(account.balance,2))
            response['currency_code'] = account.currency.code
            return HttpResponse(json.dumps(response),content_type='application/json')
        if action_type == "gettransactionbyaccount":

            context = json.loads(json.dumps(request.POST))
            context['accountid'] = int(context['accountid'])
            accountid = request.POST.get("accountid")
            transaction_no = request.POST.get("transaction_no")
            beneficiary_name = request.POST.get("beneficiary_name")
            from_date = request.POST.get("from_date")
            to_date = request.POST.get("to_date")
            creditdebit = request.POST.get("creditdebit")

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

            transactions = self.paginate(transactions,page=request.POST.get("page",1),
                                         per_page=request.POST.get("per_page",10))
            context['accounts'] = self.get_accounts(request)
            context['account'] = Accounts.objects.get(id=accountid)
            context['transactions'] = transactions
            context['request'] = request
            if request.POST.get("is_paginate"):
                response['statementtable_html'] = render_to_string('transactions/e-statements/includes/statement_table.html',context)
                return HttpResponse(json.dumps(response),content_type='application/json')
            return render(request, 'transactions/e-statements/base.html', context)

        elif action_type == "export_statement":
            accountid = request.POST.get("accountid")
            from_date = request.POST.get("from_date")
            to_date = request.POST.get("to_date")
            creditdebit = request.POST.get("creditdebit")
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
            response['status'] = True
            if transactions:
                filename = f"{account.accountno} - Statement.{request.POST.get('export_type')}"
                folder = f"statements/{request.POST.get('export_type')}/"
                filepath = settings.MEDIA_ROOT + settings.MEDIA_URL + folder
                create_directory(filepath)
                if request.POST.get("export_type") == 'pdf':
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
                response['filepath'] = settings.AWS_S3_BUCKET_URL + folder + filename
            else:
                response['status'] = False

            return HttpResponse(json.dumps(response), content_type='application/json')
        elif action_type == "add_to_session":
            request.session['transaction_details_postdata'] = request.POST.dict()
            response['status'] = True
            return HttpResponse(json.dumps(response), content_type='application/json')


@method_decorator(login_required, name='dispatch')
class GetTransactionDetailsView(View,ModelQueries,TransactionMail,UtilMixins):
    def get(self,request):
        if request.session.get("st-transaction_id"):
            context = {}
            try:
                transaction = Transactions.objects.get(id=request.session.get("st-transaction_id"))
                if request.user.customer_details.all()[0].useracc_customer.all()[0].ismaster_account:
                    try:
                        tr_objs = Transactions.objects.filter(transactionno=transaction.parenttransaction.transactionno,isdeleted=False)
                    except:
                        tr_objs = []
                    for tr_obj in tr_objs:
                        if tr_obj.amount_type == "Net Amount":
                            transaction = tr_obj
            except Exception as e:
                logger.info(e)
                return redirect('/statements')
            context['transaction'] = transaction
            return render(request, 'transactions/e-statements/transaction-details.html', context)
        return redirect('/statements')
    def post(self,request):
        action_type = request.POST.get('action_type')
        context = {}
        if action_type == "get_trasnactiondetailsby_id":
            transaction = Transactions.objects.get(id=request.POST.get("transaction_id"))
            if request.user.customer_details.all()[0].useracc_customer.all()[0].ismaster_account:
                try:
                    tr_objs = Transactions.objects.filter(transactionno=transaction.parenttransaction.transactionno,isdeleted=False)
                except:
                    tr_objs = []
                for tr_obj in tr_objs:
                    if tr_obj.amount_type == "Net Amount":
                        transaction = tr_obj
            # account = Accounts.objects.get(id=request.POST.get("account_id"))
            context['transaction'] = transaction
            request.session['st-transaction_id'] = request.POST.get("transaction_id")
            # context['account'] = account
            return render(request, 'transactions/e-statements/transaction-details.html', context)
        elif action_type == "export_pdf":
            response = {}
            transaction = Transactions.objects.get(id=request.POST.get("transaction_id"))
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
                elif transaction.transactiontype.name == "Domestic Transfer":
                    context = {
                        'domestic_transfer': True,
                        'transactionno': transaction.transactionno,
                        'transaction_datetime_utc': transaction.createdon.strftime("%d %b %Y, %-H:%M UTC"),
                        'sender_name': full_name,
                        'from_currency_code': transaction.fromaccount.currency.code,
                        'fromaccount': transaction.fromaccount.accountno,
                        'beneficiary_accno': transaction.domtransaction_tr.all()[0].accountnumber,
                        'beneficiary_name': transaction.domtransaction_tr.all()[0].accountholdername,
                        'bank_name': transaction.domtransaction_tr.all()[0].bankname,
                        'routing_number': transaction.domtransaction_tr.all()[0].routing_number,
                        'city': transaction.domtransaction_tr.all()[0].city,
                        'country': transaction.domtransaction_tr.all()[0].country.shortform,
                        'currency': transaction.domtransaction_tr.all()[0].currency.code,
                        'purpose_type': transaction.domtransaction_tr.all()[0].purpose.transactionpurpose,
                        'purpose_note': transaction.domtransaction_tr.all()[0].other_purpose_note if transaction.domtransaction_tr.all()[0].other_purpose_note else "",
                        'email': transaction.domtransaction_tr.all()[0].email,
                        'box_no': transaction.domtransaction_tr.all()[0].user_box_no if transaction.domtransaction_tr.all()[0].user_box_no else None,
                        'street': transaction.domtransaction_tr.all()[0].user_street if transaction.domtransaction_tr.all()[0].user_street else None,
                        'user_city': transaction.domtransaction_tr.all()[0].user_city if transaction.domtransaction_tr.all()[0].user_city else None,
                        'state': transaction.domtransaction_tr.all()[0].user_state if transaction.domtransaction_tr.all()[0].user_state else None,
                        'user_counrty': transaction.domtransaction_tr.all()[0].user_country.shortform if transaction.domtransaction_tr.all()[0].user_country else None,
                        'phone_no': transaction.domtransaction_tr.all()[0].user_phone if transaction.domtransaction_tr.all()[0].user_phone else None,
                        'amount': transaction_amounts.get("net_amount"),
                        'conversion_fee': transaction_amounts.get("conversion_fee"),
                        'domestic_fee': transaction_amounts.get("domestic_fee"),
                        'cable_charge': transaction_amounts.get("cable_charge"),
                        'debit_amount': self.get_debit_amount(transaction,"True"),
                        'credit_amount': round(transaction.toamount,2),
                        'note': transaction.note,
                        'year': str(datetime.date.today().year),

                    }
                    context.update({
                        'invoice': self.get_transaction_receipt(transaction)
                    })
                    file = render_pdf('accounts/wire_transfer/domestic-transaction-pdf-template.html', context, invoice)
                elif transaction.transactiontype.name in [ "Acccount To Account Transfer","Currency Conversion"]:
                    if transaction.transactiontype.name == "Acccount To Account Transfer":
                        beneficairy_name =  f'{transaction.toaccount.user_account.firstname} {transaction.toaccount.user_account.middlename} {transaction.toaccount.user_account.lastname}'
                    else:
                        beneficairy_name = None
                    context = {
                        'transaction_number': transaction.transactionno,
                        'debit_account': transaction.fromaccount.accountno,
                        'debit_currency_code':transaction.fromaccount.currency.code,
                        'credit_account': transaction.toaccount.accountno,
                        'credit_currency_code':transaction.toaccount.currency.code,
                        'beneficiary_name': beneficairy_name,
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
                    'wallet_transfer' : True,
                    'transactionno':transaction.transactionno,
                    'transaction_datetime_utc':transaction.createdon.strftime("%d %b %Y, %-H:%M UTC"),
                    'sender_name': full_name,
                    'Wallet_name': transaction.walletwithdrawal_tr.all()[0].wallet_name,
                    'from_currency_code': transaction.fromaccount.currency.code,
                    'fromaccount': transaction.fromaccount.accountno,
                    'beneficiary_name': transaction.walletwithdrawal_tr.all()[0].accountholdername,
                    'currency': transaction.walletwithdrawal_tr.all()[0].currency.code,
                    'amount': transaction_amounts.get("net_amount"),
                    'conversion_fee': transaction_amounts.get("conversion_fee"),
                    'wallet_tr_fee':transaction_amounts.get("wallet_fee"),
                    'cable_charge':transaction_amounts.get("cable_charge"),
                    'debit_amount': self.get_debit_amount(transaction,"True"),
                    'credit_amount': round(transaction.toamount,2),
                    'note': transaction.note,
                    'year':str(datetime.date.today().year),
                }
                    file = render_pdf('wallet-withdrawal/wallettransfer_transaction-pdf-template.html', context, invoice)
            response['filepath'] = settings.AWS_S3_BUCKET_URL+'invoices/' + invoice
            response['status'] = True

            if request.POST.get("send_mail"):
                context = {
                    'user': full_name.title(),
                    'mail_attach': True,
                    'from_currency_code': transaction.fromaccount.currency.code,
                    'amount': transaction_amounts.get("net_amount"),
                    'year': str(datetime.date.today().year),
                }

                self.transaction_success_or_failure_mail(email=request.user.email, email_data=context, status=True,
                                                         attach=filepath)
                response['message'] = "Email sent successfully!"
            return HttpResponse(json.dumps(response), content_type='application/json')


@method_decorator(login_required, name='dispatch')
class UPIpaymentView(View):
    def get(self,request):
        upi_status= Useraccounts.objects.get(customer__user=request.user)
        if upi_status.upi_payment:
            return render(request, 'customer-management/upi-payment.html')
        else:
            return redirect('/')
@method_decorator(login_required, name='dispatch')
@method_decorator(template_decorator(title="Wallet Withdrawal"), name='dispatch')
@method_decorator(transaction_status, name='dispatch')
class WalletWithdrawalView(View):
    def get(self, request):
        if request.GET.get('Edit'):
            prevData = request.session['walletwithdrawal']
        else:
            prevData = None
        accounts = Accounts.objects.filter(user_account__customer__user=request.user, isdeleted=False)
        currencies = Currencies.objects.filter(isdeleted=False,code='USD')
        cryptobeneficiaries = Cryptobeneficiaries.objects.filter(createdby=request.user, isdeleted=False)
        transactionpurposetypes = Transactionpurposetype.objects.filter(isdeleted=False)
        user_details = Useraccounts.objects.get(isdeleted=False, customer__user=request.user)
        context = {
            'accounts': accounts,
            'currencies': currencies,
            'cryptobeneficiaries': cryptobeneficiaries,
            'transactionpurposetypes': transactionpurposetypes,
            'prevData': prevData,
            'user_details': user_details
        }
        if request.session.get('cancelWalletTrans'):
            context['message'] = request.session.get('cancelWalletTrans')
            logger.info(f"cancel WalletWithdrawalTransaction by {request.user.email}")
            context['status'] = True
            del request.session['cancelWalletTrans']
        if request.session.get('wireTrdeclinedMsg'):
            context['message'] = request.session.get('wireTrdeclinedMsg')
            context['status'] = False
            del request.session['wireTrdeclinedMsg']
        return render(request, 'wallet-withdrawal/wallet.html', context)

    def post(self, request):

        def context_function():
            prevData = request.POST.dict()
            accounts = Accounts.objects.filter(user_account__customer__user=request.user, isdeleted=False)
            currencies = Currencies.objects.filter(isdeleted=False,code='USD')
            cryptobeneficiaries = Cryptobeneficiaries.objects.filter(createdby=request.user, isdeleted=False)
            transactionpurposetypes = Transactionpurposetype.objects.filter(isdeleted=False)
            self.context = {
                'accounts': accounts,
                'currencies': currencies,
                'cryptobeneficiaries': cryptobeneficiaries,
                'transactionpurposetypes': transactionpurposetypes,
                'prevData': prevData,
                'user_details': Useraccounts.objects.get(isdeleted=False, customer__user=request.user)
            }
            return True
        if not checkNonAsciiChracters([request.POST.get('Walletname'),request.POST.get('Note')]):
            if context_function():
                self.context['message'] = 'Fancy characters are not allowed'
                logger.info(f"{request.user.email} Entered Fancy characters.only Alphanumeric characters are allowed")
                self.context['status'] = False
                return render(request, 'wallet-withdrawal/wallet.html', self.context)

        if request.session.get('walletwithdrawal'):
            del request.session['walletwithdrawal']
        if request.session.get('token'):
            del request.session['token']
        request.session['walletwithdrawal'] = request.POST.dict()

        amount = round(Decimal(request.POST.get('Amount')), 2)
        from_amount = amount
        from_account = Accounts.objects.get(accountno=request.POST.get('FromAccount'), isdeleted=False)
        from_account_balance = Decimal(from_account.balance)

        def conversion_charges(amount):
            if amount < 1000:
                self.wallet_transfer_fee = Decimal(20.00)
                self.cable_charge = Decimal(39.00)

            elif amount >= 1000 and amount < 3450:
                self.total_tr_charge = Decimal(69.00)
                self.wallet_transfer_fee = round(amount * Decimal((2 / 100)), 2)
                self.cable_charge = round(self.total_tr_charge - self.wallet_transfer_fee, 2)

            elif amount >= 3450:
                self.wallet_transfer_fee = round(amount * Decimal((2 / 100)), 2)
                self.cable_charge = Decimal(0.00)

        def conversion_rates(amount, from_currency_code, conversion_fee, wallet_transfer_fee, cable_charge):

            to_dollar = Currencyconversionratescombined.objects.get(fromcurrency__code='USD',
                                                                    tocurrency__code=from_currency_code,
                                                                    isdeleted=False)
            currency_conversion = Currencyconversionratescombined.objects.get(fromcurrency__code=from_currency_code,
                                                                              tocurrency__code=request.POST.get(
                                                                                  'Currency'), isdeleted=False)

            conversionrate = round(currency_conversion.conversionrate, 4)
            try:
                currency_margin = Currencyconversionmargins.objects.get(fromcurrency__code=from_currency_code,
                                                                        tocurrency__code=request.POST.get('Currency'),
                                                                        isdeleted=False)
                margin_rate = currency_margin.marginpercent
                conversionrate = conversionrate - (conversionrate * Decimal(float(margin_rate) / 100))
            except Exception as e:
                logger.info(e)
                pass

            self.min_tr_amount = Decimal(100) * to_dollar.conversionrate
            self.conversion_fee = conversion_fee
            self.wallet_transfer_fee = round(wallet_transfer_fee * to_dollar.conversionrate, 2)
            self.cable_charge = round(cable_charge * to_dollar.conversionrate, 2)
            self.credit_amount = round(from_amount * conversionrate, 2)

        from_currency_code = from_account.currency.code
        if request.POST.get('Currency') == from_currency_code:
            if from_currency_code == 'USD':
                amount = Decimal(amount)
            else:
                to_dollar = Currencyconversionratescombined.objects.get(fromcurrency__code='USD',
                                                                        tocurrency__code=from_currency_code,
                                                                        isdeleted=False)
                amount = Decimal(amount) / to_dollar.conversionrate
            conversion_fee = Decimal(0.00)
            conversion_charges(amount)
        else:
            if from_currency_code == 'USD':
                amount = Decimal(amount)
            else:
                to_dollar = Currencyconversionratescombined.objects.get(fromcurrency__code='USD',
                                                                        tocurrency__code=from_currency_code,
                                                                        isdeleted=False)
                amount = Decimal(amount) / to_dollar.conversionrate
            conversion_fee = round(from_amount * Decimal(0.5 / 100), 2)
            conversion_charges(amount)
        conversion_rates(amount, from_currency_code, conversion_fee, self.wallet_transfer_fee, self.cable_charge)
        debit_amount = self.wallet_transfer_fee + self.cable_charge + self.conversion_fee + from_amount
        commission_charges = round((self.wallet_transfer_fee + self.cable_charge + self.conversion_fee), 2)
        if from_account_balance < debit_amount:
            if context_function():
                self.context['message'] = "You don't have enough funds to make this transaction"
                logger.info(f"{request.user.email}  account balance {from_account_balance}. so user don't have enough funds to make this transaction ")
                self.context['status'] = False
                return render(request, 'wallet-withdrawal/wallet.html', self.context)
        elif from_amount < self.min_tr_amount:
            if context_function():
                self.context[
                    'message'] = f'Minimum amount required for the transaction is {format(self.min_tr_amount, ".2f")} {from_currency_code}'
                logger.info(f"the {from_amount} to be transaction is lowerthan  Minimum amount. {self.min_tr_amount} required for the transaction ")
                self.context['status'] = False
                return render(request, 'wallet-withdrawal/wallet.html', self.context)
        is_crypto_ben = Cryptobeneficiaries.objects.filter(name=request.POST.get('BeneficiaryName'),
            isdeleted=False, createdby=request.user).exists()
        request.session['walletwithdrawal'].update({
            'cable_charge': format(self.cable_charge, ".2f"),
            'wallet_transfer_fee': format(self.wallet_transfer_fee, ".2f"),
            'conversion_fee': format(self.conversion_fee, ".2f"),
            'debit_amount': format(debit_amount, ".2f"),
            'commission_charges': format(commission_charges, ".2f"),
            'credit_amount': format(self.credit_amount, ".2f"),
            'from_currency_code': from_currency_code,
            'recipient_currency_code': request.POST.get('Currency'),
            'is_crypto_ben': is_crypto_ben
        })

        request.session['token'] = token_urlsafe(30)
        return redirect('wallet-withdrawal-confirm', request.session['token'])

@method_decorator(login_required, name='dispatch')
@method_decorator(transaction_status, name='dispatch')
class WalletWithdrawalConfirm(View):
    
    @transaction.atomic
    def get(self,request,token):
        if  not token or token != request.session.get('token') or not request.session['walletwithdrawal']:
            logger.info(f"{token} and  token from session {request.session.get('token')} are not same.it redirect to dashborad ")
            return redirect('/')
        if token == request.session.get('token'):
            return render(request,'wallet-withdrawal/wallet-transfer-confirm.html')
        
    @transaction.atomic
    def post(self, request,token):
        if request.POST.get('action_type') == 'resent otp' :
            user_account = Useraccounts.objects.get(customer__user=request.user)
            full_name = f"{user_account.firstname} {user_account.lastname}"
            otp_status = OTP()
            if request.session.get('prevToken'):
                del request.session['prevToken']
            request.session['prevToken'] = request.session['token']
            return JsonResponse({
                'message' : 'OTP sent, Please verify!'
                })

        elif request.POST.get('otp_sent') == 'otp_sent':
            if token == request.session.get('token'):
                if  request.POST.get('save_ben') == 'on':
                    crypto_ben, status = Cryptobeneficiaries.objects.get_or_create(
                        name = request.session['walletwithdrawal']['BeneficiaryName'],
                        wallet_name=request.session['walletwithdrawal']['Walletname'],
                        currency = Currencies.objects.get(code=request.session['walletwithdrawal']['Currency']),
                        createdby = request.user,
                        customer = Customers.objects.get(user=request.user)
                    )
                    crypto_ben.save()
                user_account = Useraccounts.objects.get(customer__user=request.user)
                full_name = f"{user_account.firstname} {user_account.lastname}"
                otp_status = OTP()
                if otp_status:
                    messages.success(request,'OTP sent, Please verify!')
                    if request.session.get('prevToken'):
                        del request.session['prevToken']
                    request.session['prevToken'] = request.session['token']
                    del request.session['token']
                    request.session['token'] = token_urlsafe(30)
                    return redirect('wallet-transfer-walletOtp', request.session['token'])
                else:
                    messages.error(request,'Could not send OTP')
                    logger.info(f"otp not send re-direct to confirm page")
                    return redirect('wallet-withdrawal-confirm', request.session['token'])
            else:
                logger.info(f"{request.user.email} generated token -{token} is not equal token from session -{request.session.get('token')}.re-direct to dashboard" )
                return redirect('/')

@method_decorator(login_required, name='dispatch')
@method_decorator(transaction_status, name='dispatch')
class CancelWalletTransfer(View):
    def get(self,request):
        if request.session.get('walletwithdrawal'):
            del request.session['walletwithdrawal']
        if request.session.get('token'):
            del request.session['token']
        request.session['cancelWalletTrans'] = 'Last transaction canceled'
        return redirect('walletwithdrawal')


@method_decorator(login_required, name='dispatch')
@method_decorator(transaction_status, name='dispatch')
class WalletTransferOtp(View):
    def get(self, request, token):
        if not token or token != request.session.get('token') or not request.session['walletwithdrawal']:
            logger.info(f"{request.user.email} generated token -{token} is not equal token from session -{request.session.get('token')}.re-direct to dashboard" )
            return redirect('/')
        if token == request.session.get('token'):
            return render(request, 'wallet-withdrawal/wallet-transfer-otp.html')

    def post(self, request, token):
        def validation_fn():

            if token != request.session.get('token'):
                logger.info(f"{request.user.email} generated token -{token} is not equal token from session -{request.session.get('token')}.re-direct to dashboard" )
                return {
                    'status': False,
                    'error': 'Your Transaction has been declined due to Security reason'
                }
            try:
                otp = Otps.objects.get(code=request.POST.get('otp'),
                                       transactiontype='Wallet Withdrawal',
                                       validated=False,
                                       createdby=request.user, token=request.session['prevToken'], isdeleted=False)
                transaction_lock_fn(request,is_lock=False)
            except Exception as e:
                logger.info(e)
                transaction_state = transaction_lock_fn(request)
                return {
                    'otp_error': True,
                    'status': False,
                    'error': transaction_state.get("message")
                }
            valid_till = datetime.datetime.now()
            valid_till = valid_till.date().strftime(settings.DATE_FORMAT)
            valid_date = datetime.datetime.strptime(valid_till, settings.DATE_FORMAT)
            if valid_date.date() <= otp.validtill:
                otp.validated = True
                otp.save()
            else:
                logger.info(f"The time for otp entry has passed")
                return {
                    'otp_error': True,
                    'status': False,
                    'error': 'Verification failed, expired otp'
                }
            try:
                customer_type = Customers.objects.get(user=request.user, isdeleted=False).customertype
                if customer_type == 1:
                    user = Useraccounts.objects.get(customer__user=request.user, isdeleted=False)
                    sender_name = f'{user.firstname} {user.lastname}'
                else:
                    sender_name = Businessdetails.objects.get(customer__user=request.user, isdeleted=False).companyname
            except Exception as e:
                logger.info(e)
                return {
                    'status': False,
                    'error': 'Your Transaction has been declined due to invalid Customer or Business details'
                }
            request.session['walletwithdrawal'].update({
                'sender_name': sender_name
            })

            try:
                last_transactionno = Transactions.objects.latest('transactionno').transactionno
            except Exception as e:
                logger.info(e)
                last_transactionno = 10000000

            def transaction_fn(last_transactionno, fromamount, charge, parent_tr=None, toamount=None, crpto_tr=None,
                               commission_charges=None, cable_charge=None, last_transaction=None):
                try:
                    try:
                        account = Accounts.objects.get(
                            accountno=request.session['walletwithdrawal']['FromAccount'], isdeleted=False)
                    except Exception as e:
                        logger.info(e)
                        return {
                            'status': False,
                            'error': 'Your Transaction has been declined due to invalid source account'
                        }
                    if account.balance < Decimal(fromamount):
                        raise Exception()
                    account_balance = account.balance - Decimal(fromamount)
                    account.balance = account_balance
                    account.save()
                except Exception as e:
                    logger.info(e)
                    return {
                        'status': False,
                        'error': 'Your Transaction has been declined due to insufficient fund'
                    }
                if cable_charge:
                    cablecharge_obj = Cablecharges.objects.create(
                        parenttransaction=parent_transaction,
                        chargeamount=Decimal(request.session['walletwithdrawal']['cable_charge']),
                        currency=Currencies.objects.get(code=request.session['walletwithdrawal']['Currency'],
                                                        isdeleted=False),
                        createdby=request.user,
                        transaction=last_transaction
                    )
                    add_log_action(request, cablecharge_obj,
                                   status=f'cable charge created for transaction {parent_transaction.transactionno}',
                                   status_id=1)
                    return {
                        'status': True,
                    }
                else:
                    if commission_charges:
                        try:
                            toaccount = Accounts.objects.get(user_account__ismaster_account=True,
                                                             currency__code=request.session['walletwithdrawal'][
                                                                 'from_currency_code'], isdeleted=False)
                        except Exception as e:
                            logger.info(e)
                            toaccount = None
                    else:
                        toaccount = None

                    to_account_balance = None
                    charge_type = None
                    if charge == 1:
                        charge_type = 'Net Amount'
                    elif charge == 2:
                        charge_type = 'Conversion Fee'
                    elif charge == 3:
                        charge_type = 'Wallet Withdrawal Fee'
                    try:
                        transactiontype, status = Transactiontypes.objects.get_or_create(name='Wallet Withdrawal Transfer')
                        self.transaction = Transactions.objects.create(
                            transactionno=int(last_transactionno) + 1,
                            fromaccount=Accounts.objects.get(accountno=request.session['walletwithdrawal']['FromAccount'], isdeleted=False),
                            toaccount=None,
                            fromamount=fromamount,
                            toamount=toamount,
                            initiatedby=request.user,
                            transactiontype=transactiontype,
                            createdby=request.user,
                            note=request.session['walletwithdrawal']['Note'],
                            recipientname=request.session['walletwithdrawal']['BeneficiaryName'],
                            fromaccountbalance=account_balance,
                            toaccountbalance=to_account_balance,
                            parenttransaction=parent_tr,
                            amount_type=charge_type,
                            affiliate_fee_percentage=Customers.objects.get(isdeleted=False, user=request.user).outgoingwallettansactionfee
                        )
                        add_log_action(request, self.transaction,
                                       status=f"transaction(Wallet Withdrawal : amount type {self.transaction.amount_type}) created for account {str(self.transaction.fromaccount.accountno)}",
                                       status_id=1)
                        if crpto_tr:
                            crpto_tr = WalletWithdrawalTransactions.objects.create(
                                transaction=self.transaction,
                                wallet_name=request.session['walletwithdrawal']['Walletname'],
                                accountholdername=request.session['walletwithdrawal']['BeneficiaryName'],
                                currency=Currencies.objects.get(code=request.session['walletwithdrawal']['Currency'], isdeleted=False),
                                createdby=request.user,
                            )
                            add_log_action(request, crpto_tr,
                                           status=f'Wallet Withdrawal transaction created for account {str(self.transaction.fromaccount.accountno)}',
                                           status_id=1)
                    except Exception as e:
                        logger.info(e)
                        return {
                            'status': False,
                            'error': 'Your Transaction has been declined due to some error'
                        }

            response = transaction_fn(last_transactionno, request.session['walletwithdrawal']['Amount'],
                                      toamount=request.session['walletwithdrawal']['credit_amount'], charge=1,
                                      crpto_tr=True)
            if response and not response.get('status'):
                return response
            parent_transaction = self.transaction
            charge = 3
            response = transaction_fn(last_transactionno,
                                      request.session['walletwithdrawal']['wallet_transfer_fee'], charge,
                                      parent_transaction,
                                      toamount=request.session['walletwithdrawal']['wallet_transfer_fee'],
                                      commission_charges=True)
            if response and not response.get('status'):
                return response
            charge = 2
            response = transaction_fn(last_transactionno, request.session['walletwithdrawal']['conversion_fee'],
                                      charge, parent_transaction,
                                      toamount=request.session['walletwithdrawal']['conversion_fee'],
                                      commission_charges=True)
            if response and not response.get('status'):
                return response
            last_transaction = self.transaction
            response = transaction_fn(last_transactionno, request.session['walletwithdrawal']['cable_charge'],
                                      parent_transaction, cable_charge=True, last_transaction=last_transaction)
            if response and not response.get('status'):
                return response
            request.session['walletwithdrawal'].update({
                'transactionno': parent_transaction.transactionno,
                'transaction_id': parent_transaction.id,
                'transaction_datetime_utc': datetime.datetime.utcnow().strftime("%d %b %Y, %-H:%M UTC"),
            })
            if request.session['prevToken']:
                del request.session['prevToken']
            if request.session.get('token'):
                del request.session['token']
                request.session['token'] = token_urlsafe(30)
            return {
                'status': True,
            }

        response = validation_fn()
        if response and not response.get('status'):
            if response.get('otp_error') == True:
                context = {
                    'statust': False,
                    'message': response.get('error')
                }
                return render(request, 'wallet-withdrawal/wallet-transfer-otp.html', context)
            user_account = Useraccounts.objects.get(customer__user=request.user)
            full_name = f"{user_account.firstname} {user_account.lastname}"
            context = {
                'user': full_name.title(),
                'error': True,
                'message': response.get('error'),
                'year': str(datetime.date.today().year),
            }
            transaction_mail_status = TransactionMail().transaction_success_or_failure_mail(email=request.user.email,
                                                                                            email_data=context,
                                                                                            status=False)
            request.session['wireTrdeclinedMsg'] = response.get('error')
            return redirect('walletwithdrawal')
        elif response.get('status'):
            customer_account = Useraccounts.objects.get(customer__user=request.user)
            context = {
                'wallet_transfer': True,
                'wallet_transfer_success': True,
                'test_user': customer_account.test_account,
                'transactionno': request.session['walletwithdrawal']['transactionno'],
                'transaction_datetime_utc': request.session['walletwithdrawal']['transaction_datetime_utc'],
                'Wallet_name':request.session['walletwithdrawal']['Walletname'],
                'sender_name': request.session['walletwithdrawal']['sender_name'],
                'from_currency_code': request.session['walletwithdrawal']['from_currency_code'],
                'fromaccount': request.session['walletwithdrawal']['FromAccount'],
                'beneficiary_name': request.session['walletwithdrawal']['BeneficiaryName'],
                'amount': request.session['walletwithdrawal']['Amount'],
                'conversion_fee': request.session['walletwithdrawal']['conversion_fee'],
                'wallet_tr_fee': request.session['walletwithdrawal']['wallet_transfer_fee'],
                'cable_charge': request.session['walletwithdrawal']['cable_charge'],
                'debit_amount': request.session['walletwithdrawal']['debit_amount'],
                'credit_amount': request.session['walletwithdrawal']['credit_amount'],
                'note': request.session['walletwithdrawal']['Note'],
                'year': str(datetime.date.today().year),

            }
            transaction_mail_status = TransactionMail().transaction_success_or_failure_mail(email=request.user.email,
                                                                                            email_data=context,
                                                                                            status=True)
            return redirect('walletwithdrawal-transfer-success', request.session['token'])

@method_decorator(login_required, name='dispatch')
@method_decorator(transaction_status, name='dispatch')
class WalletTransferSuccess(View):
    def get(self,request,token):
        if request.GET.get("export_pdf"):
            response = {}
            invoice = f"transaction{request.session['walletwithdrawal'].get('transactionno')}.pdf"
            context = {
                    'wallet_transfer' : True,
                    'transactionno':request.session['walletwithdrawal']['transactionno'],
                    'transaction_datetime_utc':request.session['walletwithdrawal']['transaction_datetime_utc'],
                    'sender_name':request.session['walletwithdrawal']['sender_name'],
                    'Wallet_name': request.session['walletwithdrawal']['Walletname'],
                    'from_currency_code':request.session['walletwithdrawal']['from_currency_code'],
                    'fromaccount':request.session['walletwithdrawal']['FromAccount'],
                    'beneficiary_name':request.session['walletwithdrawal']['BeneficiaryName'],
                    'currency':request.session['walletwithdrawal']['Currency'],
                    'amount':request.session['walletwithdrawal']['Amount'],
                    'conversion_fee':request.session['walletwithdrawal']['conversion_fee'],
                    'wallet_tr_fee':request.session['walletwithdrawal']['wallet_transfer_fee'],
                    'cable_charge':request.session['walletwithdrawal']['cable_charge'],
                    'debit_amount':request.session['walletwithdrawal']['debit_amount'],
                    'credit_amount':request.session['walletwithdrawal']['credit_amount'],
                    'note':request.session['walletwithdrawal']['Note'],
                    'year':str(datetime.date.today().year),

                }
            file = render_pdf('wallet-withdrawal/wallettransfer_transaction-pdf-template.html', context, invoice)
            response['filepath'] = settings.AWS_S3_BUCKET_URL+'invoices/'+invoice
            return HttpResponse(json.dumps(response),content_type='application/json')
        else:
            if  token != request.session.get('token') or not token or not request.session['walletwithdrawal']:
                logger.info(f"{request.user.email} generated token -{token} is not equal token from session -{request.session.get('token')}.re-direct to dashboard" )
                return redirect('/')
            if token == request.session.get('token'):
                return render(request, 'wallet-withdrawal/walletwithdrawal_transaction-success.html')

    def post(self,request,token):
        user_account = Useraccounts.objects.get(customer__user=request.user)
        full_name = f"{user_account.firstname} {user_account.lastname}"
        email_data = {
                'user' : full_name.title(),
                'mail_attach' : True,
                'from_currency_code':request.session['walletwithdrawal']['from_currency_code'],
                'amount':request.session['walletwithdrawal']['Amount'],
                'year':str(datetime.date.today().year),
            }
        response = {}
        invoice = f"transaction{request.session['walletwithdrawal'].get('transactionno')}.pdf"
        context = {
                'wallet_transfer' : True,
                'transactionno':request.session['walletwithdrawal']['transactionno'],
                'transaction_datetime_utc':request.session['walletwithdrawal']['transaction_datetime_utc'],
                'sender_name':request.session['walletwithdrawal']['sender_name'],
                'from_currency_code':request.session['walletwithdrawal']['from_currency_code'],
                'fromaccount':request.session['walletwithdrawal']['FromAccount'],
                'beneficiary_name':request.session['walletwithdrawal']['BeneficiaryName'],
                'Wallet_name': request.session['walletwithdrawal']['Walletname'],
                'currency':request.session['walletwithdrawal']['Currency'],
                'amount':request.session['walletwithdrawal']['Amount'],
                'conversion_fee':request.session['walletwithdrawal']['conversion_fee'],
                'wallet_tr_fee':request.session['walletwithdrawal']['wallet_transfer_fee'],
                'cable_charge':request.session['walletwithdrawal']['cable_charge'],
                'debit_amount':request.session['walletwithdrawal']['debit_amount'],
                'credit_amount':request.session['walletwithdrawal']['credit_amount'],
                'note':request.session['walletwithdrawal']['Note'],
                'year':str(datetime.date.today().year),

            }
        file = render_pdf('wallet-withdrawal/wallettransfer_transaction-pdf-template.html', context, invoice)
        response['filepath'] = settings.AWS_S3_BUCKET_URL+'invoices/'+invoice
        transaction_mail_status=TransactionMail().transaction_success_or_failure_mail(email=request.user.email,email_data=email_data,status=True, attach=file)
        context = {
            'status' : True,
            'message' : 'Mail sent successfully!'
        }
        return render(request, 'wallet-withdrawal/walletwithdrawal_transaction-success.html',context)