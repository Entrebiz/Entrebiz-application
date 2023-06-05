
from django.views import View
from django.shortcuts import render, redirect
from django.conf import settings
from Transactions.mixins import add_log_action, checkNonAsciiChracters
from utils.models import Accounts, Currencies, Incomingtracepayment, Useraccounts
import os
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from EntrebizAdmin.decorators import template_decorator
import logging
logger = logging.getLogger('lessons')

@method_decorator(login_required, name='dispatch')
@method_decorator(template_decorator(title="Missing Payment"),name='dispatch')
class MissingPaymentList(View):
    def get(self, request):
        tracepayment_lists = Incomingtracepayment.objects.filter(isdeleted=False,isadmindeleted=False,createdby=request.user).order_by('id')
        context = {
            'tracepayment_lists' : tracepayment_lists
        }
        if request.session.get('tracePaymentSuccessMsg'):
            context['status'] = True
            context['message'] = request.session.get('tracePaymentSuccessMsg')
            del request.session['tracePaymentSuccessMsg']
        elif request.session.get('tracePaymentDeleteMsg'):
            context['status'] = True
            context['message'] = request.session.get('tracePaymentDeleteMsg')
            del request.session['tracePaymentDeleteMsg']
        return render(request,'reportMissingPayment/missing-payment-list.html',context)
    def post(self, request):
        if request.POST.get('action_type') == 'delete_tracepayment':
            id = request.POST.get('tracepayment_id')
            try:
                tracepayment = Incomingtracepayment.objects.get(createdby=request.user,id=id)
                tracepayment.isdeleted = True
                tracepayment.save()
                message = 'Deleted Successfully'
                add_log_action(request, tracepayment, status=f"deleted outward remittance of {tracepayment.amount} {tracepayment.currency.code} from account {tracepayment.account.accountno}", status_id=3)
            except Exception as e:
                logger.info(e)
                message = 'Error'
            if request.session.get('tracePaymentDeleteMsg'):
                del request.session['tracePaymentDeleteMsg']
            request.session['tracePaymentDeleteMsg'] = message
            return redirect('/tracePayment/list')

@method_decorator(login_required, name='dispatch')
class AddTracePayment(View):
    def get(self, request):
        accounts = Accounts.objects.filter(isdeleted=False,createdby=request.user)
        currencies = Currencies.objects.filter(isdeleted=False)
        user_details = Useraccounts.objects.get(isdeleted=False,customer__user=request.user)
        context = {
            'accounts' : accounts,
            'currencies' : currencies,
            'user_details' : user_details
        }
        return render(request,'reportMissingPayment/add-tracepayment.html',context)
    def post(self, request):
        if request.POST.get('CONFIRM'):
            account_id = request.POST.get('AccountId')
            sender_name = request.POST.get('senderName')
            sender_bank = request.POST.get('SenderBank')
            sender_account_number = request.POST.get('senderAccountNo')
            amount = request.POST.get('Amount')
            currency_id = request.POST.get('CurrencyId')
            booking_date = request.POST.get('BookingDate')
            invoice_doc = request.FILES.get('invoice-doc')
            reference = request.POST.get('Reference')
            def validate():
                if not account_id:
                    return {
                        'status' : False,
                        'message' : 'Account Number is required.'
                    }
                elif not amount:
                    return {
                        'status' : False,
                        'message' : 'Amount is required.'
                    }
                elif not currency_id:
                    return {
                        'status' : False,
                        'message' : 'Currency is required.'
                    }
                elif invoice_doc:
                    ext = os.path.splitext(invoice_doc.name)[1]
                    filesize = invoice_doc.size
                    if not ext in settings.ALLOWED_FORMATS:
                        return {
                            'status' : False,
                            'message' : 'Incorrect file format',
                            }
                    elif filesize > settings.MAX_FILE_SIZE:
                        return {
                            'status' : False,
                            'message' : 'Maximum file size allowed is 10 MB',
                            }
                    elif not all(ord(c) < 128 for c in invoice_doc.name):
                        return {
                            'status' : False,
                            'message' : 'Special characters should not be in file name',
                            }
                elif not checkNonAsciiChracters([sender_name,sender_bank,reference]):
                    return {
                            'status': False,
                            'message': "Fancy characters are not allowed"
                        }
                return {
                    'message' : 'Submitted Successfully',
                    'status' : True
                }
            data = validate()
            if data.get('status'):
                incoming_trace_payment = Incomingtracepayment.objects.create(
                    account = Accounts.objects.get(id=account_id),
                    sendername = sender_name,
                    senderbank = sender_bank,
                    senderaccountno = sender_account_number,
                    amount = amount,
                    bookingdate = booking_date if booking_date else None,
                    paymentattachment = invoice_doc,
                    currency = Currencies.objects.get(id=currency_id),
                    reference=reference,
                    createdby=request.user,
                )
                add_log_action(request, incoming_trace_payment, status=f"created outward remittance of {incoming_trace_payment.amount} {incoming_trace_payment.currency.code} from account {incoming_trace_payment.account.accountno}", status_id=1)
                if request.session.get('tracePaymentSuccessMsg'):
                    del request.session['tracePaymentSuccessMsg']
                request.session['tracePaymentSuccessMsg'] = data.get('message')
                return redirect('/tracePayment/list')
            else:
                accounts = Accounts.objects.filter(isdeleted=False,createdby=request.user)
                currencies = Currencies.objects.filter(isdeleted=False)
                context = {}
                context['accounts'] = accounts
                context['currencies'] = currencies
                context['AccountId'] = account_id
                context['senderName'] = sender_name
                context['SenderBank'] = sender_bank
                context['senderAccountNo'] = sender_account_number
                context['Amount'] = amount
                context['BookingDate'] = booking_date
                context['invoice-doc'] = invoice_doc
                context['Reference'] = reference
                context['CurrencyId'] = currency_id
                context['status'] = False
                context['user_details'] = Useraccounts.objects.get(isdeleted=False,customer__user=request.user)
                context['message'] = data.get('message')
                return render(request,'reportMissingPayment/add-tracepayment.html',context)
        if request.POST.get('CANCEL'):
            if request.session.get('tracePaymentSuccessMsg'):
                del request.session['tracePaymentSuccessMsg']
            if request.session.get('tracePaymentDeleteMsg'):
                del request.session['tracePaymentDeleteMsg']
            return redirect('/tracePayment/list')