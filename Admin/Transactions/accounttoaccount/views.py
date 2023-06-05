

import logging
from django.views import View

from utils.mixins import UtilMixins
from utils.models import Accounts, Currencyconversionmargins, Customers, Otps, Useraccounts,\
     Currencies, Accounts, Transactions, Externalbeneficiaries,Internalbeneficiaries,Transactiontypes, Currencyconversionratescombined
from secrets import token_urlsafe
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.conf import settings
from decimal import Decimal
from Transactions.mixins import OTP, TransactionMail
import datetime
from django.http import HttpResponse
import json
from django.template.loader import get_template
import pdfkit
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from EntrebizAdmin.decorators import template_decorator
logger = logging.getLogger('lessons')

def getInternalbeneficiarylist(request):
    beneficiary_accountnumber = request.POST.get('beneficiary_account')
    internal_beneficiary = Internalbeneficiaries.objects.get(createdby=request.user, account=Accounts.objects.get(accountno=beneficiary_accountnumber),isdeleted=False)
    data = {
        'accountnumber' : internal_beneficiary.account.accountno
        }
    return JsonResponse(data)

def accountbalance(request):
    account_number = request.POST.get("account_number")
    # account = Accounts.objects.get(createdby=request.user,accountno=account_number,isdeleted=False)
    account = Accounts.objects.get(accountno=account_number,isdeleted=False)
    data = {
        'account_balance' : account.balance,
       'account_currency_code' : account.currency.code
    }
    return JsonResponse(data)


@method_decorator(login_required, name='dispatch')
@method_decorator(template_decorator(title="Inter Account Transfers"),name='dispatch')
class AccountToAccountTransferView(View):
    template_name='accounttoaccount/ac-ac-transfer.html'
    
    def get(self, request):
        if request.GET.get('Edit'):
            data = request.session['accounttoaccounttransfer']
        else:
            data = None
        try:
            context = {
                'currencies':Currencies.objects.all(),
                'internalbeneficiaries' : Internalbeneficiaries.objects.filter(createdby=request.user,isdeleted=False),
                'accounts': Accounts.objects.filter(user_account__customer__user=request.user, isdeleted=False),
                'data': data,
                'user_details' : Useraccounts.objects.get(isdeleted=False,customer__user=request.user)
            }
            if request.session.get('cancelAccTrMsg'):
                context['messagee'] = request.session.get('cancelAccTrMsg')
                context['status'] = False
                del request.session['cancelAccTrMsg']
        except Exception as e:
            logger.info(e)
            context={}
        
        return render(request, 'accounttoaccount/ac-ac-transfer.html',context)
    def post(self, request):
        prevdata = request.POST.dict()
        ben_acc_number = request.POST.get('beneficiary_accountnumber')
        try:
            Accounts.objects.get(accountno=ben_acc_number, isdeleted=False)
        except Exception as e:
            logger.info(e)
            context = {
                'data':prevdata,
                'messagee' : 'Invalid credit account!',
                'status':False,
                'accounts': Accounts.objects.filter(user_account__customer__user=request.user, isdeleted=False),
                'internalbeneficiaries' : Internalbeneficiaries.objects.filter(createdby=request.user),
                'user_details' : Useraccounts.objects.get(isdeleted=False,customer__user=request.user)
            }
            # return redirect('accTransaction')
            return render(request,'accounttoaccount/ac-ac-transfer.html',context)
        debit_account_number = request.POST.get('debit_account')
        debit_account = Accounts.objects.get(accountno=debit_account_number)
        if float(request.POST.get('amount')) <  float(debit_account.balance) :
            try:
                del request.session['accounttoaccounttransfer']
                del request.session['token']
            except Exception as e:
                logger.info(e)
                pass
            request.session['accounttoaccounttransfer'] = request.POST.dict()
            beneficiary_account_number = request.POST.get('beneficiary_accountnumber')
            try:
                internal_beneficiary = Internalbeneficiaries.objects.get(createdby=request.user,account=Accounts.objects.get(accountno=beneficiary_account_number),isdeleted=False)
                beneficiary_name = internal_beneficiary.receivername
            except Exception as e:
                logger.info(e)
                beneficiary_name = ''
            benefiary_account=Accounts.objects.get(accountno=beneficiary_account_number)
            from_amount = Decimal(request.POST.get('amount'))
            if debit_account.currency.code == benefiary_account.currency.code:
                conversion_fee = Decimal(0.00)
            else:
                conversion_fee = round(from_amount * Decimal(0.5/100),4)
            try:
                currency_conversion = Currencyconversionratescombined.objects.get(fromcurrency__code=debit_account.currency.code,tocurrency__code=benefiary_account.currency.code, isdeleted=False)
            except Exception as e:
                logger.info(e)
                context = {
                    'data': prevdata,
                    'messagee': 'Having trouble with selected account! Please try with another.',
                    'status': False,
                    'accounts': Accounts.objects.filter(user_account__customer__user=request.user, isdeleted=False),
                    'internalbeneficiaries': Internalbeneficiaries.objects.filter(createdby=request.user),
                    'user_details' : Useraccounts.objects.get(isdeleted=False,customer__user=request.user)
                }
                return render(request, 'accounttoaccount/ac-ac-transfer.html', context)
            
            conversionrate = currency_conversion.conversionrate
            try:
                currency_margin = Currencyconversionmargins.objects.get(fromcurrency__code=debit_account.currency.code,tocurrency__code=benefiary_account.currency.code,isdeleted=False)
                margin_rate = currency_margin.marginpercent
                conversionrate = conversionrate - (conversionrate* Decimal(float(margin_rate)/100))
            except Exception as e:
                logger.info(e)
                pass

            # credit_amount = round(from_amount * currency_conversion.conversionrate,4)
            credit_amount = round(from_amount * conversionrate,4)
            debit_amount = from_amount + conversion_fee
            if debit_amount > float(debit_account.balance):
                context = {
                    'data': prevdata,
                    'messagee': 'Insufficient Balance',
                    'status': False,
                    'accounts': Accounts.objects.filter(user_account__customer__user=request.user, isdeleted=False),
                    'internalbeneficiaries': Internalbeneficiaries.objects.filter(createdby=request.user),
                    'user_details' : Useraccounts.objects.get(isdeleted=False,customer__user=request.user)
                }
                return render(request, 'accounttoaccount/ac-ac-transfer.html', context)
            request.session['accounttoaccounttransfer'].update({
                'beneficiary_name':beneficiary_name,
                'currency_code_beneficiary':benefiary_account.currency.code,
                'currency_code_debit':debit_account.currency.code,
                'conversion_fee' : format(conversion_fee,'4f'),
                'credit_amount' : format(credit_amount,'4f'),
                'debit_amount' : format(debit_amount,'4f'),
                'net_amount' : format(from_amount,'4f')
                    })
            request.session['token'] = token_urlsafe(30)
            return redirect('accConfirmation', request.session['token'])
        else:
            context = {
                'data':prevdata,
                'messagee' : 'Insufficient Balance',
                'status' :False,
                'accounts': Accounts.objects.filter(user_account__customer__user=request.user, isdeleted=False),
                'internalbeneficiaries' : Internalbeneficiaries.objects.filter(createdby=request.user),
                'user_details' : Useraccounts.objects.get(isdeleted=False,customer__user=request.user)
            }
            # return redirect('accTransaction')
            return render(request,'accounttoaccount/ac-ac-transfer.html',context)

@method_decorator(login_required, name='dispatch')
class AccountToAccountCancelView(View):
    def get(self, request):
        try:
            del request.session['accounttoaccounttransfer']
            del request.session['token']
        except Exception as e:
            logger.info(e)
            pass
        # messages.info(request,'Last transaction canceled')
        request.session['cancelAccTrMsg'] = 'Last transaction canceled'
        return redirect('accTransaction')

@method_decorator(login_required, name='dispatch')
class AccountToAccountDetailsView(View):
    template_name = "accounttoaccount/transfer-details.html"
    def get(self, request,token):
        if token==request.session['token']:
           return render(request, 'accounttoaccount/transfer-details.html')
        else:
            #return to home page
            print("invalid token")
            return redirect('/')

    def post(self, request,token):
        access_token = token
        try:
            if request.session.get('cancelAccTrMsg'):
                
                del request.session['cancelAccTrMsg']
        except Exception as e:
            logger.info(e)
            pass
        if request.POST.get('type')=='otpresend':
            user_account = Useraccounts.objects.get(customer__user=request.user)
            full_name = f"{user_account.firstname} {user_account.lastname}"

            otp_status = OTP().send_email_otp(transaction_type=3,created_by=request.user,email=request.user.email,
                                full_name=full_name,token=request.session['token'])
            if otp_status:
                # messages.success(request,'OTP sent, Please verify!')
                request.session['prevToken'] = request.session['token']
                del request.session['token']
                request.session['token'] = token_urlsafe(30)
                data={
                    'message':'OTP resent, Please verify!'
                }
                return JsonResponse(data)
            else:
                messages.error(request,'Could not send OTP')
                return redirect('accConfirmation', request.session['token'])

        elif request.POST.get('sendOtp')=='sendOtp' and access_token:
            user_account = Useraccounts.objects.get(customer__user=request.user)
            full_name = f"{user_account.firstname} {user_account.lastname}"
            otp_status = OTP().send_email_otp(transaction_type=3,created_by=request.user,email=request.user.email,
                                full_name=full_name,token=request.session['token'])
            if otp_status:
                messages.success(request,'OTP sent, Please verify!')
                request.session['prevToken'] = request.session['token']
                del request.session['token']
                request.session['token'] = token_urlsafe(30)
                
                return redirect('accOtp', request.session['token'])
            else:
                messages.error(request,'Could not send OTP')
                return redirect('accConfirmation', request.session['token'])

@method_decorator(login_required, name='dispatch')
class AccountToAccountOTP(View):
    template_name='accounttoaccount/otp-verification.html'
    def get(self,request,token):
        if token==request.session['token']:
            context={}
            
            if request.session.get('Otpfailuremsg'):
                context['messagee'] = request.session['Otpfailuremsg']
                del request.session['Otpfailuremsg']
                context['status'] = False
                    
            
            return render(request, 'accounttoaccount/otp-verification.html',context)
        else:
            return redirect('/')
    def post(self,request,token):
        
        try:
            def validation_fn():
                if not token:
                    return {
                        'status' : False,
                        'error' : 'Your Transaction has been declined due to Security reason'
                    }
                try:
                    otp = Otps.objects.get(code=request.POST.get('otp'),
                                    transactiontype='Account to Account Transfer',
                                    validated=False,
                                    createdby=request.user,token=request.session['prevToken'])
                except Exception as e:
                    logger.info(e)
                    return {
                    'status' : False,
                    'otp_error' : True,
                    'error' : 'Verification failed, wrong user or otp'
                    }
                valid_till = datetime.datetime.now()
                valid_till = valid_till.date().strftime(settings.DATE_FORMAT)
                valid_date = datetime.datetime.strptime(valid_till, settings.DATE_FORMAT)
                
                if valid_date.date() <= otp.validtill:
                    otp.validated = True
                    otp.save()
                    
                    try:
                        # debit_account = Accounts.objects.get(
                        #     createdby=request.user, accountno=request.session['accounttoaccounttransfer']['debit_account']
                        # )
                        debit_account = Accounts.objects.get(accountno=request.session['accounttoaccounttransfer']['debit_account']
                        )
                        credit_account = Accounts.objects.get(
                            accountno=request.session['accounttoaccounttransfer']['beneficiary_accountnumber']
                        )
                        debit_amount = Decimal(request.session['accounttoaccounttransfer']['debit_amount'])
                        net_amount = Decimal(request.session['accounttoaccounttransfer']['net_amount'])
                        conversion_fee = Decimal(request.session['accounttoaccounttransfer']['conversion_fee'])
                        credit_amount = Decimal(request.session['accounttoaccounttransfer']['credit_amount'])
                        db_account_balance = debit_account.balance
                        if db_account_balance < debit_amount:
                            # raise Exception()
                            return {
                                'status' : False,
                                'error' : 'Your Transaction has been declined due to insufficient fund'
                                }
                        cr_account_balance = credit_account.balance
                        debit_accountbalance = Decimal(db_account_balance) - net_amount
                        credit_accountbalance = Decimal(cr_account_balance) + credit_amount
                        debit_account.balance = debit_accountbalance
                        debit_account.save()
                        credit_account.balance = credit_accountbalance
                        credit_account.save()
                        try:
                            account_number_prev = Transactions.objects.latest('transactionno').transactionno
                        except Exception as e:
                            logger.info(e)
                            account_number_prev = 10000000
                        transactionno = int(account_number_prev) + 1
                        def create_transaction(transactionno,debit_account,credit_account,fromamount,toamount,debit_balance,credit_balance,amount_type):
                            transaction_obj = Transactions.objects.create(
                                transactionno=transactionno,
                                fromaccount=debit_account,
                                toaccount=credit_account,
                                fromamount=fromamount,
                                toamount=toamount,
                                transactiontype=Transactiontypes.objects.get(name='Acccount To Account Transfer'),
                                createdby=request.user,
                                note=request.session['accounttoaccounttransfer']['note'],
                                recipientname=request.session['accounttoaccounttransfer']['beneficiary_name'],
                                fromaccountbalance=debit_balance,
                                toaccountbalance=credit_balance,
                                amount_type=amount_type
                            )
                            return transaction_obj
                        try:
                            net_amount = request.session.get("accounttoaccounttransfer").get("net_amount")
                            amount_type = "Net Amount"
                            create_transaction(transactionno, debit_account, credit_account, net_amount,
                                               credit_amount,
                                               debit_accountbalance, credit_accountbalance, amount_type)
                        except Exception as e:
                            logger.info(e)
                            return {
                                'status': False,
                                'error': 'Something went wrong! Please try again.'
                            }
                        try:
                            master_credit_account = Accounts.objects.get(user_account__ismaster_account=True,
                                                                  currency=debit_account.currency, isdeleted=False)
                            debit_account.balance -= Decimal(conversion_fee)
                            master_credit_account.balance += Decimal(conversion_fee)
                            debit_account.save()
                            master_credit_account.save()
                            debit_balance = debit_account.balance
                            credit_balance = credit_account.balance

                            amount_type = "Conversion Fee"
                            create_transaction(transactionno, debit_account, credit_account, conversion_fee,
                                               conversion_fee,
                                               debit_balance, credit_balance, amount_type)

                        except Exception as e:
                            logger.info(e)
                            return {
                                'status': False,
                                'error': 'Something went wrong! Please try again.'
                            }

                        request.session['accounttoaccounttransfer'].update({
                            'transactionnumber':transactionno,
                            'date_and_time' : datetime.datetime.utcnow().strftime("%d %b %Y, %-H:%M UTC")
                        })
                        if request.session['prevToken']:
                            del request.session['prevToken']
                        if request.session.get('token'):
                            del request.session['token']
                            request.session['token'] = token_urlsafe(30)
                        #send success mail here
                        return {
                            'status' : True
                            
                            }
                        
                        # return redirect('accSuccess', request.session['token'])
                    except Exception as e:
                        logger.info(e)
                        return redirect('accSuccess', request.session['token'])
                else:
                    return {
                    'status' : False,
                    'error' : 'Your Transaction has been declined due to Expired OTP you entered'
                    }
            response = validation_fn()
            if response and not response.get('status'):
                # SEND FAILURE EMAIL HERE
                # messages.error(request,response.get('error'))
                request.session['Otpfailuremsg'] = response.get('error')
                if response.get('otp_error') == True:
                    return redirect('accOtp', request.session['token'])
                user_account = Useraccounts.objects.get(customer__user=request.user)
                full_name = f"{user_account.firstname} {user_account.lastname}"
                context={
                    'error' : True,
                    'message' : response.get('error'),
                    'year':str(datetime.date.today().year),
                    'user':full_name
                }
                transaction_mail_status=TransactionMail().transaction_success_or_failure_mail(email=request.user.email,email_data=context,status=False)
                return redirect('accOtp', request.session['token'])
            elif response.get('status'):
                context={
                    'acc_acc_transfer' : True,
                    'transactionno':request.session['accounttoaccounttransfer']['transactionnumber'],
                    'fromaccount': request.session['accounttoaccounttransfer']['debit_account'],
                    'from_currency_code':request.session['accounttoaccounttransfer']['currency_code_debit'],
                    'beneficiary_accno': request.session['accounttoaccounttransfer']['beneficiary_accountnumber'],
                    'credit_currency_code':request.session['accounttoaccounttransfer']['currency_code_beneficiary'],
                    'beneficiary_name':request.session['accounttoaccounttransfer']['beneficiary_name'],
                    'amount':request.session['accounttoaccounttransfer']['amount'],
                    'conversion_fee':request.session['accounttoaccounttransfer']['conversion_fee'],
                    'debit_amount':request.session['accounttoaccounttransfer']['debit_amount'],
                    'credit_amount':request.session['accounttoaccounttransfer']['credit_amount'],
                    'note':request.session['accounttoaccounttransfer']['note'],
                    'transaction_datetime_utc':request.session['accounttoaccounttransfer']['date_and_time']
                    }
                transaction_mail_status=TransactionMail().transaction_success_or_failure_mail(email=request.user.email,email_data=context,status=True,attach=None)
                return redirect('accSuccess', request.session['token'])
            
        except Exception as e:
            logger.info(e)
            #logout
            #SEND FAILURE EMAIL HERE
            user_account = Useraccounts.objects.get(customer__user=request.user)
            full_name = f"{user_account.firstname} {user_account.lastname}"
            context = {
                'user':full_name
            }
            send_email=TransactionMail().transaction_success_or_failure_mail(email=request.user.email,email_data=context,status=False,attach=None)
            if send_email and request.user:
                # messages.error(request,'Verification failed, wrong user or otp')
                return redirect('accOtp', request.session['token'])
            else:
                return redirect('accOtp', request.session['token'])
            
@method_decorator(login_required, name='dispatch')
class AccountToAccountOTPSuccess(View):
    def get(self,request,token):
        storage = messages.get_messages(request)
        storage.used = True
        if request.GET.get("export_pdf"):
            response = {}
            invoice = f"transaction{request.session['accounttoaccounttransfer'].get('transactionnumber')}.pdf"
            context = {
                'transaction_number':request.session['accounttoaccounttransfer']['transactionnumber'],
                'debit_account': request.session['accounttoaccounttransfer']['debit_account'],
                'debit_currency_code':request.session['accounttoaccounttransfer']['currency_code_debit'],
                'credit_account': request.session['accounttoaccounttransfer']['beneficiary_accountnumber'],
                'credit_currency_code':request.session['accounttoaccounttransfer']['currency_code_beneficiary'],
                'beneficiary_name':request.session['accounttoaccounttransfer']['beneficiary_name'],
                'net_amount':request.session['accounttoaccounttransfer']['amount'],
                'conversion_fee': request.session['accounttoaccounttransfer']['conversion_fee'],
                'debit_amount':request.session['accounttoaccounttransfer']['debit_amount'],
                'credit_amount':request.session['accounttoaccounttransfer']['credit_amount'],
                'note':request.session['accounttoaccounttransfer']['note'],
                'Date_and_Time':request.session['accounttoaccounttransfer']['date_and_time']

                }
            file = render_pdf('accounttoaccount/transaction-invoice.html', context, invoice)
            response['filepath'] = settings.AWS_S3_BUCKET_URL+'invoices/'+invoice
            return HttpResponse(json.dumps(response),content_type='application/json')
            
        else:
            if  token != request.session.get('token') or not token or not request.session['accounttoaccounttransfer']:
                # logout here
                return redirect('/')
            if token == request.session.get('token'):
                return render(request, 'accounttoaccount/transaction-success.html')
    def post(self,request,token):
        if request.POST.get('action_type') == 'add_as_ben':
            try:
                account = Accounts.objects.get(accountno=request.POST.get('account_id'), isdeleted=False)
                customer = Customers.objects.get(user=request.user)
                ben_nickname = request.POST.get('NickName')
            except Exception as e:
                logger.info(e)
                messages.error(request,'Receiver Account number not exist')
                return redirect('accSuccess', request.session['token'])
            try:
                if Internalbeneficiaries.objects.filter(account=account, createdby=request.user,
                                                        receivername=ben_nickname, isdeleted=False).exists():
                    message = 'Beneficiary with this nick name already exist'
                elif Internalbeneficiaries.objects.filter(account=account, createdby=request.user, isdeleted=False).exists():
                    message = 'Beneficiary already exist'
                messages.error(request,message)
                return redirect('accSuccess', request.session['token'])
            except Exception as e:
                logger.info(e)
                pass
            internal_ben = Internalbeneficiaries.objects.create(receivername=ben_nickname,
                            account=account,createdby=request.user,customer=customer)
            messages.success(request,'Beneficiary added successfully')
            return redirect('accSuccess', request.session['token'])

        elif request.POST.get('action_type') == 'email_send':
            user_account = Useraccounts.objects.get(customer__user=request.user)
            full_name = f"{user_account.firstname} {user_account.lastname}"
            email_data = {
                    'mail_attach' : True,
                    'from_currency_code':request.session['accounttoaccounttransfer']['currency_code_debit'],
                    'amount':request.session['accounttoaccounttransfer']['amount'],
                    'year':str(datetime.date.today().year),
                    'user' : full_name
                }
            response={}
            invoice = f"transaction{request.session['accounttoaccounttransfer'].get('transactionnumber')}.pdf"
            user_account = Useraccounts.objects.get(customer__user=request.user)
            full_name = f"{user_account.firstname} {user_account.lastname}"
            context = {
                    'transaction_number':request.session['accounttoaccounttransfer']['transactionnumber'],
                    'debit_account': request.session['accounttoaccounttransfer']['debit_account'],
                    'debit_currency_code':request.session['accounttoaccounttransfer']['currency_code_debit'],
                    'credit_account': request.session['accounttoaccounttransfer']['beneficiary_accountnumber'],
                    'credit_currency_code':request.session['accounttoaccounttransfer']['currency_code_beneficiary'],
                    'beneficiary_name':request.session['accounttoaccounttransfer']['beneficiary_name'],
                    'net_amount':request.session['accounttoaccounttransfer']['amount'],
                    'conversion_fee':request.session['accounttoaccounttransfer']['conversion_fee'],
                    'debit_amount':request.session['accounttoaccounttransfer']['debit_amount'],
                    'credit_amount':request.session['accounttoaccounttransfer']['credit_amount'],
                    'note':request.session['accounttoaccounttransfer']['note'],
                    'Date_and_Time':request.session['accounttoaccounttransfer']['date_and_time'],
                    'user'  : full_name
                    }
            file = render_pdf('accounttoaccount/transaction-invoice.html', context, invoice)
            response['filepath'] = settings.AWS_S3_BUCKET_URL+'invoices/'+invoice
            
            transaction_mail_status=TransactionMail().transaction_success_or_failure_mail(email=request.user.email,email_data=email_data,status=True, attach=file)
            if transaction_mail_status:
                messages.success(request,'Email sent successfully')
                return redirect('accSuccess', request.session['token'])
            else:
                messages.error(request,'Error')
                return redirect('accSuccess', request.session['token'])

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
    cloudpath = 'invoices/'+upload_filename
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

def page_not_found_view(request, exception):
    return render(request, 'common/404.html', status=404)

def server_error(request, exception=None):
    return render(request, 'common/500.html', status=500)

def server_unavailable(request, exception=None):
    return render(request, 'common/503.html', status=503)

def access_forbidden(request, reason=""):
    return redirect("/")
