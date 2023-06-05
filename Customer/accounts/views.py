import datetime
import json
import logging
import re
from calendar import monthrange
from secrets import token_urlsafe

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView

from accounts.forms import ExternalBeneficiaryForm, InternalBeneficiaryForm, DomesticBeneficiaryForm
from entrebiz import settings
from EntrebizAdmin.decorators import template_decorator
from Transactions.mixins import (OTP, ConfirmYourMail, acc_list,
                                 add_log_action, checkNonAsciiChracters,
                                 randomword)
from UserDetails.forms import UserDetailsForm
from utils.models import (Accounts, Activationlinks, Activitylog,
                          Businessdetails, Countries, Cryptobeneficiaries,
                          Currencies, Customerdocuments, Customers,
                          Documentfields, Documenttypes, Externalbeneficiaries,
                          Internalbeneficiaries, Otps, Useraccounts,DomesticBeneficiary)

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


class QRCode(View):
    def get(self, request):
        if request.user_agent.os.family == "Android":
            return redirect("https://play.google.com/store/apps/details?id=com.codesvera.entrebiz")
        elif request.user_agent.os.family == "iOS":
            return redirect("https://apps.apple.com/in/app/entrebiz/id6443900815")
        
        
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
            now = timezone.now()
            email = request.POST['email']
            password = request.POST['password']
            try:
                user = User.objects.get(email=email)
                if user.check_password(password):
                    try:
                        # request.session['showDelayModal'] = True
                        user_account = Useraccounts.objects.get(customer__user=user, isdeleted=False)
                        if user_account.account_locked_for and now < user_account.account_locked_for:
                            message = "Your account has been locked out for 12 hours due to multiple failed login attempts."
                        else:
                            user_account.logintrycount = 0
                            user_account.account_locked_for = None
                            user_account.save()
                            if user_account.twofactorauth:
                                token = token_urlsafe(30)
                                request.session['login_token'] = token
                                request.session['isTwoStepPassed'] = 0
                                request.session['user_email'] = user.email
                                full_name = f"{user_account.firstname} {user_account.lastname}"

                                return redirect('/twoStepVerification')
                            else:
                                login(request, user)
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
                                    Activitylog.objects.create(user=user, activity="login",
                                                        activitytime=datetime.datetime.now())
                                    try:
                                        customer_type = Customers.objects.get(user=request.user).customertype
                                        if customer_type == 1:
                                            if not useraccount.dateofbirth and not useraccount.nationality:
                                                return redirect('/pageStatus/?page=1')
                                            elif not Customerdocuments.objects.filter(customer__user=request.user,documenttype__description='ID verification proof').exists():
                                                return redirect('/pageStatus/?page=2')
                                            elif not Customerdocuments.objects.filter(customer__user=request.user,documenttype__description='Address verification proof').exists():
                                                return redirect('/pageStatus/?page=3')
                                        else:
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
                                    return redirect("/")  
                    except Useraccounts.DoesNotExist:
                        logger.info('Account Does not exist')
                        message = "Account Does not exist"
                    except Exception as e:
                        logger.info(e)
                        message = "Something went wrong! Please try again."
                else:
                    user_account = Useraccounts.active.get(customer__user=user)
                    if user_account.account_locked_for and now > user_account.account_locked_for:
                        user_account.account_locked_for = None
                        user_account.logintrycount = 0
                        user_account.save()
                    user_account.logintrycount +=0 if user_account.logintrycount > 5 else 1
                    user_account.save()
                    if user_account.logintrycount >= 5:
                        message = "Your account has been locked out for 12 hours due to multiple failed login attempts."
                        if not user_account.account_locked_for:
                            user_account.account_locked_for = datetime.datetime.now()+datetime.timedelta(hours=12)
                            user_account.save()
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
        context['currencies'] = Currencies.active.all()
        context['countries'] = Countries.active.all().order_by('name')
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
                if user_type == "personal":
                    if not first_name or first_name == "":
                        return {
                            'status': False,
                            'error': "First Name missing"
                        }
                    elif user_acc.customer.customertype == 2:
                        return {
                                'status': False,
                                'error': "First Name doesn't match"
                            } 
                    elif  user_acc.firstname != first_name:
                        return {
                            'status': False,
                            'error': "First Name doesn't match"
                        }
                    elif not user_acc.lastname:
                        return {
                            'status': False,
                            'error': "Account details doesn't match"
                        }
                    elif not last_name or last_name == "":
                        return {
                            'status': False,
                            'error': "Last Name missing"
                        }
                    elif user_acc.lastname != last_name:
                        return {
                            'status': False,
                            'error': "Last Name doesn't match"
                        }
                elif user_type == 'company':
                    if not first_name or first_name == "":
                        return {
                            'status': False,
                            'error': "Company Name missing"
                        }
                    try:
                        company_name = Businessdetails.objects.get(customer=user_acc.customer).companyname
                    except Exception as e:
                        logger.info(e)
                        return {
                                'status': False,
                                'error': "Company Name doesn't match"
                            }
                    if company_name != first_name:
                        return {
                                'status': False,
                                'error': "Company Name doesn't match"
                            }
                if not checkNonAsciiChracters(ben_nickname):
                    return {
                            'status': False,
                            'error': "Fancy characters not allowed"
                        }
                if Internalbeneficiaries.objects.filter(account=account_obj, createdby=request.user, isdeleted=False):
                    return {
                        'status': False,
                        'error': "Beneficiary exist"
                    }
                if Internalbeneficiaries.objects.filter(createdby=request.user,
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
                internalben_obj, created = Internalbeneficiaries.objects.get_or_create(receivername=ben_nickname, account=account_obj,
                                                            createdon=created_on, createdby=request.user,
                                                            modifiedon=modified_on, modifiedby=request.user,
                                                            customer=customer)
                if created:
                    add_log_action(request, internalben_obj, status=f'beneficiary account {internalben_obj.account.accountno} for account to account transfer created', status_id=1)
                context['status'] = True
                context['message'] = "Beneficiary Successfully Added!"
                request.session['beneficiary_update_message'] = "Beneficiary Successfully Added!"
                return redirect('/beneficiary/list/?type=transaction')
            else:
                context['status'] = False
                context['message'] = data.get("error")
                return render(request, 'accounts/beneficiary/add-beneficiary.html', context)
            
        elif ben_type == "domestictransfer":
            form = DomesticBeneficiaryForm(request.POST,request=request)
            context = json.loads(json.dumps(request.POST))
            context['currencies'] = Currencies.objects.filter(Q(code='USD') | Q(code='INR') | Q(code='SGD'), isdeleted=False)
            context['countries'] = Countries.active.filter(Q(name='United States') | Q(name='India') | Q(name='Singapore'))
            if form.is_valid():
                save_form = form.save(commit=False)
                save_form.country = Countries.objects.get(id=request.POST.get('domestic_country'))
                save_form.currency = Currencies.objects.get(id=request.POST.get('domestic_currency'))
                save_form.customer = Customers.objects.get(user=request.user)
                save_form.createdby = request.user
                save_form.save()
                users_type = request.POST.get("user_type")
                if users_type == "personal":
                    save_form.account_type = "Personal"
                else:
                    save_form.account_type = "Company"
                save_form.save()
                    
                add_log_action(request, DomesticBeneficiary.objects.get(id=save_form.id), status=f'beneficiary account {form.cleaned_data["domestic_accountnumber"]} for domestic tansfer created', status_id=1)
                context['message'] = "Beneficiary Successfully Added!"
                request.session['beneficiary_update_message'] = "Beneficiary Successfully Added!"
                return redirect('/beneficiary/list/?type=domestictransfer')
            else:
                context['form'] = form
            return render(request, 'accounts/beneficiary/add-beneficiary.html', context)

            
        elif ben_type == "walletwithdrawal":
            wallet_name = request.POST.get("walletname")

            def validation(request):
                beneficary_name = request.POST.get("ben_name")
                status = True
                try:
                    customer = request.user.customer_details.all()[0]
                except Exception as e:
                    logger.info(e)
                    return {
                        'status': False,
                        'error': "Customer details not found"
                    }
                if not beneficary_name:
                    return {
                        'status':False,
                        'error':"Wallet name field is required"
                    }
                if not wallet_name:
                    return {
                        'status':False,
                        'error':"Wallet Address field is required"
                    }
                if not checkNonAsciiChracters([wallet_name,beneficary_name]):
                    return {
                        'status': False,
                        'error': "Fancy characters not allowed"
                    }
                if Cryptobeneficiaries.objects.filter(wallet_name=wallet_name, createdby=request.user, isdeleted=False):
                    return {
                        'status': False,
                        'error': "Wallet Address already exist"
                    }
                if Cryptobeneficiaries.objects.filter(createdby=request.user,
                                                        name=beneficary_name, isdeleted=False):
                    return {
                        'status': False,
                        'error': "Wallet name already exist"
                    }

                return {
                    'status': status,
                    'customer': customer,
                    'beneficary_name':beneficary_name,
                }

            data = validation(request)
            context = json.loads(json.dumps(request.POST))
            if data.get("status"):
                created_on = datetime.datetime.now()
                modified_on = datetime.datetime.now()
                customer = data.get("customer")
                beneficary_name = data.get("beneficary_name")
                cryptoben_obj, created = Cryptobeneficiaries.objects.get_or_create(wallet_name=wallet_name,
                                                                                       name=beneficary_name,
                                                                                       createdon=created_on,
                                                                                       createdby=request.user, modifiedon=modified_on,customer=customer,
                                                                                   currency=Currencies.objects.get(code='USD'),
                                                                                   modifiedby=request.user)
                if created:
                    add_log_action(request, cryptoben_obj,
                                   status=f'Wallet withdrawal {cryptoben_obj.name} walletname has been created',
                                   status_id=1)
                context['status'] = True
                context['message'] = "Wallet Withdrawal Successfully Added!"
                request.session['beneficiary_update_message'] = "Wallet Withdrawal Successfully Added"
                return redirect('/beneficiary/list/?type=walletwithdrawal')
            else:
                context['status'] = False
                context['message'] = data.get("error")
                context['currencies'] = Currencies.active.all()
                return render(request, 'accounts/beneficiary/add-beneficiary.html', context)
        else:
            form = ExternalBeneficiaryForm(request.POST,request=request)
            context = json.loads(json.dumps(request.POST))
            context['currencies'] = Currencies.objects.all()
            context['countries'] = Countries.active.all().order_by('name')
            if form.is_valid():
                save_form = form.save(commit=False)
                save_form.country = Countries.objects.get(id=request.POST.get('country'))
                save_form.currency = Currencies.objects.get(id=request.POST.get('currency'))
                save_form.customer = Customers.objects.get(user=request.user)
                save_form.createdby =  request.user
                users_type = request.POST.get("user_type")
                if users_type == "personal":
                    save_form.account_type = "Personal"
                else:
                    save_form.account_type = "Company"
                save_form.save()
                    
                add_log_action(request, Externalbeneficiaries.objects.get(id=save_form.id), status=f'beneficiary account {form.cleaned_data["accountnumber"]} for international wire transfer created', status_id=1)
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
        elif list_type and list_type == "walletwithdrawal":
            context['list_type'] = "walletwithdrawal"
            context['crypto_benificiaries'] = Cryptobeneficiaries.objects.filter(createdby=request.user,
                                                                                     isdeleted=False)
        elif list_type and list_type == "domestictransfer":
            context['list_type'] = "domestictransfer"
            context['domestictransfer_benificiaries'] = DomesticBeneficiary.objects.filter(createdby=request.user,
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
        elif list_type and list_type == "walletwithdrawal":
            context['list_type'] = "walletwithdrawal"
            context['crypto_benificiaries'] = Cryptobeneficiaries.objects.filter(createdby=request.user,
                                                                                     isdeleted=False)
        elif list_type and list_type == "domestictransfer":
            context['list_type'] = "domestictransfer"
            context['domestictransfer_benificiaries'] = DomesticBeneficiary.objects.filter(createdby=request.user,
                                                                                     isdeleted=False)
        else:
            context['internal_benificiaries'] = Internalbeneficiaries.objects.filter(createdby=request.user,
                                                                                     isdeleted=False)
        context['list_type'] = list_type
        return render(request, 'accounts/beneficiary/list-beneficiary.html', context)


@method_decorator(login_required, name='dispatch')
class UpdateBeneficiaryView(View):
    def get(self, request):
        c_code = request.GET.get("c_code")
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
                try:
                    Cryptobeneficiaries.objects.get(slug=slug, isdeleted=False)
                    bentype = 'walletwithdrawal'
                except Exception as e:
                    logger.info(e)
                    try:
                        DomesticBeneficiary.objects.get(slug=slug, isdeleted=False)
                        bentype = 'domestictransfer'
                    except Exception as e:
                        logger.info(e)
                        return redirect('/beneficiary/list/')
        try:
            if bentype == 'transaction':
                ben_obj = Internalbeneficiaries.objects.get(slug=slug, isdeleted=False)
                context = {'id': ben_obj.id, 'name': ben_obj.receivername, 'accountnumber': ben_obj.account.accountno,
                           'firstname': ben_obj.account.user_account.firstname,
                           'lastname': ben_obj.account.user_account.lastname,'ben_obj':ben_obj
                           }
            elif bentype == 'walletwithdrawal':
                ben_obj = Cryptobeneficiaries.objects.get(slug=slug, isdeleted=False)
                context = {'id': ben_obj.id, 'name': ben_obj.name, 'walletname': ben_obj.wallet_name,'currency':ben_obj.currency,
                           'ben_obj': ben_obj
                           }
            elif bentype == 'domestictransfer':
                ben_obj = DomesticBeneficiary.objects.get(slug=slug, isdeleted=False)
                context = {
                    'id': ben_obj.id,
                    'c_code':c_code,
                    'domestic_name': ben_obj.domestic_name,
                    'domestic_accountnumber': ben_obj.domestic_accountnumber,
                    'domestic_bankname': ben_obj.domestic_bankname,
                    'routing_number': ben_obj.routing_number,
                    'domestic_city': ben_obj.domestic_city,
                    'domestic_country': ben_obj.country.id if ben_obj.country else None,
                    'domestic_currency': ben_obj.currency.id if ben_obj.currency else None,
                    'domestic_email': ben_obj.domestic_email,
                    'currencies': Currencies.objects.filter(Q(code='USD') | Q(code='INR') | Q(code='SGD'), isdeleted=False),
                    'countries': Countries.active.filter(Q(name='United States') | Q(name='India') | Q(name='Singapore')),
                    'ben_obj': ben_obj
                }
            else:
                ben_obj = Externalbeneficiaries.objects.get(slug=slug, isdeleted=False)
                context = {'id': ben_obj.id, 'name': ben_obj.name, 'accountnumber': ben_obj.accountnumber,
                           'bankname': ben_obj.bankname, 'swiftcode': ben_obj.swiftcode, 'city': ben_obj.city,
                           'country': ben_obj.country.id if ben_obj.country else None, 'currency': ben_obj.currency.id if ben_obj.currency else None, 'email': ben_obj.email,
                           'currencies': Currencies.objects.all(), 'countries': Countries.active.all().order_by('name'), 'ben_obj': ben_obj}
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
                    add_log_action(request, intobj, status=f"beneficiary account(account to account transfer) {intobj.account.accountno} deleted", status_id=3)
                except Exception as e:
                    logger.info(e)
                    status = False
            elif bentype == 'walletwithdrawal':
                try:
                    crpobj = Cryptobeneficiaries.objects.get(slug=slug, isdeleted=False)
                    crpobj.isdeleted = True
                    crpobj.save()
                    add_log_action(request, crpobj, status=f"beneficiary account(Walletwithdrawal transfer) {crpobj.name} deleted", status_id=3)
                except Exception as e:
                    logger.info(e)
                    status = False
            
            elif bentype == 'domestictransfer':
                try:
                    extobj = DomesticBeneficiary.objects.get(slug=slug, isdeleted=False)
                    extobj.isdeleted = True
                    extobj.save()
                    add_log_action(request, extobj, status=f"beneficiary account(domestic transfer) {extobj.domestic_accountnumber} deleted", status_id=3)
                except Exception as e:
                    logger.info(e)
                    status = False
                    
            elif bentype == 'international':
                try:
                    extobj = Externalbeneficiaries.objects.get(slug=slug, isdeleted=False)
                    extobj.isdeleted = True
                    extobj.save()
                    add_log_action(request, extobj, status=f"beneficiary account(international wire transfer) {extobj.accountnumber} deleted", status_id=3)
                except Exception as e:
                    logger.info(e)
                    status = False
            return HttpResponse(json.dumps({'status': status}), content_type='application/json')
        else:
            ben_id = request.POST.get("id")
            accountnumber = request.POST.get("accountnumber")
            name = request.POST.get("name")
            walletname=request.POST.get("walletname")
            context = json.loads(json.dumps(request.POST))
            context['currencies'] = Currencies.objects.all()
            context['countries'] = Countries.active.all().order_by('name')
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
                    elif not checkNonAsciiChracters(name):
                        context['status'] = False
                        context['firstname'] = ben_obj.account.user_account.firstname
                        context['lastname'] = ben_obj.account.user_account.lastname
                        context['message'] = f"Fancy characters are not allowed ({name})"


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
                    add_log_action(request, ben_obj, status=f"beneficiary account(account to account transfer) {account_obj.accountno} edited", status_id=2)
                    context['message'] = "Beneficiary Successfully Updated!"
                    request.session['beneficiary_update_message'] = "Beneficiary Successfully Updated!"
                    return redirect('/beneficiary/list/?type=transaction')

            elif beneficiary_type == 'walletwithdrawal':
                context['status'] = True
                ben_obj = Cryptobeneficiaries.objects.get(id=ben_id, isdeleted=False)
                if Cryptobeneficiaries.objects.filter(~Q(id=ben_id), createdby=request.user,name=name,wallet_name=walletname, isdeleted=False):
                    context['status'] = False
                    context['name'] = ben_obj.name
                    context['walletname'] = ben_obj.wallet_name
                    context['message'] = "Nick name already exist!"
                elif not checkNonAsciiChracters([name,walletname]):
                    context['status'] = False
                    context['name'] = ben_obj.name
                    context['walletname'] = ben_obj.wallet_name
                    context['message'] = f"Fancy characters are not allowed"

                if context['status'] == True:
                    ben_obj.name = name
                    ben_obj.wallet_name = walletname
                    ben_obj.save()
                    add_log_action(request, ben_obj, status=f"Wallet withdrawal(wallet withdrawal transfer) {ben_obj.name} has been edited", status_id=2)
                    context['message'] = "Beneficiary Successfully Updated!"
                    request.session['beneficiary_update_message'] = "Beneficiary Successfully Updated!"
                    return redirect('/beneficiary/list/?type=walletwithdrawal')
                
            elif beneficiary_type == 'domestictransfer':
                    ben_obj = DomesticBeneficiary.objects.get(id=ben_id, isdeleted=False)
                    form = DomesticBeneficiaryForm(request.POST, instance=ben_obj,request=request)
                    if form.is_valid():
                        save_form = form.save(commit=False)
                        save_form.country = Countries.objects.get(id=request.POST.get('domestic_country'))
                        save_form.currency = Currencies.objects.get(id=request.POST.get('domestic_currency'))
                        save_form.customer = Customers.objects.get(user=request.user)
                        save_form.createdby = request.user
                        save_form.save()
                        add_log_action(request, ben_obj, status=f"beneficiary account(domestictransfer transfer) {ben_obj.domestic_accountnumber} edited", status_id=4)
                        context['message'] = "Beneficiary Successfully Updated!"
                        request.session['beneficiary_update_message'] = "Beneficiary Successfully Updated!"
                      
                        return redirect('/beneficiary/list/?type=domestictransfer')
                        
                    else:
                        
                        context['status'] = False
                        context['form'] = form
                        
            else:
                ben_obj = Externalbeneficiaries.objects.get(id=ben_id, isdeleted=False)
                form = ExternalBeneficiaryForm(request.POST, instance=ben_obj,request=request)
                if form.is_valid():
                    save_form = form.save(commit=False)
                    save_form.country = Countries.objects.get(id=request.POST.get('country'))
                    save_form.currency = Currencies.objects.get(id=request.POST.get('currency'))
                    save_form.customer = Customers.objects.get(user=request.user)
                    save_form.createdby = request.user
                    save_form.save()
                    add_log_action(request, ben_obj, status=f"beneficiary account(international wire transfer) {ben_obj.accountnumber} edited", status_id=2)
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
        if request.session.get('showDelayModal'):
            context['show_modal'] = request.session.get('showDelayModal')
            del request.session['showDelayModal']
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
                add_log_action(request, acc_obj, status=f'account {acc_obj.accountno} created', status_id=1)
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
    logout(request)
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
            add_log_action(request, account_obj, status=f'account {account_obj.accountno} deleted', status_id=3)
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
                OTP()
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

class PersonalSignUp(View):
    def get(self,request):
        context = {}
        if request.session.get('personalInfo'):
            context = request.session.get('personalInfo')
            del request.session['personalInfo']
        context['currencies'] = Currencies.objects.filter(isdeleted=False)
        return render(request,'accounts/openaccount/personal-signup/personal-signup.html',context)
    def post(self,request):
        def valiadte(request):
            firstName = request.POST.get('firstName').strip()
            lastName = request.POST.get('lastName').strip()
            email = request.POST.get('email').strip()
            primaryCurrency = request.POST.get('primaryCurrency')
            secondaryCurrency = request.POST.get('secondaryCurrency')
            termsConditions = request.POST.get('termsConditions')
            email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
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

class PersonalSignUpConfirm(View,ConfirmYourMail):
    def get(self,request):
        if request.session.get('personalInfo'):
            first_currency = Currencies.objects.get(code = request.session['personalInfo'].get('primaryCurrency'))
            second_currency = Currencies.objects.get(code = request.session['personalInfo'].get('secondaryCurrency'))
            context = request.session.get('personalInfo')
            context['first_currency'] = first_currency
            context['second_currency'] = second_currency
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
            try:
                if request.session.get('referFriend'):
                    refferer_account = Useraccounts.active.get(id=request.session['referFriend'].get('refferer_id'))
                    useraccount.referred_by = refferer_account
                    useraccount.show_referee = True
                    useraccount.save()
                    refferer_account.referencecount += 1
                    refferer_account.save()
                    del request.session['referFriend']
            except Exception as e:
                logger.info(e)
            for currency in [primary_currency,secondary_currency]:
                accountno_list = list(map(int, list(Accounts.objects.filter(user_account__ismaster_account=False).order_by('-accountno').values_list('accountno', flat=True))))
                accountno_list.sort(reverse = True)
                account,status = Accounts.objects.get_or_create(user_account=useraccount,accountno = int(accountno_list[0]) + 1 if accountno_list else settings.DEFAULT_ADD,
                            currency=Currencies.objects.get(code=currency),accounttype=1,isprimary=1 if currency==primary_currency else 2,createdby=user)
            try:
                primary_account = f"{useraccount.accnt_usr_accnt.all()[0].accountno} {useraccount.accnt_usr_accnt.all()[0].currency.code}"
                secondary_account = f"{useraccount.accnt_usr_accnt.all()[1].accountno} {useraccount.accnt_usr_accnt.all()[1].currency.code}"
            except Exception as e:
                primary_account = ""
                secondary_account = ""
                logger.info(f"Error in fetching account details->{e}")
            add_log_action(request, useraccount, status=f'Personal account({user_email}) has been created with accounts {primary_account} and {secondary_account}', status_id=1,user_id=user.id)
            del request.session['personalInfo']
            mail_status = self.send_confirm_mail(full_name, user_email,createdby=user,transaction_type=1, dev_type=1)
            return render(request,'accounts/openaccount/personal-signup/signup-success.html')
        else:
            return redirect('/register/personal')

class SetPassword(View):
    def get(self,request):
        try:
            activation_link = Activationlinks.objects.get(activationcode=request.GET.get('activationLink'),
                                validated=False,isdeleted=False)
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
                return redirect('/')
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
                context['countries'] = Countries.active.all().order_by('name')
                context['year_choices'] = year_choices
                context['months_choices'] = months_choices
                context['day_choices'] = day_choices
                del request.session['personal_details']
            else:
                context = {'id': user_account.id, 'firstname': user_account.firstname,
                            'middlename': user_account.middlename,
                            'lastname': user_account.lastname, 'email': user_account.customer.user.email,'year_choices':year_choices,'months_choices':months_choices,'day_choices':day_choices}
                context['countries'] = Countries.active.all().order_by('name')
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
                if not checkNonAsciiChracters([request.POST.get('street_address'),request.POST.get('city'),request.POST.get('region')]):
                    return {
                            'status': False,
                            'message': "Fancy characters are not allowed"
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
