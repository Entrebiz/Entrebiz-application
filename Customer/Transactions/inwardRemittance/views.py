from django.shortcuts import render, redirect
from django.views import View
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from Transactions.mixins import add_log_action, checkNonAsciiChracters
from utils.models import Accounts, Bankdetail, Receivemoney, Useraccounts
import os
from django.utils.decorators import method_decorator
from EntrebizAdmin.decorators import template_decorator
import logging
logger = logging.getLogger('lessons')

@method_decorator(login_required, name='dispatch')
@method_decorator(template_decorator(title="Inward Remittance"),name='dispatch')
class InwardRemittance(View):
    def get(self, request):
        context = {}
        if request.session.get('inwardRemittanceDetails'):
            context = request.session.get('inwardRemittanceDetails')
        if request.session.get('receiveMoneyErrorMsg'):
            context['message'] = request.session.get('receiveMoneyErrorMsg')
            del request.session['receiveMoneyErrorMsg']
        return render(request,'accounts/inward-remittance/inward-remittance.html',context)
    def post(self, request):
        if request.session.get('inwardRemittanceDetails'):
            del request.session['inwardRemittanceDetails']
        request.session['inwardRemittanceDetails'] = request.POST.dict()
        def validate(request):
            bank_id = request.POST.get('bank')
            account_id = request.POST.get('Currency')
            sender_name = request.POST.get('SenderName')
            sender_acc_number = request.POST.get('SenderAccountNo')
            sender_bank_name = request.POST.get('SenderBankName')
            sender_country = request.POST.get('SenderCountry')
            swift_code = request.POST.get('SwiftCode')
            amount = request.POST.get('Amount')
            reference = request.POST.get('Reference')
            invoice_doc = request.FILES.get('invoice-doc')
            if not amount:
                return {
                    'status' : False,
                    'message' : 'Please enter the amount' 
                }
            elif sender_acc_number and not sender_acc_number.isalnum():
                 return {
                    'status' : False,
                    'message' : 'Account number should not contain any special characters' 
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
            elif not checkNonAsciiChracters([sender_name,sender_bank_name,sender_country,swift_code,reference]):
                return {
                        'status': False,
                        'message': "Fancy characters not allowed"
                    }
            try:
                bank_details = Bankdetail.objects.get(id=bank_id,isdeleted=False)
            except Exception as e:
                logger.info(e)
                return {
                    'status' : False,
                    'message' : 'selected bank is not available' 
                }
            try:
                receive_money = Receivemoney.objects.create(
                    receiveraccount = Accounts.objects.get(id=account_id),
                    senderaccountno = sender_acc_number,
                    sendername = sender_name,
                    swiftcode = swift_code,
                    amount = amount,
                    reference=reference,
                    payment_proof = invoice_doc,
                    sendercountry = sender_country,
                    senderbankname = sender_bank_name,
                    bank = Bankdetail.objects.get(id=bank_id),
                    createdby = request.user
                )
                add_log_action(request, receive_money, status=f"created inward remittance of {receive_money.amount} {receive_money.receiveraccount.currency.code}", status_id=1)
            except Exception as e:
                logger.info(e)
                return {
                    'status' : False,
                    'message' : 'Error Occured' 
                }
            return {
                'status' : True
            }
        data = validate(request)
        if data.get('status'):
            if request.session.get('receiveMoneySuccess'):
                del request.session['receiveMoneySuccess']
            request.session['receiveMoneySuccess'] = True
            return redirect('/receiveMoneySuccess')
        else:
            if request.session.get('receiveMoneyErrorMsg'):
                del request.session['receiveMoneyErrorMsg']
            request.session['receiveMoneyErrorMsg'] = data.get('message')
            return redirect('/receiveMoney')

@method_decorator(login_required, name='dispatch')
class InwardRemittanceSuccess(View):
    def get(self, request):
        if request.session.get('inwardRemittanceDetails'):
            del request.session['inwardRemittanceDetails']
        if request.session.get('receiveMoneySuccess'):
            del request.session['receiveMoneySuccess']
            return render(request,'accounts/inward-remittance/inward-remittance-success.html')
        return redirect('/receiveMoney')

@method_decorator(login_required, name='dispatch')
class BankDetails(View):
    def get(self, request):
        if request.GET.get('for bank name'):
            acc_id = request.GET.get('acc_id')
            acc = Accounts.objects.get(id=acc_id)
            currency_code = acc.currency.code
            bank_details = Bankdetail.objects.filter(currency__code=currency_code,isdeleted=False).values()
            context = { 'bank_details' : bank_details}
            try:
                if request.session.get('inwardRemittanceDetails'):
                    context['bank'] = int(request.session['inwardRemittanceDetails']['bank'])
                    del request.session['inwardRemittanceDetails']
            except Exception as e:
                logger.info(e)
                pass
            template = render_to_string('accounts/inward-remittance/select-bank-dropdown.html',context)
            template1 = render_to_string('accounts/inward-remittance/bank-details-fields.html')
            response = {'bank_details' : template, 'bank_details_fields' : template1}
        elif request.GET.get('for bank details'):
            bank_id = request.GET.get('bank_id')
            bank_details = Bankdetail.objects.get(id=bank_id,isdeleted=False)
            context = { 'bank_details' : bank_details}
            template = render_to_string('accounts/inward-remittance/bank-details.html',context)
            response = {'bank_details' : template}
        return JsonResponse(response)
