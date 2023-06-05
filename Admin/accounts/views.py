import datetime
import json
import re
import logging
from decimal import Decimal
from secrets import token_urlsafe
from calendar import monthrange
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView

from Transactions.mixins import OTP, ConfirmYourMail, randomword, acc_list
from accounts.forms import ExternalBeneficiaryForm, InternalBeneficiaryForm
from UserDetails.forms import UserDetailsForm
from entrebiz import settings
from utils.models import Activationlinks, Customerdocuments, Documentfields, Documenttypes, Internalbeneficiaries, Accounts, Useraccounts, Externalbeneficiaries, Countries, Currencies, \
    Customers, Activitylog, Otps
from EntrebizAdmin.decorators import template_decorator
logger = logging.getLogger('lessons')
class DashboardView(View):
    def get(self, request):
        template_name = 'common/landing-page.html'
        if request.user.is_authenticated:
            if request.session.get('page_check_token'):
                del request.session['page_check_token']
            else:
                pass
            return redirect('/dashboard')
        return render(request, template_name)


class LoginView(View,OTP):
    def get(self, request):
        context = {}
        if request.session.get('login_message'):
            context['msg'] = request.session.get('login_message')
            context['status'] = True
            del request.session['login_message']
        try:
            user = request.user.customer_details.all()[0].useracc_customer.all()[0]
        except Exception as e:
            logger.info(e)
            user = False
        if request.user.is_authenticated and user:
            return redirect('/dashboard')
        return render(request, 'accounts/login/login.html',context)

    def post(self, request):
        message = ''
        if request.method == 'POST':
            email = request.POST['email']
            password = request.POST['password']
            try:
                user = User.objects.get(email=email)
                if user.check_password(password):
                    try:
                        user_account = Useraccounts.objects.get(customer__user=user, isdeleted=False)
                        if user_account.twofactorauth:
                            token = token_urlsafe(30)
                            request.session['login_token'] = token
                            request.session['isTwoStepPassed'] = 0
                            request.session['user_email'] = user.email
                            full_name = f"{user_account.firstname} {user_account.lastname}"
                            self.send_email_otp(5,created_by=user, email=user.email,full_name=full_name,token=token,
                                                activation_code=None)
                            return redirect('/twoStepVerification')
                        else:
                            login(request, user)
                            Activitylog.objects.create(user=user, activity="login",
                                                       activitytime=datetime.datetime.now())

                            useraccount = Useraccounts.objects.get(customer__user=request.user)
                            if useraccount.activestatus.lower() == "deactivated by ubo":
                                message = "Account is deactivated by UBO."
                            elif useraccount.activestatus.lower() == "suspended":
                                message = "Your account is suspended, please contact support@entrebiz-pte.com"
                            elif useraccount.activestatus.lower() == "rejected":
                                message = "Your account is rejected, please contact support@entrebiz-pte.com"
                            elif useraccount.islocked:
                                message = "Your account is locked, please contact support@entrebiz-pte.com"
                            else:
                                try:
                                    customer_type = Customers.objects.get(user=request.user).customertype
                                    # useraccount = Useraccounts.objects.get(customer__user=request.user)
                                    if customer_type == 1:
                                        if not useraccount.dateofbirth and not useraccount.nationality:
                                            return redirect('/pageStatus/?page=1')
                                        elif not Customerdocuments.objects.filter(customer__user=request.user,documenttype__description='ID verification proof').exists():
                                            return redirect('/pageStatus/?page=2')
                                        elif not Customerdocuments.objects.filter(customer__user=request.user,documenttype__description='Address verification proof').exists():
                                            return redirect('/pageStatus/?page=3')
                                    else:
                                        # useraccount = Useraccounts.objects.get(customer__user=request.user)
                                        if not Customerdocuments.objects.filter(customer__user=request.user,documenttype__name='Registration certificate').exists():
                                            token = token_urlsafe(30)
                                            request.session['page_check_token']=token
                                            return redirect('/documentVerification/companyEdit')
                                        else:
                                            if not useraccount.dateofbirth and not useraccount.nationality:
                                                return redirect('/pageStatus/?page=1')
                                            elif not Customerdocuments.objects.filter(customer__user=request.user,documenttype__description='ID verification proof').exists():
                                                return redirect('/pageStatus/?page=2')
                                            elif not Customerdocuments.objects.filter(customer__user=request.user,documenttype__description='Address verification proof').exists():
                                                return redirect('/pageStatus/?page=3')
                                except Exception as e:
                                    logger.info(e)
                                    pass
                                return redirect("/")
                    except Useraccounts.DoesNotExist:
                        logger.info('Account Does not exist')
                        message = "Account Does not exist"
                    except Exception as e:
                        logger.info(e)
                        message = "Something went wrong! Please try again."


                else:
                    message = 'Incorrect email or password'
            except Exception as e:
                logger.info(e)
                message = 'Incorrect email or password'

        return render(request, 'accounts/login/login.html', {'message': message})


@method_decorator(login_required, name='dispatch')
class ManageBeneficiaryView(View):
    def get(self, request):
        context = {}
        context['currencies'] = Currencies.objects.all()
        context['countries'] = Countries.objects.all()
        return render(request, 'accounts/beneficiary/add-beneficiary.html', context)

    def post(self, request):
        ben_type = request.POST.get("beneficiary_type")
        if ben_type == "transaction":
            ben_nickname = request.POST.get("ben_nickname")

            def validation(request):
                accountno = request.POST.get("int_accountnumber")
                first_name = request.POST.get("firstname")
                last_name = request.POST.get("lastname")
                user_type = request.POST.get("user_type")
                status = True
                try:
                    account_obj = Accounts.objects.get(accountno=accountno,isdeleted=False)
                    if account_obj.createdby == request.user:
                        return {
                            'status': False,
                            'error': "Cannot add own account as beneficiary!"
                        }
                except Exception as e:
                    logger.info(e)
                    return {
                        'status': False,
                        'error': "Receiver Account number not exist"
                    }
                try:
                    customer = request.user.customer_details.all()[0]
                except Exception as e:
                    logger.info(e)
                    return {
                        'status': False,
                        'error': "Customer details not found"
                    }
                user_acc = account_obj.user_account
                if not first_name or first_name == "":
                    return {
                        'status': False,
                        'error': "First Name missing"
                    }
                if user_acc.firstname != first_name:
                    name = "First Name" if user_type == "personal" else "Company Name"
                    return {
                        'status': False,
                        'error': "{} doesn't match".format(name)
                    }
                if user_type == "personal":
                    if not user_acc.lastname:
                        return {
                            'status': False,
                            'error': "Account details doesn't match"
                        }
                    if not last_name or last_name == "":
                        return {
                            'status': False,
                            'error': "Last Name missing"
                        }
                    if user_acc.lastname != last_name:
                        return {
                            'status': False,
                            'error': "Last Name doesn't match"
                        }
                if Internalbeneficiaries.objects.filter(account=account_obj, createdby=request.user, isdeleted=False):
                    return {
                        'status': False,
                        'error': "Beneficiary exist"
                    }
                if Internalbeneficiaries.objects.filter(account=account_obj, createdby=request.user,
                                                        receivername=ben_nickname, isdeleted=False):
                    return {
                        'status': False,
                        'error': "Nick name already exist"
                    }

                return {
                    'status': status,
                    'account_obj': account_obj,
                    'customer': customer
                }

            data = validation(request)
            context = json.loads(json.dumps(request.POST))
            if data.get("status"):
                account_obj = data.get("account_obj")
                customer = data.get("customer")
                created_on = datetime.datetime.now()
                modified_on = datetime.datetime.now()
                Internalbeneficiaries.objects.get_or_create(receivername=ben_nickname, account=account_obj,
                                                            createdon=created_on, createdby=request.user,
                                                            modifiedon=modified_on, modifiedby=request.user,
                                                            customer=customer)
                context['status'] = True
                context['message'] = "Beneficiary Successfully Added!"
                request.session['beneficiary_update_message'] = "Beneficiary Successfully Added!"
                return redirect('/beneficiary/list/?type=transaction')
            else:
                context['status'] = False
                context['message'] = data.get("error")
                return render(request, 'accounts/beneficiary/add-beneficiary.html', context)
        else:
            form = ExternalBeneficiaryForm(request.POST)
            context = json.loads(json.dumps(request.POST))
            context['currencies'] = Currencies.objects.all()
            context['countries'] = Countries.objects.all()
            if form.is_valid():
                save_form = form.save(commit=False)
                save_form.country = Countries.objects.get(id=request.POST.get('country'))
                save_form.currency = Currencies.objects.get(id=request.POST.get('currency'))
                save_form.customer = Customers.objects.get(user=request.user)
                save_form.createdby = request.user
                save_form.save()
                context['message'] = "Beneficiary Successfully Added!"
                request.session['beneficiary_update_message'] = "Beneficiary Successfully Added!"
                return redirect('/beneficiary/list/?type=international')
            else:
                context['form'] = form
            return render(request, 'accounts/beneficiary/add-beneficiary.html', context)


@method_decorator(login_required, name='dispatch')
@method_decorator(template_decorator(title="Beneficiary"),name='dispatch')
class BeneficiaryListView(View):
    def get(self, request):
        context = {}

        list_type = request.GET.get("type")
        if request.session.get('beneficiary_update_message'):
            context['status'] = True
            context['message'] = request.session.get('beneficiary_update_message')
            del request.session['beneficiary_update_message']
        if list_type and list_type == "international":
            context['list_type'] = "international"
            context['external_benificiaries'] = Externalbeneficiaries.objects.filter(createdby=request.user,
                                                                                     isdeleted=False)
        else:
            context['list_type'] = "transaction"
            context['internal_benificiaries'] = Internalbeneficiaries.objects.filter(createdby=request.user,
                                                                                     isdeleted=False)

        return render(request, 'accounts/beneficiary/list-beneficiary.html', context)

    def post(self, request):
        context = {}
        list_type = request.POST.get("beneficiary_type")
        if list_type == "international":
            context['external_benificiaries'] = Externalbeneficiaries.objects.filter(createdby=request.user,
                                                                                     isdeleted=False)
        else:
            context['internal_benificiaries'] = Internalbeneficiaries.objects.filter(createdby=request.user,
                                                                                     isdeleted=False)
        context['list_type'] = list_type
        return render(request, 'accounts/beneficiary/list-beneficiary.html', context)


@method_decorator(login_required, name='dispatch')
class UpdateBeneficiaryView(View):
    def get(self, request):
        slug = request.GET.get("slug")
        context = {}
        if not slug or slug == "":
            return redirect('/beneficiary/list/')
        try:
            Internalbeneficiaries.objects.get(slug=slug, isdeleted=False)
            bentype = 'transaction'
        except Exception as e:
            logger.info(e)
            try:
                Externalbeneficiaries.objects.get(slug=slug, isdeleted=False)
                bentype = 'international'
            except Exception as e:
                logger.info(e)
                return redirect('/beneficiary/list/')
        try:
            if bentype == 'transaction':
                ben_obj = Internalbeneficiaries.objects.get(slug=slug, isdeleted=False)
                context = {'id': ben_obj.id, 'name': ben_obj.receivername, 'accountnumber': ben_obj.account.accountno,
                           'firstname': ben_obj.account.user_account.firstname,
                           'lastname': ben_obj.account.user_account.lastname,
                           }
            else:
                ben_obj = Externalbeneficiaries.objects.get(slug=slug, isdeleted=False)
                context = {'id': ben_obj.id, 'name': ben_obj.name, 'accountnumber': ben_obj.accountnumber,
                           'bankname': ben_obj.bankname, 'swiftcode': ben_obj.swiftcode, 'city': ben_obj.city,
                           'country': ben_obj.country.id if ben_obj.country else None, 'currency': ben_obj.currency.id if ben_obj.currency else None, 'email': ben_obj.email,
                           'currencies': Currencies.objects.all(), 'countries': Countries.objects.all()}
            context['beneficiary_type'] = bentype

        except Exception as e:
            logger.info(e)
            pass
        return render(request, 'accounts/beneficiary/edit-beneficiary.html', context)

    def post(self, request):
        if request.POST.get("action_type") == 'delete':
            slug = request.POST.get("slug")
            bentype = request.POST.get("bentype")
            status = True
            if bentype == 'transaction':
                try:
                    intobj = Internalbeneficiaries.objects.get(slug=slug, isdeleted=False)
                    intobj.isdeleted = True
                    intobj.save()
                except Exception as e:
                    logger.info(e)
                    status = False
            elif bentype == 'international':
                try:
                    extobj = Externalbeneficiaries.objects.get(slug=slug, isdeleted=False)
                    extobj.isdeleted = True
                    extobj.save()
                except Exception as e:
                    logger.info(e)
                    status = False
            return HttpResponse(json.dumps({'status': status}), content_type='application/json')
        else:
            ben_id = request.POST.get("id")
            accountnumber = request.POST.get("accountnumber")
            name = request.POST.get("name")
            context = json.loads(json.dumps(request.POST))
            context['currencies'] = Currencies.objects.all()
            context['countries'] = Countries.objects.all()
            context['status'] = True
            beneficiary_type = request.POST.get("beneficiary_type")
            context['beneficiary_type'] = beneficiary_type

            if beneficiary_type == 'transaction':
                context['status'] = True
                ben_obj = Internalbeneficiaries.objects.get(id=ben_id, isdeleted=False)
                try:
                    account_obj = Accounts.objects.get(accountno=accountnumber)
                    if account_obj.createdby == request.user:
                        context['status'] = False
                        context['firstname'] = ben_obj.account.user_account.firstname
                        context['lastname'] = ben_obj.account.user_account.lastname
                        context['message'] = "Cannot add own account as beneficiary!"
                    elif Internalbeneficiaries.objects.filter(~Q(id=ben_id), account=account_obj,
                                                              createdby=request.user, isdeleted=False):
                        context['status'] = False
                        context['firstname'] = ben_obj.account.user_account.firstname
                        context['lastname'] = ben_obj.account.user_account.lastname
                        context['message'] = "Beneficiary exist!"
                    elif Internalbeneficiaries.objects.filter(~Q(id=ben_id), createdby=request.user,
                                                              receivername=name, isdeleted=False):

                        context['status'] = False
                        context['firstname'] = ben_obj.account.user_account.firstname
                        context['lastname'] = ben_obj.account.user_account.lastname
                        context['message'] = "Nick name already exist!"


                except Exception as e:
                    logger.info(e)
                    context['firstname'] = ben_obj.account.user_account.firstname
                    context['lastname'] = ben_obj.account.user_account.lastname
                    context['status'] = False
                    context['message'] = "Account number does not exists!"
                    return render(request, 'accounts/beneficiary/edit-beneficiary.html', context)
                if context['status'] == True:
                    ben_obj.account = account_obj
                    ben_obj.receivername = name
                    ben_obj.save()
                    context['message'] = "Beneficiary Successfully Updated!"
                    request.session['beneficiary_update_message'] = "Beneficiary Successfully Updated!"
                    return redirect('/beneficiary/list/?type=transaction')
            else:
                ben_obj = Externalbeneficiaries.objects.get(id=ben_id, isdeleted=False)
                form = ExternalBeneficiaryForm(request.POST, instance=ben_obj)
                if form.is_valid():
                    save_form = form.save(commit=False)
                    save_form.country = Countries.objects.get(id=request.POST.get('country'))
                    save_form.currency = Currencies.objects.get(id=request.POST.get('currency'))
                    save_form.customer = Customers.objects.get(user=request.user)
                    save_form.createdby = request.user
                    save_form.save()
                    context['message'] = "Beneficiary Successfully Updated!"
                    request.session['beneficiary_update_message'] = "Beneficiary Successfully Updated!"
                    return redirect('/beneficiary/list/?type=international')
                else:
                    context['status'] = False
                    context['form'] = form
            return render(request, 'accounts/beneficiary/edit-beneficiary.html', context)


@method_decorator(login_required, name='dispatch')
class AccountListView(View):
    def get(self, request):
        context = {}
        user_details = Useraccounts.active.get(customer__user=request.user)
        accounts = Accounts.active.filter(user_account__customer__user=request.user, isdeleted=False).order_by(
            "-createdon")
        if user_details.added_by:
            accounts = acc_list(user_details)
        pr_accounts = accounts.filter(isprimary=1)
        sc_accounts = accounts.filter(isprimary=2)
        context['account_length'] = len(accounts)
        accounts = accounts.filter(isprimary=3)
        context['accounts'] = accounts
        context['pr_accounts'] = pr_accounts
        context['sc_accounts'] = sc_accounts
        context['currencies'] = Currencies.active.all().order_by("code")
        context['media_url'] = settings.MEDIA_URL
        return render(request, 'transactions/currencies/list-accounts.html', context)

    def post(self, request):
        response = {}
        action_type = request.POST.get("action_type")
        if action_type == "update_currency":
            loggeduser = request.user
            user_details = Useraccounts.objects.get(customer__user=request.user)
            if user_details.added_by:
                loggeduser = user_details.added_by.user
                
            acc_id = request.POST.get("acc_id")
            acc_status = int(request.POST.get("acc_status")) if request.POST.get("acc_status") else 0
            try:
                acc_obj = Accounts.objects.get(id=acc_id)
                if acc_status == 1:
                    try:
                        # acc_obj_pr = Accounts.objects.get(user_account__customer__user=request.user, isprimary=1,isdeleted=False)
                        acc_obj_pr = Accounts.objects.get(user_account__customer__user=loggeduser, isprimary=1,isdeleted=False)
                        acc_obj_pr.isprimary = acc_obj.isprimary
                        acc_obj_pr.save()
                    except Exception as e:
                        logger.info(e)
                        pass
                    acc_obj.isprimary = 1
                elif acc_status == 2:
                    try:
                        # acc_obj_sec = Accounts.objects.get(user_account__customer__user=request.user, isprimary=2,isdeleted=False)
                        acc_obj_sec = Accounts.objects.get(user_account__customer__user=loggeduser, isprimary=2,isdeleted=False)
                        acc_obj_sec.isprimary = acc_obj.isprimary
                        acc_obj_sec.save()
                    except Exception as e:
                        logger.info(e)
                        pass
                    acc_obj.isprimary = 2
                acc_obj.save()
                response['status'] = True
            except Exception as e:
                logger.info(e)
                response['status'] = False
        elif action_type == "add-currency":
            loggeduser = request.user
            user_details = Useraccounts.objects.get(customer__user=request.user)
            if user_details.added_by:
                loggeduser = user_details.added_by.user
            currency_id = request.POST.get("currency_id")
            currency_obj = Currencies.objects.get(id=currency_id)
            accountno_list = list(map(int, list(Accounts.objects.filter(user_account__ismaster_account=False).order_by('-accountno').values_list('accountno', flat=True))))
            accountno_list.sort(reverse = True)
            accountno = int(accountno_list[0]) + 1 if accountno_list else settings.DEFAULT_ADD
            acc_obj, created = Accounts.objects.get_or_create(
                # user_account=Useraccounts.objects.get(customer__user=request.user),
                user_account=Useraccounts.objects.get(customer__user=loggeduser),
                # currency=currency_obj, createdby=request.user,isdeleted=False)
                currency=currency_obj, createdby=loggeduser,isdeleted=False)

            message = "{} Currency added to your account successfully!".format(currency_obj.code)
            status = True
            if created:
                accounts = Accounts.active.filter(user_account__customer__user=loggeduser, isdeleted=False)
                if not accounts.filter(isprimary=1):
                    isprimary = 1
                elif accounts.filter(isprimary=1) and not accounts.filter(isprimary=2):
                    isprimary = 2
                else:
                    isprimary = 3
                acc_obj.accountno = accountno
                acc_obj.isprimary = isprimary
                acc_obj.save()
                context = {}
                accounts = Accounts.active.filter(user_account__customer__user=loggeduser, isdeleted=False).order_by(
                    "-createdon")
                pr_accounts = accounts.filter(isprimary=1)
                sc_accounts = accounts.filter(isprimary=2)
                context['account_length'] = len(accounts)
                accounts = accounts.filter(isprimary=3)
                context['accounts'] = accounts
                context['pr_accounts'] = pr_accounts
                context['sc_accounts'] = sc_accounts
                context['currencies'] = Currencies.objects.all()
                context['media_url'] = settings.MEDIA_URL
                response['account_list_html'] = render_to_string('accounts/dashboard/includes/account_list.html',
                                                                 context)
            else:
                message = "Currency already exists!"
                status = False
            response['message'] = message
            response['status'] = status
        return HttpResponse(json.dumps(response), content_type='application/json')


def user_logout(request):
    if request.user.is_authenticated:
            logout(request)
            return redirect('/login')
    return redirect('/login')


@method_decorator(login_required, name='dispatch')
@method_decorator(template_decorator(title="Remove currency"),name='dispatch')
class RemoveCurrencyView(View):
    def get(self,request):
        context = {}

        accounts = Accounts.active.filter(isprimary=3,user_account__customer__user=request.user, isdeleted=False,balance=0).order_by(
            "currency__code")

        if not accounts:
            user_details=Useraccounts.objects.get(customer__user = request.user, isdeleted = False)
            customer = user_details.added_by
            accounts =  Accounts.objects.filter(isprimary=3,user_account__customer=customer, isdeleted=False, balance=0).order_by("currency__code")

        context['accounts'] = accounts
        return render(request,'accounts/currency/remove_currency.html',context)

    def post(self,request):
        context = {}
        account_id = request.POST.get('account_id')
        try:
            account_obj = Accounts.objects.get(~Q(isprimary=1)&~Q(isprimary=2),slug=account_id)
            account_obj.isdeleted = True
            account_obj.save()

            context['message'] = "Account Deleted Successfully"
            context['status'] = True
        except Exception as e:
            logger.info(e)
            context['message'] = "Account not found"
            context['status'] = False
        accounts = Accounts.active.filter(user_account__customer__user=request.user, isdeleted=False,
                                           balance=0).order_by(
            "-createdon")
        context['accounts'] = accounts
        return render(request,'accounts/currency/remove_currency.html',context)


class TwoStepVerificationView(View):
    def get(self,request):
        if request.session.get('isTwoStepPassed') == 0:
            context = {
                'user_email':request.session.get("user_email")
            }
            return render(request,'accounts/login/2FA-otp-verify.html',context)
        else:
            return redirect('/')

    def post(self,request):
        context = {}
        otp = request.POST.get("otp")
        if request.POST.get("action") == "resend":
            token = request.session.get('login_token')
            user_email = request.session.get('user_email')
            try:
                user = User.objects.get(email=user_email)
                user_account = Useraccounts.objects.get(customer__user=user)
                full_name = f"{user_account.firstname} {user_account.lastname}"
                OTP().send_email_otp(5, created_by=user, email=user.email, full_name=full_name, token=token,
                                     activation_code=None)
                context['status'] = True
                context['message'] = 'OTP resent, Please verify!'
            except Exception as e:
                logger.info(e)
                context['status'] = False
                context['message'] = 'Something went wrong! Please try again.'
            return render(request, 'accounts/login/2FA-otp-verify.html', context)
        try:
            user = User.objects.get(email=request.session.get("user_email"))
            try:
                otp_obj = Otps.objects.get(code=otp, token=request.session.get('login_token'),
                                           transactiontype="Login",
                                           createdby=user)
                if not otp_obj.validated:
                    if otp_obj.validtill >= datetime.datetime.now().date():
                        otp_obj.validated = True
                        otp_obj.save()
                        request.session['otp_success_message'] = "OTP Verified!"
                        request.session['isTwoStepPassed'] = 1
                        login(request, user)
                        Activitylog.objects.create(user=user, activity="login", activitytime=datetime.datetime.now())
                        return redirect("/")
                    else:
                        context['status'] = False
                        context['message'] = 'verification failed, otp expired'
                else:
                    context['status'] = False
                    context['message'] = 'verification failed, already validated'
            except Exception as e:
                logger.info(e)
                context['status'] = False
                context['message'] = 'verification failed, wrong user or otp'
        except Exception as e:
            logger.info(e)
            context['status'] = False
            context['message'] = 'Something went wrong! Please try login again.'
        return render(request,'accounts/login/2FA-otp-verify.html',context)

from EntrebizAdmin.decorators import superuser_only
@method_decorator(login_required, name='dispatch')
@method_decorator(superuser_only, name='dispatch')
class PersonalSignUp(View):
    def get(self,request):
        context = {}
        if request.session.get('personalInfo'):
            context = request.session.get('personalInfo')
            del request.session['personalInfo']
        elif request.session.get('personalInfoTemp'):
            context = request.session.get('personalInfoTemp')
            del request.session['personalInfoTemp']
        context['currencies'] = Currencies.objects.filter(isdeleted=False)
        return render(request,'accounts/openaccount/personal-signup/personal-signup.html',context)
    def post(self,request):
        acc_type = request.POST.get('acc_type')
        if acc_type == 'for_new_acc':
            def valiadte(request):
                firstName = request.POST.get('firstName').strip()
                lastName = request.POST.get('lastName').strip()
                email = request.POST.get('email').strip()
                primaryCurrency = request.POST.get('primaryCurrency')
                secondaryCurrency = request.POST.get('secondaryCurrency')
                termsConditions = request.POST.get('termsConditions')
                email_regex = '^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$'
                if not firstName:
                    return {
                        'status' : False,
                        'message' : 'First Name is required'
                    }
                elif not lastName:
                    return {
                        'status' : False,
                        'message' : 'Last Name is required.'
                    }
                elif not email:
                    return {
                        'status' : False,
                        'message' : 'Email is required.'
                    }
                elif email and User.objects.filter(email=email).exists():
                    return {
                    'status' : False,
                    'message' : 'Email already exists'
                    }
                elif not primaryCurrency:
                    return {
                        'status' : False,
                        'message' : '1st Currency is required.'
                    }
                elif not secondaryCurrency:
                    return {
                        'status' : False,
                        'message' : '2nd Currency is required.'
                    }
                elif termsConditions != 'on':
                    return {
                        'status' : False,
                        'message' : 'Please accept terms and conditions'
                    }
                elif email and not re.search(email_regex, email):
                    return {
                        'status' : False,
                        'message' : 'Invalid Email'
                    }
                elif primaryCurrency == secondaryCurrency:
                    return {
                        'status' : False,
                        'message' : 'Please choose a different currency'
                    }
                return {
                    'status' : True
                }
            
            data = valiadte(request)
            if data.get("status"):
                request.session['personalInfo'] = request.POST.dict()
                return redirect('/register/personalSignUpConfirm')
            else:
                context = request.POST.dict()
                context['currencies'] = Currencies.objects.filter(isdeleted=False)
                context['status'] = False
                context['message'] = data.get('message')
                return render(request,'accounts/openaccount/personal-signup/personal-signup.html',context)
        elif acc_type == 'for_exist_acc':
            accountcheck = request.POST.get('accountcheck')
            firstName = request.POST.get('firstName').strip()
            lastName = request.POST.get('lastName').strip()
            email = request.POST.get('email').strip()
            accnumber_list = request.POST.getlist('accnumber')
            balance_list = request.POST.getlist('balance')
            currency_list = request.POST.getlist('currency')
            termsConditions = request.POST.get('termsConditions')
            email_regex = '^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$'
            accnumber_set = set(accnumber_list)
            currency_set = set(currency_list)
            def validate():
                if not firstName:
                    return {
                        'status' : False,
                        'message' : 'First Name is required'
                    }
                elif not lastName:
                    return {
                        'status' : False,
                        'message' : 'Last Name is required.'
                    }
                elif not email:
                    return {
                        'status' : False,
                        'message' : 'Email is required.'
                    }
                elif email and User.objects.filter(email=email).exists():
                    return {
                    'status' : False,
                    'message' : 'Email already exists'
                    }
                elif not all(accnumber_list):
                    return {
                        'status' : False,
                        'message' : 'Account numbers should not be empty'
                    }
                elif not all(balance_list):
                    return {
                        'status' : False,
                        'message' : 'Balance numbers should not be empty'
                    }
                elif not all(currency_list):
                    return {
                        'status' : False,
                        'message' : 'Currency should be selected'
                    }
                elif termsConditions != 'on':
                    return {
                        'status' : False,
                        'message' : 'Please accept terms and conditions'
                    }
                elif email and not re.search(email_regex, email):
                    return {
                        'status' : False,
                        'message' : 'Invalid Email'
                    }
                elif len(accnumber_list) != len(accnumber_set):
                    return {
                        'status' : False,
                        'message' : 'Account numbers should not be same'
                    }
                elif len(currency_list) != len(currency_set):
                    return {
                        'status' : False,
                        'message' : 'Please choose a different currency'
                    }
                elif not all([accnumber.isdigit() for accnumber in accnumber_list]):
                    return {
                        'status' : False,
                        'message' : 'Account number should be a whole number'
                    }
                for accnumber in accnumber_list:
                    if Accounts.objects.filter(isdeleted=False,accountno=accnumber).exists():
                        return {
                            'status' : False,
                            'message' : f'Account number {accnumber} already exist'
                        }
                try:
                    sum([float(balance) for balance in balance_list])
                except Exception as e:
                    logger.info(e)
                    return {
                        'status' : False,
                        'message' : 'Balance should be in numbers'
                    }
                accnumber_and_bal = zip(accnumber_list,balance_list)
                if len(tuple(accnumber_and_bal)) < 2:
                    return {
                        'status' : False,
                        'message' : 'Minimum 2 accounts details should be filled'
                    }
                return {
                    'status' : True
                }
            data = validate()
            account_list = []
            for i in range(len(accnumber_list)):
                account_list.append({
                    'accnumber' : accnumber_list[i],
                    'balance' : balance_list[i],
                    'currency' : currency_list[i],
                })
            if data.get("status"):
                request.session['personalInfoTemp'] = request.POST.dict()
                request.session['personalInfoTemp'].update({
                    'account_lists' : account_list
                })
                return redirect('/register/personalSignUpConfirm')
            else:
                context = {}
                context['currencies'] = Currencies.objects.filter(isdeleted=False)
                context['account_lists'] = account_list
                context['firstName'] = firstName
                context['lastName'] = lastName
                context['email'] = email
                context['accountcheck'] = True if accountcheck == 'on' else False
                context['status'] = False
                context['message'] = data.get('message')
                return render(request,'accounts/openaccount/personal-signup/personal-signup.html',context)

@method_decorator(login_required, name='dispatch')
@method_decorator(superuser_only, name='dispatch')
class PersonalSignUpConfirm(View,ConfirmYourMail):
    def get(self,request):
        if request.session.get('personalInfo'):
            first_currency = Currencies.objects.get(code = request.session['personalInfo'].get('primaryCurrency'))
            second_currency = Currencies.objects.get(code = request.session['personalInfo'].get('secondaryCurrency'))
            context = request.session.get('personalInfo')
            context['first_currency'] = first_currency
            context['second_currency'] = second_currency
            return render(request,'accounts/openaccount/personal-signup/personal-signup-confirm.html',context)
        elif request.session.get('personalInfoTemp'):
            context = request.session.get('personalInfoTemp')
            return render(request,'accounts/openaccount/personal-signup/personal-signup-confirm.html',context)
        else:
            return redirect('/register/personal')
    def post(self,request):
        if request.session.get('personalInfo'):
            user_email = request.session['personalInfo'].get('email')
            firstname = request.session['personalInfo'].get('firstName')
            middlename = request.session['personalInfo'].get('middleName')
            lastname = request.session['personalInfo'].get('lastName')
            primary_currency = request.session['personalInfo'].get('primaryCurrency')
            secondary_currency = request.session['personalInfo'].get('secondaryCurrency')
            full_name = f"{firstname} {lastname}"
            password = User.objects.make_random_password()
            usr_name = randomword(13)
            while True:
                if User.objects.filter(username=usr_name).exists():
                    usr_name = randomword(13)
                else:
                    break
            user = User.objects.create_user(username=usr_name,email=user_email,password=password)
            customer,status = Customers.objects.get_or_create(user=user,customertype=1,agreetermsandconditions=True,createdby=user,isactive=True)
            useraccount,status = Useraccounts.objects.get_or_create(customer=customer,firstname=firstname,middlename=middlename,lastname=lastname)
            for currency in [primary_currency,secondary_currency]:
                accountno_list = list(map(int, list(Accounts.objects.filter(user_account__ismaster_account=False).order_by('-accountno').values_list('accountno', flat=True))))
                accountno_list.sort(reverse = True)
                account,status = Accounts.objects.get_or_create(user_account=useraccount,accountno = int(accountno_list[0]) + 1 if accountno_list else settings.DEFAULT_ADD,
                            currency=Currencies.objects.get(code=currency),accounttype=1,isprimary=1 if currency==primary_currency else 2,createdby=user)
            del request.session['personalInfo']
            mail_status = self.send_confirm_mail(full_name, user_email,createdby=user,transaction_type=1, dev_type=1)
            return render(request,'accounts/openaccount/personal-signup/signup-success.html')
        elif request.session.get('personalInfoTemp'):
            user_email = request.session['personalInfoTemp'].get('email')
            firstname = request.session['personalInfoTemp'].get('firstName')
            middlename = request.session['personalInfoTemp'].get('middleName')
            lastname = request.session['personalInfoTemp'].get('lastName')
            full_name = f"{firstname} {lastname}"
            password = User.objects.make_random_password()
            usr_name = randomword(13)
            while True:
                if User.objects.filter(username=usr_name).exists():
                    usr_name = randomword(13)
                else:
                    break
            user = User.objects.create_user(username=usr_name,email=user_email,password=password)
            customer,status = Customers.objects.get_or_create(user=user,customertype=1,agreetermsandconditions=True,createdby=user,isactive=True)
            useraccount,status = Useraccounts.objects.get_or_create(customer=customer,firstname=firstname,middlename=middlename,lastname=lastname)
            account_lists = request.session['personalInfoTemp']['account_lists']
            count = 1
            for acc in account_lists:
                account,status = Accounts.objects.get_or_create(user_account=useraccount,accountno = acc['accnumber'],balance=Decimal(acc['balance']),
                            currency=Currencies.objects.get(code=acc['currency']),accounttype=1,isprimary=count,createdby=user)
                if count > 2:
                    count = 3
                else:
                    count +=1
            del request.session['personalInfoTemp']
            mail_status = self.send_confirm_mail(full_name, user_email,createdby=user,transaction_type=1, dev_type=1)
            return render(request,'accounts/openaccount/personal-signup/signup-success.html')
        else:
            return redirect('/register/personal')

class SetPassword(View):
    def get(self,request):
        try:
            activation_link = Activationlinks.objects.get(activationcode=request.GET.get('activationLink'),
                                validated=False,isdeleted=False,transactiontype='Confirm your email')
            expirydate = activation_link.validtill
            valid_till = datetime.datetime.now()
            valid_till = valid_till.date().strftime(settings.DATE_FORMAT)
            valid_date = datetime.datetime.strptime(valid_till, settings.DATE_FORMAT)
            submitdate = valid_date.date()
            if expirydate>submitdate and activation_link.validated == False:
                message = 'Activationlink verified'
                context = {}
                context['activationLink'] = activation_link.activationcode
                context['ActivationcodeId'] = activation_link.id
                return render(request,'accounts/openaccount/personal-signup/set-password.html',context)
            else:
                message = 'Activation code expired'
        except Exception as e:
            logger.info(e)
            message = 'Wrong Activation Code'
            return redirect('/')

    def post(self,request):
        def validate(request):
            password = request.POST.get('password').strip()
            confirm_password = request.POST.get('confirmPassword').strip()
            activation_code = request.POST.get('activationLink')
            if not password:
                return {
                    'status' : False,
                    'message' : "Please enter password"
                }
            elif not confirm_password:
                return {
                    'status' : False,
                    'message' : "Please re-enter password"
                }
            elif password != confirm_password:
                return {
                    'status' : False,
                    'message' : "Your passwords does not match"
                }
            elif not re.search("[A-Z]",password):
                        return {
                        'status' : False,
                        'message' : f"New password not valid ! It should contain one letter between [A-Z]"
                        }
            elif not re.search("[a-z]",password):
                return {
                'status' : False,
                'message' : f"New password not valid ! It should contain one letter between [a-z]"
                }
            elif not re.search("[1-9]",password):
                return {
                'status' : False,
                'message' : f"New password not valid ! It should contain one letter between [1-9]"
                }
            elif not re.search("[~!@#$%^&*]",password):
                return {
                'status' : False,
                'message' : f"New password not valid ! It should contain at least one letter in [~!@#$%^&*]"
                }
            elif re.search("[\s]",password):
                return {
                'status' : False,
                'message' : f"New password not valid ! It should not contain any space"
                }
            elif (len(password)<10 or len(password)>50):
                return {
                'status' : False,
                'message' : f"New password not valid ! Total characters should be between 10 and 50"
                }
            try:
                activation_link = Activationlinks.objects.get(activationcode=activation_code,validated=False,isdeleted=False)
                activation_link.validated = True
                activation_link.save()
                user = activation_link.createdby
                user.set_password(password)
                user.save()
                return {
                'status' : True,
                }
            except Exception as e:
                logger.info(e)
                return {
                    'status' : False,
                    'message' : f"Wrong Activation Code"
                }
        data = validate(request)
        if data.get('status'):
            if request.session.get('login_message'):
                del request.session['login_message']
            request.session['login_message'] = 'Password set successfully'
            return redirect('/login')
        else:
            context = request.POST.dict()
            context['message'] = data.get('message')
            context['status'] = False
            return render(request,'accounts/openaccount/personal-signup/set-password.html',context)
        
@method_decorator(login_required, name='dispatch')
class PageStatus(View):
    def get(self,request):
        useraccount = Useraccounts.objects.get(customer__user=request.user, isdeleted=False)
        if request.GET.get('page') == '1':
            if useraccount.dateofbirth and useraccount.nationality:
                return redirect('/pageStatus/?page=2')
            if request.session.get('page_check_token'):
                del request.session['page_check_token']
            else:
                pass
            user_account = Useraccounts.objects.get(customer__user=request.user)
            year = datetime.datetime.today().year
            year_choices = list(range(year-16, year - 125, -1))
            months_choices = []
            for i in range(1,13):
                months_choices.append(datetime.date(2022, i, 1).strftime('%B'))
            day_choices = []
            for day in range(1,(monthrange(2022, 3)[1])+1):
                day_choices.append(day)
            if request.session.get('personal_details'):
                context = request.session.get('personal_details')
                context['countries'] = Countries.objects.all().order_by('name')
                context['year_choices'] = year_choices
                context['months_choices'] = months_choices
                context['day_choices'] = day_choices
                del request.session['personal_details']
            else:
                context = {'id': user_account.id, 'firstname': user_account.firstname,
                            'middlename': user_account.middlename,
                            'lastname': user_account.lastname, 'email': user_account.customer.user.email,'year_choices':year_choices,'months_choices':months_choices,'day_choices':day_choices}
                context['countries'] = Countries.objects.all().order_by('name')
            if request.session.get('initial'):
                del request.session['initial']
            request.session['initial'] = True
            if request.session.get('personalErrorMsg'):
                context['message'] = request.session.get('personalErrorMsg')
                context['status'] = False
                del request.session['personalErrorMsg'] 
            return render(request, 'accounts/openaccount/personal-signup/personal-details.html',context)
        elif request.GET.get('page') == '2':
            if Customerdocuments.objects.filter(customer__user=request.user,documenttype__description='ID verification proof').exists():
                return redirect('/pageStatus/?page=3')
            id_docs=Documenttypes.objects.filter(description='ID verification proof',isdeleted=False)
            year = datetime.datetime.today().year
            year_choices = list(range(year, year + 22, 1))
            months_choices = []
            for i in range(1,13):
                months_choices.append(datetime.date(2022, i, 1).strftime('%B'))
            context = {}
            if request.session.get('idDetails'):
                context = request.session.get('idDetails')
                del request.session['idDetails']
            if request.session.get('idErrorMsg'):
                context.update({
                    'status' : False,
                    'message' : request.session.get('idErrorMsg')
                })
                del request.session['idErrorMsg']
            context.update({
                'id_docs' : id_docs,
                'year_choices' : year_choices,
                'months_choices' : months_choices
            })

            return render(request, 'accounts/openaccount/personal-signup/personal-id-verify.html',context)
        elif request.GET.get('page') == '3':
            if Customerdocuments.objects.filter(customer__user=request.user,documenttype__description='Address verification proof').exists():
                return redirect('/')
            address_docs=Documenttypes.objects.filter(description='Address verification proof',isdeleted=False)
            context = {}
            if request.session.get('addressDetails'):
                context = request.session.get('addressDetails')
                del request.session['addressDetails']
            if request.session.get('addressErrorMsg'):
                context.update({
                    'status' : False,
                    'message' : request.session.get('addressErrorMsg')
                })
                del request.session['addressErrorMsg']
            context.update({
                'address_docs' : address_docs
            })

            return render(request, 'accounts/openaccount/personal-signup/personal-address-verify.html',context)
        elif request.GET.get('page') == '4':
            return redirect('/dashboard')
    def post(self,request):
        if request.session.get('initial'):
            if request.session.get('personal_details'):
                del request.session['personal_details']
            request.session['personal_details'] = request.POST.dict()
            def validate(request):
                validate_dict = {
                    'day' : request.POST.get('day'),
                    'month' : request.POST.get('month'),
                    'year' : request.POST.get('year'),
                    'street address' : request.POST.get('street_address'),
                    'city' : request.POST.get('city'),
                    'state / region' : request.POST.get('region'),
                    'zipcode' : request.POST.get('zipcode'),
                    'country code' : request.POST.get('countrycode'),
                    'phone number' : request.POST.get('phonenumber'),
                    'country of residence' : request.POST.get('country'),
                    'nationality' : request.POST.get('nationality'),
                }
                for k,v in validate_dict.items():
                    if v in ('',None,False):
                        return {
                            'status' : False,
                            'message' : f'{k} is missing' 
                        }
                    elif k == 'phone number' and not v.isdigit():
                        return {
                            'status' : False,
                            'message' : 'Invalid phone number format' 
                        }
                return {
                    'status' : True
                }
               
            data = validate(request)
            if data.get('status'):
                datetime_object = datetime.datetime.strptime(request.POST.get('month'), "%B")
                month_number = str(datetime_object.month)
                dateofbirth = f"{request.POST.get('day')}-{month_number}-{request.POST.get('year')}"
                dateofbirth_to_db = f"{request.POST.get('year')}-{month_number}-{request.POST.get('day')}"
                request.session['personal_details'].update({
                    'dateofbirth' : dateofbirth,
                    'dateofbirth_to_db' : dateofbirth_to_db
                })
                return redirect('/settings/personal/confirm/')
            else:
                if request.session.get('personalErrorMsg'):
                    del request.session['personalErrorMsg']
                request.session['personalErrorMsg']  = data.get('message')
                return redirect('/pageStatus/?page=1')
        else:
            return redirect('/pageStatus/?page=1')

@method_decorator(login_required, name='dispatch')
class ShowDocumentFields(View):
    def get(self,request):
        if request.GET.get('for_field'):
            documenttype = Documenttypes.objects.get(id=request.GET.get('id_proof'),isdeleted=False)
            doc_fileds = Documentfields.objects.filter(documenttype=documenttype,isdeleted=False).values()
            response = {
                'doc_fileds' : list(doc_fileds),
            }
            return JsonResponse(response)

class CurrencyAccounts(View):
    def post(self, request):
        val = request.POST.get('val')
        ids = request.POST.get('uniqueIds')
        context = {}
        context['currencies'] = Currencies.objects.filter(isdeleted=False)
        if val == '0':
            template = render_to_string('accounts/openaccount/personal-signup/new-acc.html',context)
        elif val == '1':
            context['count'] = 1
            template = render_to_string('accounts/openaccount/personal-signup/existing-acc.html',context)
        elif val == 'duplicate':
            ids = json.loads(ids)
            count = ids[-1]+1
            context['count'] = count
            template = render_to_string('accounts/openaccount/personal-signup/append-acc.html',context)
        response = {'curr_acc' : template}
        return JsonResponse(response)