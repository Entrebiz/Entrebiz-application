from decimal import Decimal
import os
import math
import re
import datetime
import json
import csv
from urllib.request import urlopen
import logging

from django.views import View
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.http import FileResponse
from django.db.models import Q
from Transactions.views import create_directory
from django.core.paginator import Paginator

logger = logging.getLogger('lessons')

from entrebiz import settings
from utils.mixins import UtilMixins
from utils.models import Accounts, Bankdetail, Businessdetails, Countries, Currencies, Customerdocumentfiles, \
    Customerdocuments, Customers, AdminAccount, DomesticTransaction, DomesticTransactionRefundRequests, Industrytypes, Referrerdetails, Transactions, Useraccounts, Comments, \
    Internationaltransactions, RefundRequests, Transactiontypes, Receivemoney, Incomingtracepayment, \
    Inwardremittancetransactions, Currencyconversionratescombined, InvoiceDocument, WalletWithdrawalRefundRequests, WalletWithdrawalTransactions,\
        Currencyconversionmargins
from EntrebizAdmin.decorators import admin_subadmin_only, allowed_users, admin_only
from Transactions.mixins import AccountActivationMail, ConfirmYourMail, CustomMail, ModelQueries, TransactionMail, add_log_action, randomword
from django.db.models import Q, F

# Create your views here.
class AdminLogin(View):
    def get(self, request):
        try:
            user = request.user.adminacc_created_by
        except Exception as e:
            logger.info(f"{e}")
            user = False
        if request.user.is_authenticated and user:
            return redirect('/dashboard')
        return render(request, 'accounts/login/admin-login.html')

    def post(self, request):
        email = request.POST.get('Email')
        password = request.POST.get('Password')

        def validate():
            if not email:
                return {
                    'status': False,
                    'message': 'Email required'
                }
            elif not password:
                return {
                    'status': False,
                    'message': 'Password required'
                }
            email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            if email and not re.search(email_regex, email):
                return {
                    'status': False,
                    'message': 'Invalid Email format'
                }
            elif not AdminAccount.objects.filter(email=email, isdeleted=False).exists():
                return {
                    'status': False,
                    'message': 'Account Does not exist'
                }
            elif AdminAccount.objects.filter(email=email, status=False, isdeleted=False).exists():
                return {
                    'status': False,
                    'message': 'You are not allowed to login'
                }
            user = AdminAccount.objects.get(email=email, isdeleted=False).createdby
            if user.check_password(password):
                auth_login(request, user)
                return {
                    'status': True
                }
            else:
                return {
                    'status': False,
                    'message': 'Incorrect email or password'
                }

        data = validate()
        if data.get('status'):
            return redirect('/dashboard')
        else:
            context = request.POST.dict()
            context['status'] = data.get('status')
            context['message'] = data.get('message')
        return render(request, 'accounts/login/admin-login.html', context)


@method_decorator(login_required, name='dispatch')
@method_decorator(admin_subadmin_only, name='dispatch')
class AdminDashboardView(View):
    def get(self, request):
        user = AdminAccount.objects.get(createdby=request.user, isdeleted=False)
        if user.admin_level == 'Super Admin':
            total_admins = AdminAccount.objects.filter(isdeleted=False).count()
        else:
            total_admins = None
        total_customers = Useraccounts.active.all().count()
        total_pvt_accounts = Useraccounts.active.filter(customer__customertype=1).count()
        total_bsnss_accounts = Useraccounts.active.filter(customer__customertype=2).count()
        context = {
            'total_customers': total_customers,
            'total_admins': total_admins,
            'total_pvt_accounts': total_pvt_accounts,
            'total_bsnss_accounts': total_bsnss_accounts,
        }
        return render(request, 'common/admin-dashboard.html', context)


@method_decorator(login_required, name='dispatch')
@method_decorator(admin_subadmin_only, name='dispatch')
class Volume(View):
    def get(self, request):
        return render(request, 'volume/volume.html')


@method_decorator(login_required, name='dispatch')
@method_decorator(admin_only, name='dispatch')
@method_decorator(allowed_users(admin_type=['Super Admin']), name='dispatch')
class AdminUserManagement(View):
    def get(self, request):
        admins = AdminAccount.objects.filter(isdeleted=False).order_by('id')
        context = {'admins': admins}
        if request.session.get('adminEditSuccMsg'):
            context['status'] = True
            context['message'] = request.session.get('adminEditSuccMsg')
            del request.session['adminEditSuccMsg']
        if request.session.get('adminDltSuccMsg'):
            context['status'] = True
            context['message'] = request.session.get('adminDltSuccMsg')
            del request.session['adminDltSuccMsg']
        if request.session.get('adminAddSuccMsg'):
            context['status'] = True
            context['message'] = request.session.get('adminAddSuccMsg')
            del request.session['adminAddSuccMsg']
        return render(request, 'adminuser-management/adminuser-management.html', context)

    def post(self, request):
        if request.POST.get('action_type') == 'delete_adminuser':
            slug = request.POST.get('slug')
            try:
                Admin_user = AdminAccount.objects.get(slug=slug, isdeleted=False)
                Admin_user.isdeleted = True
                Admin_user.save()
                add_log_action(request, Admin_user, status=f'admin user "{Admin_user.firstname}" has been deleted', status_id=3)
                if request.session.get('adminDltSuccMsg'):
                    del request.session['adminDltSuccMsg']
                request.session['adminDltSuccMsg'] = 'User deleted successfully'
            except Exception as e:
                logger.info(f"{e}")
                return redirect('/adminUserManagement')
        return redirect('/adminUserManagement')


@method_decorator(login_required, name='dispatch')
@method_decorator(admin_only, name='dispatch')
@method_decorator(allowed_users(admin_type=['Super Admin']), name='dispatch')
class AddAdminUser(View):
    def get(self, request):
        return render(request, 'adminuser-management/add-adminuser.html')

    def post(self, request):
        first_name = request.POST.get('FirstName')
        email = request.POST.get('Email')
        password1 = request.POST.get('Password')
        password2 = request.POST.get('ConfirmPassword')
        approval_level = request.POST.get('ApprovalLevel')

        def validate():
            if not first_name:
                return {
                    'status': False,
                    'message': 'Name is required.'
                }
            elif not email:
                return {
                    'status': False,
                    'message': 'Email is required.'
                }
            email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            if email and not re.search(email_regex, email):
                return {
                    'status': False,
                    'message': 'Invalid Email format'
                }
            elif not password1:
                return {
                    'status': False,
                    'message': 'Password is required.'
                }
            elif not password2:
                return {
                    'status': False,
                    'message': 'Confirm Password is required.'
                }
            elif not approval_level:
                return {
                    'status': False,
                    'message': 'Admin Type is required.'
                }
            elif password1 != password2:
                return {
                    'status': False,
                    'message': "Password does not match"
                }
            elif not re.search("[A-Z]", password1):
                return {
                    'status': False,
                    'message': f"Password not valid ! It should contain one letter between [A-Z]"
                }
            elif not re.search("[a-z]", password1):
                return {
                    'status': False,
                    'message': f"Password not valid ! It should contain one letter between [a-z]"
                }
            elif not re.search("[1-9]", password1):
                return {
                    'status': False,
                    'message': f"Password not valid ! It should contain one letter between [1-9]"
                }
            elif not re.search("[~!@#$%^&*]", password1):
                return {
                    'status': False,
                    'message': f"Password not valid ! It should contain at least one letter in [~!@#$%^&*]"
                }
            elif re.search("[\s]", password1):
                return {
                    'status': False,
                    'message': f"Password not valid ! It should not contain any space"
                }
            elif AdminAccount.objects.filter(email=email, isdeleted=False).exists():
                return {
                    'status': False,
                    'message': f"Account with same email exist"
                }
            usr_name = randomword(13)
            while True:
                if User.objects.filter(username=usr_name).exists():
                    usr_name = randomword(13)
                else:
                    break
            try:
                user = User.objects.create_user(username=usr_name, email=email, password=password1)
                admin_user = AdminAccount.objects.create(firstname=first_name, email=email, createdby=user,
                                                         approval_level=approval_level, admin_level='Admin')
                add_log_action(request, admin_user, status=f'admin user "{admin_user.firstname}" has been created', status_id=1)
            except Exception as e:
                logger.info(f"{e}")
                return {
                    'status': False,
                    'message': "Error Occured"
                }
            return {
                'status': True,
                'message': 'User created successfully'
            }

        data = validate()
        if data.get('status'):
            if request.session.get('adminAddSuccMsg'):
                del request.session['adminAddSuccMsg']
            request.session['adminAddSuccMsg'] = data.get('message')
            return redirect('/adminUserManagement')
        else:
            context = request.POST.dict()
            context['message'] = data.get('message')
            context['status'] = data.get('status')
            return render(request, 'adminuser-management/add-adminuser.html', context)


@method_decorator(login_required, name='dispatch')
@method_decorator(admin_only, name='dispatch')
@method_decorator(allowed_users(admin_type=['Super Admin']), name='dispatch')
class EditAdminUser(View):
    def get(self, request):
        try:
            slug = request.GET.get('slug')
            admin_user = AdminAccount.objects.get(slug=slug, isdeleted=False)
            ApprovalLevel = admin_user.approval_level
            context = {'admin_user': admin_user, 'ApprovalLevel': ApprovalLevel}
            return render(request, 'adminuser-management/edit-adminuser.html', context)
        except Exception as e:
            logger.info(f"{e}")
            return redirect('/adminUserManagement')

    def post(self, request):
        slug = request.POST.get('slug')
        first_name = request.POST.get('FirstName')
        email = request.POST.get('Email')
        approval_level = request.POST.get('ApprovalLevel')

        def validate():
            if not first_name:
                return {
                    'status': False,
                    'message': 'Name is required.'
                }
            if not email:
                return {
                    'status': False,
                    'message': 'Email is required.'
                }
            email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            if email and not re.search(email_regex, email):
                return {
                    'status': False,
                    'message': 'Invalid Email'
                }
            if email:
                try:
                    users_email = AdminAccount.objects.filter(isdeleted=False).values_list('email')
                    current_ed_user_email = AdminAccount.objects.get(slug=slug).email
                    count = 0
                    if current_ed_user_email == email:
                        count = 1
                    for mail in users_email:
                        if email == mail[0]:
                            count += 1
                    if count != 0 and count != 2:
                        return {
                            'status': False,
                            'message': 'Email already exist'
                        }
                except Exception as e:
                    logger.info(f"{e}")
                    pass
            if not approval_level:
                return {
                    'status': False,
                    'message': 'Admin Type is required.'
                }
            if request.POST.get('Activestatus') == 'on':
                active_status = True
            else:
                active_status = False
            try:
                admin_user = AdminAccount.objects.get(slug=slug, isdeleted=False)
                admin_user.firstname = first_name
                prev_mail_id = admin_user.email
                admin_user.email = email
                admin_user.approval_level = approval_level
                admin_user.status = active_status
                admin_user.save()
                user = admin_user.createdby
                user.email = email
                user.save()
                add_log_action(request, admin_user, status=f'admin user "{admin_user.firstname}" has been edited', status_id=2)
                return {
                    'status': True,
                    'message': 'User updated successfully'
                }
            except Exception as e:
                logger.info(f"{e}")
                return {
                    'status': False,
                    'message': 'Error Occured'
                }

        data = validate()
        if data.get('status'):
            if request.session.get('adminEditSuccMsg'):
                del request.session['adminEditSuccMsg']
            request.session['adminEditSuccMsg'] = data.get('message')
            return redirect('/adminUserManagement')
        else:
            context = request.POST.dict()
            context['message'] = data.get('message')
            context['status'] = False
            return render(request, 'adminuser-management/edit-adminuser.html', context)


@method_decorator(login_required, name='dispatch')
@method_decorator(admin_only, name='dispatch')
@method_decorator(allowed_users(admin_type=['Super Admin']), name='dispatch')
class FilterAdmin(View):
    def get(self, request):
        admin_name = request.GET.get('adminName').strip()
        admin_status = request.GET.get('adminStatus').strip()
        admins = AdminAccount.objects.filter(isdeleted=False)
        if admin_name:
            admins = admins.filter(firstname__icontains=admin_name,isdeleted=False)
        if admin_status == '1':
            admins = admins.filter(status=True,isdeleted=False)
        if admin_status == '0':
            admins = admins.filter(status=False,isdeleted=False)
        context = { 'admins' : admins.order_by('id')}
        template = render_to_string('adminuser-management/filter-admin.html',context)
        response = {'admin_details' : template,}

        return JsonResponse(response)


@method_decorator(login_required, name='dispatch')
@method_decorator(admin_only, name='dispatch')
class BankManagement(View):
    def get(self, request):
        bank_details = Bankdetail.objects.filter(isdeleted=False).order_by('id')
        countries = Countries.objects.all().order_by('name')
        currencies = Currencies.objects.filter(isdeleted=False).order_by('code')
        context = {
            'bank_details': bank_details,
            'countries': countries,
            'currencies': currencies,
        }
        if request.session.get('bankAddSuccMsg'):
            context['status'] = True
            context['message'] = request.session.get('bankAddSuccMsg')
            del request.session['bankAddSuccMsg']
        if request.session.get('bankEditSuccMsg'):
            context['status'] = True
            context['message'] = request.session.get('bankEditSuccMsg')
            del request.session['bankEditSuccMsg']
        if request.session.get('bankDltSuccMsg'):
            context['status'] = True
            context['message'] = request.session.get('bankDltSuccMsg')
            del request.session['bankDltSuccMsg']
        return render(request, 'bank-management/bank-management.html', context)

    def post(self, request):
        if request.POST.get('action_type') == 'delete_bank':
            slug = request.POST.get('slug')
            try:
                bank_details = Bankdetail.objects.get(slug=slug, isdeleted=False)
                bank_details.isdeleted = True
                bank_details.save()
                add_log_action(request, bank_details, status=f'bank "{bank_details.bankname}" has been deleted', status_id=3)
                if request.session.get('bankDltSuccMsg'):
                    del request.session['bankDltSuccMsg']
                request.session['bankDltSuccMsg'] = 'Bank deleted successfully'
                return redirect('/bankManagement')
            except Exception as e:
                logger.info(f"{e}")
                return redirect('/bankManagement')


@method_decorator(login_required, name='dispatch')
@method_decorator(admin_only, name='dispatch')
class ViewBank(View):
    def get(self, request):
        try:
            slug = request.GET.get('slug')
            bank_details = Bankdetail.objects.get(slug=slug, isdeleted=False)
            return render(request, 'bank-management/view-bank.html', context={'bank_details': bank_details})
        except Exception as e:
            logger.info(f"{e}")
            return redirect('/bankManagement')


@method_decorator(login_required, name='dispatch')
@method_decorator(admin_only, name='dispatch')
class FilterBank(View):
    def get(self, request):
        currency_id = request.GET.get('currency_id').strip()
        country_id = request.GET.get('country_id').strip()
        bank_details = Bankdetail.objects.filter(isdeleted=False)
        if currency_id:
            bank_details = Bankdetail.objects.filter(currency__id=currency_id, isdeleted=False)
        if country_id:
            bank_details = bank_details.filter(country__id=country_id, isdeleted=False)
        context = {'bank_details': bank_details.order_by('id')}
        template = render_to_string('bank-management/filter-list.html', context)
        response = {'bank_details': template, }
        return JsonResponse(response)


@method_decorator(login_required, name='dispatch')
@method_decorator(admin_only, name='dispatch')
class AddBank(View):
    def get(self, request):
        countries = Countries.objects.all().order_by('name')
        currencies = Currencies.objects.filter(isdeleted=False).order_by('code')
        context = {
            'countries': countries,
            'currencies': currencies,
        }
        return render(request, 'bank-management/add-bank.html', context)

    def post(self, request):
        beneficiary_name = request.POST.get('BeneficiaryName')
        beneficiary_address = request.POST.get('BeneficiaryAddress')
        bank_name = request.POST.get('BankName')
        ac_number = request.POST.get('AcNumber')
        address = request.POST.get('Address')
        currency_id = request.POST.get('CurrencyId')
        swiftcode = request.POST.get('SwiftCode')
        city = request.POST.get('City')
        country_id = request.POST.get('Country')
        reference = request.POST.get('Reference')

        def validate():
            if not beneficiary_name:
                return {
                    'status': False,
                    'message': 'Beneficiary Name is required.'
                }
            elif not bank_name:
                return {
                    'status': False,
                    'message': 'Bank Name is required.'
                }
            elif not ac_number:
                return {
                    'status': False,
                    'message': 'Account Number is required.'
                }
            elif not address:
                return {
                    'status': False,
                    'message': 'Address of Bank is required.'
                }
            elif not currency_id:
                return {
                    'status': False,
                    'message': 'Select Currency is required.'
                }
            elif not swiftcode:
                return {
                    'status': False,
                    'message': 'BIC/SWIFT Code is required.'
                }
            elif not city:
                return {
                    'status': False,
                    'message': 'City is required.'
                }
            elif not country_id:
                return {
                    'status': False,
                    'message': 'Select Country is required.'
                }
            try:
                bank_details, created = Bankdetail.objects.get_or_create(
                    currency=Currencies.objects.get(id=currency_id, isdeleted=False),
                    bankname=bank_name,
                    acnumber=ac_number,
                    address=address,
                    reference=reference,
                    swiftcode=swiftcode,
                    beneficiaryname=beneficiary_name,
                    beneficiaryaddress=beneficiary_address,
                    city=city,
                    country=Countries.objects.get(id=country_id),
                )
                if created:
                    add_log_action(request, bank_details, status=f'bank "{bank_details.bankname}" has been added', status_id=1)
                return {
                    'status': True,
                    'message': 'Bank added successfully'
                }
            except Exception as e:
                logger.info(f"{e}")
                return {
                    'status': False,
                    'message': 'Error Occured'
                }

        data = validate()
        if data.get('status'):
            if request.session.get('bankAddSuccMsg'):
                del request.session['bankAddSuccMsg']
            request.session['bankAddSuccMsg'] = data.get('message')
            return redirect('/bankManagement')
        else:
            context = request.POST.dict()
            context['message'] = data.get('message')
            context['status'] = data.get('status')
            countries = Countries.objects.all().order_by('name')
            currencies = Currencies.objects.filter(isdeleted=False).order_by('code')
            context['countries'] = countries
            context['currencies'] = currencies
            return render(request, 'bank-management/edit-bank.html', context)


@method_decorator(login_required, name='dispatch')
@method_decorator(admin_only, name='dispatch')
class EditBank(View):
    def get(self, request):
        try:
            slug = request.GET.get('slug')
            countries = Countries.objects.all()
            currencies = Currencies.objects.filter(isdeleted=False)
            context = {
                'countries': countries,
                'currencies': currencies
            }
            bank_details = Bankdetail.objects.get(slug=slug, isdeleted=False)
            context['slug'] = bank_details.slug
            context['BeneficiaryName'] = bank_details.beneficiaryname
            context['BeneficiaryAddress'] = bank_details.beneficiaryaddress
            context['BankName'] = bank_details.bankname
            context['AcNumber'] = bank_details.acnumber
            context['Address'] = bank_details.address
            context['CurrencyId'] = bank_details.currency.id
            context['SwiftCode'] = bank_details.swiftcode
            context['City'] = bank_details.city
            context['Country'] = bank_details.country.id
            context['Reference'] = bank_details.reference
            return render(request, 'bank-management/edit-bank.html', context)
        except Exception as e:
            logger.info(f"{e}")
            return redirect('/bankManagement')

    def post(self, request):
        slug = request.POST.get('slug')
        beneficiary_name = request.POST.get('BeneficiaryName')
        beneficiary_address = request.POST.get('BeneficiaryAddress')
        bank_name = request.POST.get('BankName')
        ac_number = request.POST.get('AcNumber')
        address = request.POST.get('Address')
        currency_id = request.POST.get('CurrencyId')
        swiftcode = request.POST.get('SwiftCode')
        city = request.POST.get('City')
        country_id = request.POST.get('Country')
        reference = request.POST.get('Reference')

        def validate():
            if not beneficiary_name:
                return {
                    'status': False,
                    'message': 'Beneficiary Name is required.'
                }
            elif not bank_name:
                return {
                    'status': False,
                    'message': 'Bank Name is required.'
                }
            elif not ac_number:
                return {
                    'status': False,
                    'message': 'Account Number is required.'
                }
            elif not address:
                return {
                    'status': False,
                    'message': 'Address of Bank is required.'
                }
            elif not currency_id:
                return {
                    'status': False,
                    'message': 'Select Currency is required.'
                }
            elif not swiftcode:
                return {
                    'status': False,
                    'message': 'BIC/SWIFT Code is required.'
                }
            elif not city:
                return {
                    'status': False,
                    'message': 'City is required.'
                }
            elif not country_id:
                return {
                    'status': False,
                    'message': 'Select Country is required.'
                }
            try:
                bank_details = Bankdetail.objects.get(slug=slug, isdeleted=False)
                bank_details.currency = Currencies.objects.get(id=currency_id, isdeleted=False)
                bank_details.bankname = bank_name
                bank_details.acnumber = ac_number
                bank_details.address = address
                bank_details.reference = reference
                bank_details.swiftcode = swiftcode
                bank_details.beneficiaryname = beneficiary_name
                bank_details.beneficiaryaddress = beneficiary_address
                bank_details.city = city
                bank_details.country = Countries.objects.get(id=country_id)
                bank_details.save()
                add_log_action(request, bank_details, status=f'bank "{bank_details.bankname}" has been edited', status_id=2)
                return {
                    'status': True,
                    'message': 'Bank details updated successfully'
                }
            except Exception as e:
                logger.info(f"{e}")
                return {
                    'status': False,
                    'message': 'Error Occured'
                }

        data = validate()
        if data.get('status'):
            if request.session.get('bankEditSuccMsg'):
                del request.session['bankEditSuccMsg']
            request.session['bankEditSuccMsg'] = data.get('message')
            return redirect('/bankManagement')
        else:
            context = request.POST.dict()
            context['message'] = data.get('message')
            context['status'] = data.get('status')
            return render(request, 'bank-management/edit-bank.html', context)


@method_decorator(login_required, name='dispatch')
@method_decorator(admin_subadmin_only, name='dispatch')
class CustomerManagement(View, ModelQueries):
    def get(self, request):
        user_accounts = Useraccounts.objects.filter(isdeleted=False).order_by('-id')
        context = {}
        if request.session.get('CustomMailStatusMsg'):
            context['message'] = request.session.get('CustomMailStatusMsg')
            context['status'] = True
            del request.session['CustomMailStatusMsg']
        if request.session.get('lockStatusMsg'):
            context['message'] = request.session.get('lockStatusMsg')
            context['status'] = True
            del request.session['lockStatusMsg']
        if request.session.get('lockStatusErrMsg'):
            context['message'] = request.session.get('lockStatusErrMsg')
            context['status'] = False
            del request.session['lockStatusErrMsg']
        if request.session.get('deleteUserErrMsg'):
            context['message'] = request.session.get('deleteUserErrMsg')
            context['status'] = False
            del request.session['deleteUserErrMsg']
        if request.session.get('deleteUserMsg'):
            context['message'] = request.session.get('deleteUserMsg')
            context['status'] = True
            del request.session['deleteUserMsg']
        # temporary
        if request.session.get('confirmationMailSendErrMsg'):
            context['message'] = request.session.get('confirmationMailSendErrMsg')
            context['status'] = False
            del request.session['confirmationMailSendErrMsg']
        if request.session.get('confirmationMailSendMsg'):
            context['message'] = request.session.get('confirmationMailSendMsg')
            context['status'] = True
            del request.session['confirmationMailSendMsg']
        context['per_page'] = 50
        user_accounts = self.paginate(user_accounts, page=1,
                                      per_page=context['per_page'])
        context['user_accounts'] = user_accounts
        return render(request, 'customer-management/customer-management.html', context)

    def post(self, request):
        if request.POST.get('action_type') == 'user_lock_unlock':
            email = request.POST.get('emailLockUnlock')
            type_lock_unlock = request.POST.get('typeLockUnlock')
            lock_status = False
            if type_lock_unlock == '0':
                lock_status = True
            try:
                user_acc = Useraccounts.objects.get(customer__user__email=email)
                user_acc.islocked = lock_status
                user_acc.save()
                if user_acc.islocked:
                    add_log_action(request, user_acc, status=f'user account "{user_acc.firstname}" has been locked', status_id=2)
                    message = 'User Locked Successfully'
                else:
                    add_log_action(request, user_acc, status=f'user account "{user_acc.firstname}" has been unlocked', status_id=2)
                    message = 'User Unlocked Successfully'
                if request.session.get('lockStatusMsg'):
                    del request.session['lockStatusMsg']
                request.session['lockStatusMsg'] = message
            except Exception as e:
                logger.info(f"{e}")
                if request.session.get('lockStatusErrMsg'):
                    del request.session['lockStatusErrMsg']
                request.session['lockStatusErrMsg'] = 'Error Occured'
            return redirect('/customerManagement')
        elif request.POST.get('action_type') == 'delete_user':
            user_id = request.POST.get('userAccountId')
            try:
                user_acc = Useraccounts.objects.get(id=user_id)
                user_acc.isdeleted = True
                user_acc.save()
                add_log_action(request, user_acc, status=f'user account "{user_acc.firstname}" has been deleted', status_id=3)
                if request.session.get('deleteUserMsg'):
                    del request.session['deleteUserMsg']
                request.session['deleteUserMsg'] = 'User deleted successfully'
            except Exception as e:
                logger.info(f"{e}")
                if request.session.get('deleteUserErrMsg'):
                    del request.session['deleteUserErrMsg']
                request.session['deleteUserErrMsg'] = 'Error Occured'
            return redirect('/customerManagement')
        elif request.POST.get('action_type') == 'allow_wallet_withdrawal':
            try:
                user_id = request.POST.get('userAccountId')
                user_acc = Useraccounts.objects.get(id=user_id)
                user_acc.allow_wallet_withdrawal = True
                user_acc.save()
                add_log_action(request, user_acc, status=f'Wallet Withdrawal Transfer has been allowed to user account "{user_acc.firstname}"', status_id=2)
                message = 'Wallet Withdrawal Transfer allowed Successfully'
                request.session['lockStatusMsg'] = message
            except Exception as e:
                logger.info(f"{e}")
                request.session['lockStatusErrMsg'] = 'Error Occured'
            return redirect('/customerManagement')


@method_decorator(login_required, name='dispatch')
@method_decorator(admin_subadmin_only, name='dispatch')
class GetCustomerDetails(View, ModelQueries, AccountActivationMail):
    def get(self, request):
        slug = request.GET.get('slug')
        try:
            user_details = Useraccounts.objects.get(isdeleted=False, slug=slug)
        except Exception as e:
            logger.info(f"{e}")
            user_details = ''
        if slug and user_details:
            # account_details = Accounts.objects.filter(isdeleted=False,user_account__customer=user_details.customer).order_by('isprimary')
            if request.GET.get('userDocument') == 'statement':
                context = {}
                current_user_details = ""
                if user_details.added_by:
                    current_user_details = user_details
                    user_details = user_details.added_by.useracc_customer.all()[0]
                accounts = self.get_accounts(user_details, True)
                sessiondata = request.session.get("transaction_details_postdata")
                current_date = datetime.datetime.now()
                prev_date = (datetime.datetime.now() - datetime.timedelta(days=30))
                if sessiondata:
                    accountid = int(sessiondata.get("accountid")) if sessiondata.get("accountid") else None
                    from_date = sessiondata.get("from_date") if sessiondata.get(
                        "from_date") else datetime.datetime.strftime(prev_date, "%Y-%m-%d")
                    to_date = sessiondata.get("to_date") if sessiondata.get(
                        "from_date") else datetime.datetime.strftime(current_date, "%Y-%m-%d")
                    transaction_no = sessiondata.get("transaction_no") if sessiondata.get("from_date") else ""
                    beneficiary_name = sessiondata.get("beneficiary_name") if sessiondata.get("from_date") else ""
                    creditdebit = sessiondata.get("creditdebit")
                    per_page = sessiondata.get("per_page") if sessiondata.get("per_page") else 10
                    page = sessiondata.get("page") if sessiondata.get("page") else 1
                    if sessiondata.get("accountid"):
                        account = Accounts.objects.get(id=sessiondata.get("accountid"), isdeleted=False)
                    else:
                        account = accounts[0] if accounts else None
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
                context = {
                    'accounts': accounts,
                    'accountid': accountid,
                    'transaction_no': transaction_no,
                    'beneficiary_name': beneficiary_name,
                    'creditdebit': creditdebit,
                    'to_date': to_date,
                    'from_date': from_date,
                    'per_page': per_page,
                    'account': account,
                    'user_details': user_details,
                    'current_user_details': current_user_details if current_user_details else user_details
                }
                try:
                    transactions = Transactions.objects.filter(Q(fromaccount=account) | Q(toaccount=account),
                                                               isdeleted=False) \
                        .order_by('-id')
                    transactions = self.get_transactions_filtered(transactions, accountid=accountid,
                                                                  transaction_no=transaction_no,
                                                                  beneficiary_name=beneficiary_name,
                                                                  from_date=from_date, to_date=to_date,
                                                                  creditdebit=creditdebit)
                    if not account.createdby.customer_details.all()[0].useracc_customer.all()[0].ismaster_account:
                        transactions = transactions.filter(~Q(amount_type="Conversion Fee")).exclude(
                            Q(toaccount__user_account__ismaster_account=True) &
                            ~Q(transactiontype__name="Third Party Transfer"))
                    transactions = transactions.order_by("-id")
                    transactions = self.paginate(transactions, page=page,
                                                 per_page=per_page)
                except Exception as e:
                    logger.info(f"{e}")
                    transactions = []
                # transactions = self.paginate(transactions, page=page,
                #                              per_page=per_page)
                context['transactions'] = transactions
                return render(request, 'customer-management/statements.html', context)
            elif request.GET.get('userDocument') == 'referrals':
                referees = user_details.user_referred_by.filter(isdeleted=False,show_referee=True).order_by('-id')
                context = {
                    'user_details': user_details,
                    'referees' : referees
                }
                if request.session.get('addReferee'):
                    context['message'] = request.session.get('addReferee')
                    context['status'] = True
                    del request.session['addReferee']
                if request.session.get('deleteReferee'):
                    context['message'] = request.session.get('deleteReferee')
                    context['status'] = True
                    del request.session['deleteReferee']
                return render(request, 'customer-management/refferals.html', context)

            customer_documents = Customerdocuments.objects.filter(isdeleted=False,
                                                                  customer=user_details.customer).order_by(
                'verificationtype__verificationtype')
            company_detials = ''
            if user_details.customer.customertype == 2:
                company_detials = Businessdetails.objects.get(customer=user_details.customer, isdeleted=False)
            context = {
                'user_details': user_details,
                'company_detials': company_detials,
                # 'account_details' : account_details,
                'account_details': self.get_accounts(user_details, True).order_by('isprimary'),
                'customer_documents': customer_documents,
            }
            if request.session.get('customerDetailsErrMsg'):
                context['message'] = request.session.get('customerDetailsErrMsg')
                context['status'] = False
                del request.session['customerDetailsErrMsg']
            if request.session.get('customerDetailsMsg'):
                context['message'] = request.session.get('customerDetailsMsg')
                context['status'] = True
                del request.session['customerDetailsMsg']
            if request.session.get('CustomMailStatusMsg'):
                context['message'] = request.session.get('CustomMailStatusMsg')
                context['status'] = True
                del request.session['CustomMailStatusMsg']
            return render(request, 'customer-management/personal-details.html', context)
        else:
            return redirect('/customerManagement')

    def post(self, request):
        response = {}
        action_type = request.POST.get("action_type")
        slug = request.POST.get('slug')
        user_details = Useraccounts.objects.get(isdeleted=False, slug=slug)
        if action_type == "gettransactionbyaccount":
            context = json.loads(json.dumps(request.POST))
            context['accountid'] = int(context['accountid'])
            accountid = request.POST.get("accountid")
            transaction_no = request.POST.get("transaction_no")
            beneficiary_name = request.POST.get("beneficiary_name")
            from_date = request.POST.get("from_date")
            to_date = request.POST.get("to_date")
            creditdebit = request.POST.get("creditdebit")

            transactions = Transactions.objects.filter(Q(fromaccount__id=accountid) | Q(toaccount__id=accountid),
                                                       isdeleted=False)
            transactions = self.get_transactions_filtered(transactions, accountid=accountid,
                                                          transaction_no=transaction_no,
                                                          beneficiary_name=beneficiary_name,
                                                          from_date=from_date, to_date=to_date, creditdebit=creditdebit)
            if not Accounts.objects.get(id=accountid).createdby.customer_details.all()[0].useracc_customer.all()[0].ismaster_account:
                transactions = transactions.filter(~Q(amount_type="Conversion Fee")).exclude(
                    Q(toaccount__user_account__ismaster_account=True) &
                    ~Q(transactiontype__name="Third Party Transfer"))
            transactions = transactions.order_by("-id")
            transactions = self.paginate(transactions, page=request.POST.get("page", 1),
                                         per_page=request.POST.get("per_page", 10))
            context['accounts'] = self.get_accounts(user_details, True)
            context['user_details'] = Useraccounts.objects.get(isdeleted=False, slug=slug)
            context['current_user_details'] = Useraccounts.objects.get(isdeleted=False, slug=slug)
            context['account'] = Accounts.objects.get(id=accountid)
            context['transactions'] = transactions
            if request.POST.get('from_page'):
                context['from_page'] = request.POST.get('from_page')
            if request.POST.get("is_paginate"):
                response['statementtable_html'] = render_to_string(
                    'transactions/e-statements/includes/statement_table.html', context)
                return HttpResponse(json.dumps(response), content_type='application/json')
            return render(request, 'customer-management/statements.html', context)

        elif action_type == "personal_details":
            comments = request.POST.get('Comments')
            user_id = request.POST.get('UserId')
            status = request.POST.get('VerificationStatus')
            risk_management = request.POST.get('RiskManagement')

            def validate():
                if not comments:
                    return {
                        'status': False,
                        'message': 'Comment is required.'
                    }
                try:
                    admin_comment = Comments.objects.create(content=comments,
                                                            createdby=AdminAccount.objects.get(createdby=request.user),
                                                            status=status)
                    user_acc = Useraccounts.objects.get(id=user_id)
                    print("user_acc.activestatus",user_acc.activestatus)
                    mail_send = True
                    if user_acc.activestatus == "Verified":
                        mail_send = False
                    user_acc.activestatus = status
                    user_acc.risk_management = risk_management
                    user_acc.admincomments.add(admin_comment)
                    user_acc.save()
                    if mail_send and user_acc.activestatus == "Verified":
                        self.send_activation_mail(user_acc)
                        self.send_admin_approved_welcome_mail_touser(user_acc)
                    add_log_action(request, user_acc, status=f'admin commented on {user_acc.firstname} that "{admin_comment.content}" and account status changed to "{user_acc.activestatus}"', status_id=1)
                    return {
                        'status': True,
                        'message': 'Document updated'
                    }
                except Exception as e:
                    logger.info(f"{e}")
                    return {
                        'status': False,
                        'message': 'Something went wrong'
                    }

            data = validate()
            if data.get('status'):
                if request.session.get('customerDetailsMsg'):
                    del request.session['customerDetailsMsg']
                request.session['customerDetailsMsg'] = data.get('message')
            else:
                if request.session.get('customerDetailsErrMsg'):
                    del request.session['customerDetailsErrMsg']
                request.session['customerDetailsErrMsg'] = data.get('message')
            return redirect('/getCustomerDetails?slug=' + slug)

        elif action_type == "update_upi_payment_status":
            response = {}
            upi_payment_status = request.POST.get("status")
            if upi_payment_status:
                upi_payment_status = eval(upi_payment_status.capitalize())
            user_account = Useraccounts.objects.get(slug=slug)
            user_account.upi_payment = upi_payment_status
            user_account.save()
            return HttpResponse(json.dumps(response), content_type='application/json')
@method_decorator(login_required, name='dispatch')
@method_decorator(admin_subadmin_only, name='dispatch')
class ViewImageDetails(View):
    def get(self, request):
        slug = request.GET.get('slug')
        try:
            if request.GET.get("Type") == "2":
                inc_trace_payment = Incomingtracepayment.objects.get(slug=slug)
                file = inc_trace_payment.paymentattachment
                filename = file.name
            elif request.GET.get("Type") == "3":
                inc_trace_payment = Receivemoney.objects.get(slug=slug)
                file = inc_trace_payment.payment_proof
                filename = file.name
            elif request.GET.get("Type") == "4":
                int_transaction = Internationaltransactions.objects.get(slug=slug)
                file = InvoiceDocument.objects.get(transaction=int_transaction.transaction).invoice_doc
                filename = file.name
            elif request.GET.get("Type") == "5":
                int_transaction = DomesticTransaction.objects.get(slug=slug)
                file = InvoiceDocument.objects.get(transaction=int_transaction.transaction).invoice_doc
                filename = file.name
            else:
                file = Customerdocumentfiles.objects.get(slug=slug).filelocation
                filename = file.name

            ext = os.path.splitext(filename)[1]
            format = ''
            if ext == '.jpg':
                format = 'image/jpg'
            elif ext == '.png':
                format = 'image/png'
            elif ext == '.pdf':
                format = 'application/pdf'
            elif ext == '.tiff':
                format = 'image/tiff'
            elif ext == '.jpeg':
                format = 'image/jpeg'
            elif ext == '.JPG':
                format = 'image/JPG'
            elif ext == '.JPEG':
                format = 'image/JPEG'
            elif ext == '.PDF':
                format = 'application/pdf'
            elif ext == '.TIFF':
                format = 'image/PDF'
            elif ext == '.PNG':
                format = 'image/png'

            filepath = settings.AWS_S3_BUCKET_URL+settings.AWS_S3_MEDIA_URL+file.name
            cloudfile = urlopen(url=filepath)
            return FileResponse(cloudfile, content_type=format)
        # except FileNotFoundError:
        #     raise Http404()
        except Exception as e:
            logger.info(f"{e}")
            return redirect('/customerManagement')


@method_decorator(login_required, name='dispatch')
class SendMail(View, CustomMail):
    def post(self, request):
        slug = request.POST.get('slug')
        subject = request.POST.get('Subject')
        content = request.POST.get('Content')
        sendermail = request.POST.get('SenderMail')
        send_status = self.send_custom_mail(subject, content, sendermail)
        message = 'Email sent!'
        if request.session.get('CustomMailStatusMsg'):
            del request.session['CustomMailStatusMsg']
        request.session['CustomMailStatusMsg'] = message
        if slug:
            return redirect('/getCustomerDetails?slug=' + slug)
        return redirect('/customerManagement')


@method_decorator(login_required, name='dispatch')
@method_decorator(admin_subadmin_only, name='dispatch')
class FilterCustomers(View, ModelQueries):
    def get(self, request):
        name = request.GET.get('name').strip()
        company_name = request.GET.get('companyName').strip()
        email = request.GET.get('email').strip()
        phone_no = request.GET.get('phoneNo').strip()
        account_no = request.GET.get('accountNo').strip()
        account_type = request.GET.get('accountType').strip()
        status = request.GET.get('status').strip()
        user_accounts = Useraccounts.objects.filter(isdeleted=False).order_by('-id')
        if name:
            user_accounts = user_accounts.filter(fullname__icontains=name)
        if company_name:
            user_accounts = user_accounts.filter(customer__bsnssdtls_cstmr__companyname__icontains=company_name)
        if email:
            user_accounts = user_accounts.filter(customer__user__email=email)
        if phone_no:
            user_accounts = user_accounts.filter(phonenumber__icontains=phone_no, )
        if account_no:
            user_accounts = user_accounts.filter(accnt_usr_accnt__accountno=account_no)
        if account_type:
            user_accounts = user_accounts.filter(customer__customertype=int(account_type))
        if status:
            user_accounts = user_accounts.filter(activestatus=status)
        user_accounts = self.paginate(user_accounts, page=request.GET.get("page", 1),
                                      per_page=request.GET.get("pageNo", 50))
        context = {'user_accounts': user_accounts}
        template = render_to_string('customer-management/filter-customer.html', context)
        response = {'customer_details': template, }
        return JsonResponse(response)


@method_decorator(login_required, name='dispatch')
@method_decorator(admin_subadmin_only, name='dispatch')
class ManageWireTransferRequestsView(View, ModelQueries):
    def get(self, request):
        context = {}
        context['currencies'] = Currencies.active.all().order_by('code')
        context['int_transactions'] = Internationaltransactions.active.filter(hideforadmin=False).order_by("-id")
        paginator = Paginator( context['int_transactions'] , per_page=100)

        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context['int_transactions'] = page_obj
        return render(request, 'wire-transfer-request/transfer-requests.html', context)

    def post(self, request):
        context = {}
        action_type = request.POST.get("action_type")
        if action_type == "filter_transactions":
            name = request.POST.get("name").strip()
            email = request.POST.get("email").strip()
            accountno = request.POST.get("accountno").strip()
            from_date = request.POST.get("fromdate")
            to_date = request.POST.get("todate")
            currencyid = request.POST.get("currencyid")
            tr_status = request.POST.get("tr_status")
            per_page = request.POST.get("per_page")
            transfer_type = request.POST.get("transfer_type")
            int_transactions = self.get_international_transaction_filtered(name, email, accountno, from_date, to_date,
                                                                           currencyid, tr_status, transfer_type).order_by("-id")
            int_transactions = self.paginate(int_transactions, page=request.POST.get("page"),
                                             per_page=per_page)
            context = request.POST.dict()
            context['currencyid'] = int(context['currencyid']) if context['currencyid'] else None
            context['currencies'] = Currencies.active.all().order_by('code')
            context['int_transactions'] = int_transactions
            if request.POST.get("is_paginate"):
                response = {}
                response['statementtable_html'] = render_to_string(
                    'wire-transfer-request/includes/transfer-requests-table.html', context)
                return JsonResponse(response)
        elif action_type == "hide-transaction":
            response = {}
            int_transaction_id = request.POST.get("int_transaction_id")
            try:
                if int_transaction_id.startswith('INT_'):
                    int_transaction_obj = Internationaltransactions.active.get(id=int_transaction_id[4:])
                elif int_transaction_id.startswith('DOM_'):
                    int_transaction_obj = DomesticTransaction.active.get(id=int_transaction_id[4:])
                int_transaction_obj.hideforadmin = True
                int_transaction_obj.save()
                add_log_action(request, int_transaction_obj, status=f"international transaction created by user with email '{int_transaction_obj.createdby.email}' has been hidden from admin", status_id=2)
                response['status'] = True
            except Exception as e:
                logger.info(f"{e}")
                response['status'] = False
                response['message'] = "Transaction does not exist!"
            return HttpResponse(json.dumps(response), content_type='application/json')
        return render(request, 'wire-transfer-request/transfer-requests.html', context)


@method_decorator(login_required, name='dispatch')
@method_decorator(admin_subadmin_only, name='dispatch')
class GetStatements(View):
    def get(self, request):
        if request.session.get("ad-transaction_id") and request.session.get("ad-slug"):
            context = {}
            try:
                transaction = Transactions.objects.get(id=request.session.get("ad-transaction_id"))
                try:
                    tr_objs = Transactions.objects.filter(transactionno=transaction.parenttransaction.transactionno,isdeleted=False)
                except:
                    tr_objs = []
                for tr_obj in tr_objs:
                    if tr_obj.amount_type == "Net Amount":
                        transaction = tr_obj
            except Exception as e:
                logger.info(e)
                return redirect('/customerManagement')
            context['transaction'] = transaction
            context['slug'] = request.session.get("ad-slug")
            return render(request, 'customer-management/transaction-details.html', context)
        return redirect('/customerManagement')

    def post(self, request):
        action_type = request.POST.get('action_type')
        slug = request.POST.get('slug')
        context = {}
        if action_type == "get_trasnactiondetailsby_id":
            transaction = Transactions.objects.get(id=request.POST.get("transaction_id"))
            try:
                tr_objs = Transactions.objects.filter(transactionno=transaction.parenttransaction.transactionno,isdeleted=False)
            except:
                tr_objs = []
            for tr_obj in tr_objs:
                if tr_obj.amount_type == "Net Amount":
                    transaction = tr_obj
            account = Accounts.objects.get(id=request.POST.get("account_id"))
            context['transaction'] = transaction
            context['account'] = account
            request.session['ad-transaction_id'] = request.POST.get("transaction_id")
            request.session['ad-slug'] = slug
            context['slug'] = slug
            return render(request, 'customer-management/transaction-details.html', context)


@method_decorator(login_required, name='dispatch')
@method_decorator(admin_subadmin_only, name='dispatch')
class AddReferral(View):
    def get(self, request):
        slug = request.GET.get('slug')
        try:
            user_details = Useraccounts.objects.get(isdeleted=False, slug=slug)
        except Exception as e:
            logger.info(f"{e}")
            user_details = ''
        if user_details:
            context = {
                'referrerSlug': user_details.slug,
            }
            return render(request, 'customer-management/add-referral.html', context)
        return redirect('/customerManagement')

    def post(self, request):
        slug = request.POST.get('referrerSlug').strip()
        referee_email = request.POST.get('refereeEmail').strip()

        def validate():
            if not referee_email:
                return {
                    'status': False,
                    'message': 'Email is required'
                }
            email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            if referee_email and not re.search(email_regex, referee_email):
                return {
                    'status': False,
                    'message': 'Invalid email'
                }
            try:
                referrer_acc = Useraccounts.objects.get(slug=slug, isdeleted=False)
            except Exception as e:
                logger.info(f"{e}")
                return {
                    'status': False,
                    'message': 'Referrer account does not exist'
                }
            try:
                referee_acc = Useraccounts.objects.get(customer__user__email=referee_email)
            except Exception as e:
                logger.info(f"{e}")
                return {
                    'status': False,
                    'message': 'Email does not exists!'
                }
            if referrer_acc == referee_acc:
                return {
                    'status': False,
                    'message': 'Can not add own account as a referral'
                }
            if referee_acc.referred_by:
                return {
                    'status': False,
                    'message': f"{'User already linked!' if referee_acc.customer.customertype == 1 else 'User under this company already linked'}"
                }
            if referee_acc.customer.customertype == 2:
                for user in Useraccounts.active.filter(added_by=referee_acc.added_by):
                    user.referred_by = referrer_acc
                    if user == referee_acc:
                        user.show_referee = True
                    user.save()
                    add_log_action(request, referee_acc, status=f'added {user.firstname} as {referrer_acc.firstname}"s referee', status_id=1)

                referrer_acc.referencecount += 1
                referrer_acc.save()
            else:
                referee_acc.referred_by = referrer_acc
                referee_acc.show_referee = True
                referee_acc.save()
                referrer_acc.referencecount += 1
                referrer_acc.save()
                add_log_action(request, referee_acc, status=f'added {referee_acc.firstname} as {referrer_acc.firstname}"s referee', status_id=1)
            return {
                'status': True,
                'message': 'Referral added successfully!'
            }

        data = validate()
        if data.get('status'):
            if request.session.get('addReferee'):
                del request.session['addReferee']
            request.session['addReferee'] = data.get('message')
            return redirect('/getCustomerDetails?userDocument=referrals&slug=' + slug)
        else:
            context = request.POST.dict()
            context['status'] = False
            context['message'] = data.get('message')
            return render(request, 'customer-management/add-referral.html', context)

@method_decorator(login_required, name='dispatch')
@method_decorator(admin_subadmin_only, name='dispatch')
class EditReferral(View):
    def get(self, request):
        referrarslug = request.GET.get('slug')
        refereeslug = request.GET.get('refereeslug')
        try:
            user_details = Useraccounts.objects.get(isdeleted=False, slug=refereeslug)
        except Exception as e:
            logger.info(f"{e}")
            user_details = ''
        if user_details:
            context = {
                'refereeSlug': user_details.slug,
                'referrerSlug': referrarslug,
                'outTranFee' : user_details.customer.outgoingtansactionfee
            }
            return render(request, 'customer-management/edit-referral.html', context)
        return redirect('/customerManagement')
    def post(self, request):
        refereeSlug = request.POST.get('refereeSlug')
        referrerSlug = request.POST.get('referrerSlug')
        OutgoingTransactionFee = request.POST.get('outTranFee').strip()
        def validate(OutgoingTransactionFee):
            if not OutgoingTransactionFee:
                return {
                    'status': False,
                    'message': 'Outgoing Transaction Fee is required.'
                }
            try:
                OutgoingTransactionFee = round(Decimal(OutgoingTransactionFee),2)
            except Exception as e:
                logger.info(e)
                return {
                    'status' : False,
                    'message' : 'Fee should be in numbers'
                }
            if OutgoingTransactionFee < 0 or OutgoingTransactionFee > 100:
                return {
                    'status': False,
                    'message': 'Please enter value in the range of 0-100'
                }
            try:
                referee_acc = Useraccounts.objects.get(slug=refereeSlug, isdeleted=False)
            except Exception as e:
                logger.info(f"{e}")
                return {
                    'status': False,
                    'message': 'Referee account does not exist'
                }
            if referee_acc.customer.customertype == 2:
                for user in Useraccounts.active.filter(added_by=referee_acc.added_by):
                    user.customer.outgoingtansactionfee = OutgoingTransactionFee
                    user.customer.save()
                    add_log_action(request, referee_acc, status=f'{user.firstname}"s refferal fee has been updated to {OutgoingTransactionFee}%', status_id=2)
            else:
                referee_acc.customer.outgoingtansactionfee = OutgoingTransactionFee
                referee_acc.customer.save()              
                add_log_action(request, referee_acc, status=f'{referee_acc.firstname}"s refferal fee has been updated to {OutgoingTransactionFee}%', status_id=2)
            return {
                'status': True,
                'message': 'Referral Fee updated successfully!'
            }

        data = validate(OutgoingTransactionFee)
        if data.get('status'):
            request.session['addReferee'] = data.get('message')
            return redirect('/getCustomerDetails?userDocument=referrals&slug=' + referrerSlug)
        else:
            context = request.POST.dict()
            context['status'] = False
            context['message'] = data.get('message')
            return render(request, 'customer-management/edit-referral.html', context)
    

@method_decorator(login_required, name='dispatch')
class DeleteReferral(View):
    def post(self, request):
        referrer_slug = request.POST.get('referrerSlug').strip()
        referee_slug = request.POST.get('refereeSlug').strip()
        referee_email = request.POST.get('refereeEmail').strip()
        if request.POST.get("action_type") == 'delete_referee':
            try:
                referrer_useraccount = Useraccounts.objects.get(isdeleted=False, slug=referrer_slug)
                referee_useraccount = Useraccounts.objects.get(isdeleted=False, slug=referee_slug)
                if referee_useraccount.referred_by == referrer_useraccount:
                    if referee_useraccount.customer.customertype == 2:
                        for user in Useraccounts.active.filter(added_by=referee_useraccount.added_by):
                            user.referred_by = None
                            if user == referee_useraccount:
                                user.show_referee = False
                            user.save()
                            user.customer.outgoingtansactionfee = 0
                            user.customer.save()
                            add_log_action(request, referrer_useraccount, status=f'{referrer_useraccount.firstname}"s referee {user.firstname} has been deleted', status_id=3)
                        referrer_useraccount.referencecount -= 1
                        referrer_useraccount.save()
                    else:
                        referee_useraccount.referred_by = None
                        referee_useraccount.customer.outgoingtansactionfee = 0
                        referee_useraccount.customer.save()
                        referee_useraccount.show_referee = False
                        referee_useraccount.save()
                        referrer_useraccount.referencecount -= 1
                        referrer_useraccount.save()
                        add_log_action(request, referrer_useraccount, status=f'{referrer_useraccount.firstname}"s referee {referee_useraccount.firstname} has been deleted', status_id=3)
                    request.session['deleteReferee'] = 'Referral removed successfully!'
                else:
                    request.session['deleteReferee'] = 'Error Occured!'
                return redirect('/getCustomerDetails?userDocument=referrals&slug=' + referrer_slug)
            except Exception as e:
                logger.info(f"{e}")
                return redirect('/getCustomerDetails?userDocument=referrals&slug=' + referrer_slug)


@method_decorator(login_required, name='dispatch')
@method_decorator(admin_subadmin_only, name='dispatch')
class WireTransferRequestsDetailView(View, ModelQueries, TransactionMail):
    def get(self, request):
        context = {}
        try:
            transaction_id = request.GET.get('TransactionId')
            if transaction_id.startswith('INT_'):
                transaction = Internationaltransactions.objects.get(slug=transaction_id[4:])
            elif transaction_id.startswith('DOM_'):
                transaction = DomesticTransaction.objects.get(slug=transaction_id[4:])
            context['int_transaction'] = transaction
        except Exception as e:
            logger.info(f"{e}")
            return redirect('/transactions')
        return render(request, 'wire-transfer-request/transfer-request-details.html', context)

    def post(self, request):
        action_type = request.POST.get("action_type")
        if action_type == "add-comment":
            tr_status = request.POST.get("tr-status")
            comment = request.POST.get("comment")
            int_transaction_id = request.POST.get("int_transaction_id")
            if int_transaction_id.startswith('INT_'):
                int_transaction_obj = Internationaltransactions.objects.get(id=int_transaction_id[4:])
                modified_slug = f"INT_{int_transaction_obj.slug}"
            elif int_transaction_id.startswith('DOM_'):
                int_transaction_obj = DomesticTransaction.objects.get(id=int_transaction_id[4:])
                modified_slug = f"DOM_{int_transaction_obj.slug}"
            if int_transaction_obj.verificationstatus in ["Refund Requested", "Refunded"]:
                tr_status = int_transaction_obj.verificationstatus
            comment_obj = self.create_comment(request, comment, tr_status, int_transaction_obj)
            # email = int_transaction_obj.transaction.fromaccount.user_account.customer.user.email
            email = int_transaction_obj.createdby.email
            try:
                currency_conversion = Currencyconversionratescombined.active.get(
                    fromcurrency__code=int_transaction_obj.transaction.fromaccount.currency.code,
                    tocurrency__code=int_transaction_obj.currency.code)
                conversionrate = format((currency_conversion.conversionrate), '.4f')
            except Exception as e:
                logger.info(f"{e}")
                conversionrate = None
            email_context = {
                'int_transaction': int_transaction_obj,
                'conversionrate': conversionrate

            }
            if tr_status == "Executed":
                self.mail_transfer_executed(email, email_context)
            try:
                return redirect('/getransactionDetails?TransactionId='+modified_slug)
            except Exception as e:
                logger.info(f"{e}")
                return redirect('/transactions')
        elif action_type == "refund-transaction":
            response = {}
            status = True
            message = ""
            if request.user.adminacc_created_by.approval_level in ["Inputter",
                                                                   "Inputter / Approver"]:  # Only inputter can do refund
                refund_amount = request.POST.get("refund-amount")
                comment = request.POST.get("comment")
                int_transaction_id = request.POST.get("int_transaction_id")
                if int_transaction_id.startswith('INT_'):
                    int_transaction_obj = Internationaltransactions.objects.get(id=int_transaction_id[4:])
                elif int_transaction_id.startswith('DOM_'):
                    int_transaction_obj = DomesticTransaction.objects.get(id=int_transaction_id[4:])
                
                total_amount = self.get_debit_amount(int_transaction_obj.transaction,tr_req=True)
                if float(refund_amount) > float(total_amount):
                    message = "Refund amount greater than original amount."
                    status = False
                else:
                    if type(int_transaction_obj).__name__ == "Internationaltransactions":
                        ref_rqst_obj = RefundRequests.objects.create(wire_transaction=int_transaction_obj,
                                                                                 amount=refund_amount)
                    elif type(int_transaction_obj).__name__ == "DomesticTransaction":
                        ref_rqst_obj = DomesticTransactionRefundRequests.objects.create(domestic_transaction=int_transaction_obj,
                                                                                 amount=refund_amount)
                    
                    ref_rqst_obj.requestedby = request.user.adminacc_created_by
                    ref_rqst_obj.comment = comment
                    ref_rqst_obj.save()
                    int_transaction_obj.verificationstatus = "Refund Requested"
                    int_transaction_obj.save()
                    comment_obj = self.create_comment(request, comment, int_transaction_obj.verificationstatus,
                                                      int_transaction_obj)
            else:
                status = False
                message = "Unauthorised action!"
            response['status'] = status
            response['message'] = message
            return HttpResponse(json.dumps(response), content_type='application/json')


@method_decorator(login_required, name='dispatch')
@method_decorator(admin_only, name='dispatch')
class AdminInwardRemittanceRequestsListView(View, ModelQueries,UtilMixins):
    def get(self, request):
        context = {}
        inward_remittances = Receivemoney.active.all().order_by("-id")
        page_number = request.GET.get('page', 1)
        inward_remittances = self.paginate(inward_remittances, page=page_number, per_page=10)
        context['paginate_data'] = inward_remittances
        context['inward_remittances'] = inward_remittances
        return render(request, 'inward-remittance-requests/inward-remittance-requests.html', context)

    def post(self, request):
        action_type = request.POST.get("action_type")
        if action_type == "filter_receive_request":
            context = {}
            request_type = request.POST.get("request_type")
            per_page = request.POST.get("per_page")
            page = request.POST.get("page",1)
            context = request.POST.dict()
            if request_type == "rep-mis-payment":
                inc_trace_payments = Incomingtracepayment.active.all().order_by("-id")
                inc_trace_payments = self.paginate(inc_trace_payments, page=page,
                                                   per_page=per_page)
                paginate_data = inc_trace_payments
                context['paginate_data'] = paginate_data
                context['inc_trace_payments'] = inc_trace_payments
            else:
                inward_remittances = Receivemoney.active.all().order_by("-id")
                inward_remittances = self.paginate(inward_remittances, page=page,
                                                   per_page=per_page)
                paginate_data = inward_remittances
                context['paginate_data'] = paginate_data
                context['inward_remittances'] = inward_remittances
            if self.is_ajax(request):
                response = {
                    'statementtable_html':render_to_string('inward-remittance-requests/includes/ir-request-list-table.html',context)

                }
                return HttpResponse(json.dumps(response),content_type='application/json')
            return render(request, 'inward-remittance-requests/inward-remittance-requests.html', context)
        elif action_type == "delete-request":
            response = {}
            request_id = request.POST.get("request_id")
            request_type = request.POST.get("request_type")
            try:
                message = ''
                status = True
                if request_type == "inc_trace_payment":
                    request_obj = Incomingtracepayment.active.get(slug=request_id)
                    add_log_action(request, request_obj, status=f"missing outward transfer request from account '{request_obj.account.accountno}' has been deleted", status_id=3)
                elif request_type == "inward_remittance":
                    request_obj = Receivemoney.active.get(slug=request_id)
                    add_log_action(request, request_obj, status=f"inward remittance request from account '{request_obj.receiveraccount.accountno}' has been deleted", status_id=3)
                else:
                    message = 'Invalid Request Type'
                    status = False
                    request_obj = None
                if request_obj:
                    request_obj.isdeleted = True
                    request_obj.save()
            except Exception as e:
                logger.info(f"{e}")
                message = 'Something went wrong! Please try again.'
                status = False
            response['message'] = message
            response['status'] = status
            return HttpResponse(json.dumps(response), content_type='application/json')


@method_decorator(login_required, name='dispatch')
@method_decorator(admin_only, name='dispatch')
class AdminInwardRemittanceRequestsDetailView(View, ModelQueries):
    def get(self, request):
        context = {}
        receive_request_id = request.GET.get("Id")
        reqtype = request.GET.get("Type")
        if reqtype == '1':
            context['inward_remittance'] = Receivemoney.active.get(slug=receive_request_id)
        elif reqtype == '2':
            context['inc_trace_payment'] = Incomingtracepayment.active.get(slug=receive_request_id)
        else:
            return redirect('/receiveMoneyRequest')
        return render(request, 'inward-remittance-requests/view-receive-request.html', context)

    def post(self, request):
        action_type = request.POST.get("action_type")
        if action_type == "add-comment":
            context = {}
            inc_trace_payment_status = request.POST.get("inc_trace_payment_status")
            comment = request.POST.get("comment")
            inc_trace_payment_id = request.POST.get("inc_trace_payment_id")
            inc_trace_payment = Incomingtracepayment.active.get(id=inc_trace_payment_id)
            comment_obj = Comments.objects.create(content=comment, createdby=request.user.adminacc_created_by,
                                                  status=inc_trace_payment_status)
            inc_trace_payment.status = inc_trace_payment_status
            inc_trace_payment.save()
            inc_trace_payment.admincomments.add(comment_obj)
            context['inc_trace_payment'] = inc_trace_payment
            return render(request, 'inward-remittance-requests/view-receive-request.html', context)


@method_decorator(login_required, name='dispatch')
@method_decorator(admin_only, name='dispatch')
@method_decorator(allowed_users(admin_type=['Inputter', 'Inputter / Approver']), name='dispatch')
class AdminInwardRemittanceManageView(View, ModelQueries):
    def get(self, request):
        context = {}
        if request.session.get("ir_success_message"):
            context['message'] = request.session.get("ir_success_message")
            context['status'] = True
            del request.session["ir_success_message"]
        return render(request, 'inward-remittance-management/debitcredit-request-list.html',context)

    def post(self, request):
        action_type = request.POST.get("action_type")
        if action_type == "search_debitcredit_requests":
            name = request.POST.get("name").strip()
            email = request.POST.get("email").strip()
            accountno = request.POST.get("accountno").strip()
            context = request.POST.dict()
            if name or email or accountno:
                accounts = self.filter_user_account(name, email, accountno)
                context['accounts'] = accounts
            return render(request, 'inward-remittance-management/debitcredit-request-list.html', context)

        if action_type == "creditdebit":
            response = {}
            amount = request.POST.get("amount")
            comment = request.POST.get("comment")
            account_id = request.POST.get("account_id")
            creditdebit_type = request.POST.get("creditdebit_type")
            try:
                account = Accounts.active.get(id=account_id)
                if creditdebit_type == "1":
                    transactiontype = Transactiontypes.objects.get(name='Inward Remittance')
                else:
                    transactiontype = Transactiontypes.objects.get(name='Other Charges')

                inwardremittancetr_obj = Inwardremittancetransactions.objects.create(amount=amount, account=account, currency=account.currency,
                                                            transactiontype=transactiontype,
                                                            comment=comment)
                add_log_action(request, inwardremittancetr_obj, status=f"{'Amount' if creditdebit_type == '1' else 'Charge'} of {inwardremittancetr_obj.amount} {inwardremittancetr_obj.currency.code} has been added for approve", status_id=1)
                response['status'] = True
                request.session["ir_success_message"] = f"{'Amount' if creditdebit_type == '1' else 'Charge'} Added successfully"
            except Exception as e:
                logger.info(f"{e}")
                response['status'] = False
                response["message"] = "Something went wrong! Please try again."
            return HttpResponse(json.dumps(response), content_type='application/json')
        return render(request, 'inward-remittance-management/debitcredit-request-list.html')

@method_decorator(login_required, name='dispatch')
@method_decorator(admin_subadmin_only, name='dispatch')
class PasswordResetMail(View,ConfirmYourMail):
    def post(self, request):
        useraccount_id = request.POST.get('userAccountID')
        try:
            user_account = Useraccounts.objects.get(id=useraccount_id)
            full_name = f"{user_account.firstname} {user_account.lastname}"
            user = user_account.customer.user
            user_email = user.email
            user_account.is_prevuser = False
            user_account.save()
            mail_status = self.send_confirm_mail(full_name, user_email,createdby=user,transaction_type=1, dev_type=1)
            request.session['confirmationMailSendMsg'] = 'Email sent' 
            return redirect('/customerManagement')
        except Exception as e:
            logger.info(f"{e}")
            request.session['confirmationMailSendErrMsg'] = 'Error occured'
            return redirect('/customerManagement')

@method_decorator(login_required, name='dispatch')
@method_decorator(admin_subadmin_only, name='dispatch')
class ManageWalletWithdrawalTransferRequestsView(View, ModelQueries):
   
    def get(self, request):
        context = {}
        context['currencies'] = Currencies.active.filter(code="USD").order_by('code')
        withdrawal_transactions = WalletWithdrawalTransactions.active.filter(hideforadmin=False).order_by("-id")
        page_number = request.GET.get('page', 1)
        withdrawal_transactions = self.paginate(withdrawal_transactions, page=page_number, per_page=20)
        context['wallet_withdrawal_transactions'] = withdrawal_transactions
        return render(request, 'wallet-withdrawal-transfer-request/transfer-requests.html', context)
    
    def post(self, request):
        context = {}
        action_type = request.POST.get("action_type")
        if action_type == "filter_transactions":
            name = request.POST.get("name").strip()
            email = request.POST.get("email").strip()
            accountno = request.POST.get("accountno").strip()
            from_date = request.POST.get("fromdate")
            to_date = request.POST.get("todate")
            currencyid = request.POST.get("currencyid")
            tr_status = request.POST.get("tr_status")
            per_page = request.POST.get("per_page")
        
            wallet_withdrawal_transactions = self.get_wallet_withdrawal_transaction_filtered(name, email, accountno, from_date, to_date,
                                                                           currencyid, tr_status).order_by("-id")
            wallet_withdrawal_transactions = self.paginate(wallet_withdrawal_transactions, page=request.POST.get("page"),
                                             per_page=per_page)
            paginate_data = wallet_withdrawal_transactions
            context = request.POST.dict()
            context['paginate_data'] = paginate_data
            context['currencyid'] = int(context['currencyid']) if context['currencyid'] else None
            context['currencies'] = Currencies.active.filter(code="USD").order_by('code')
            context['wallet_withdrawal_transactions'] = wallet_withdrawal_transactions
            if request.POST.get("is_paginate"):
                response = {}
                response['statementtable_html'] = render_to_string(
                    'transactions/e-statements/includes/statement_table.html', context)
                return HttpResponse(json.dumps(response), content_type='application/json')
        elif action_type == "hide-transaction":
            response = {}
            wallet_withdrawal_transaction_id = request.POST.get("wallet_withdrawal_transaction_id")            
            try:
                wallet_withdrawal_transaction_obj = WalletWithdrawalTransactions.active.get(id=wallet_withdrawal_transaction_id)
                wallet_withdrawal_transaction_obj.hideforadmin = True
                wallet_withdrawal_transaction_obj.save()
                add_log_action(request, wallet_withdrawal_transaction_obj, status=f"wallet withdrawal transaction created by user with email '{wallet_withdrawal_transaction_obj.createdby.email}' has been hidden from admin", status_id=2)
                response['status'] = True
            except Exception as e:
                logger.info(f"{e}")
                response['status'] = False
                response['message'] = "Transaction does not exist!"
            return HttpResponse(json.dumps(response), content_type='application/json')
        return render(request, 'wallet-withdrawal-transfer-request/transfer-requests.html', context)


@method_decorator(login_required, name='dispatch')
@method_decorator(admin_subadmin_only, name='dispatch')
class WalletWithdrawalTransferRequestsDetailView(View, ModelQueries, TransactionMail):
    def get(self, request):
        context = {}
        try:
            context['wallet_transaction'] = WalletWithdrawalTransactions.active.get(slug=request.GET.get("TransactionId"))
        except Exception as e:
            logger.info(f"{e}")
            return redirect('/wallet-transactions')
        return render(request, 'wallet-withdrawal-transfer-request/transfer-request-details.html', context)

    def post(self, request):
        action_type = request.POST.get("action_type")
        if action_type == "add-comment":
            tr_status = request.POST.get("tr-status")
            comment = request.POST.get("comment")
            wallet_transaction_id = request.POST.get("wallet_transaction_id")
            wallet_transaction_obj = WalletWithdrawalTransactions.objects.get(id=wallet_transaction_id)
            if wallet_transaction_obj.verificationstatus in ["Refund Requested", "Refunded"]:
                tr_status = wallet_transaction_obj.verificationstatus
            comment_obj = self.create_comment(request, comment, tr_status, wallet_transaction_obj)
            email = wallet_transaction_obj.createdby.email
            try:
                currency_conversion = Currencyconversionratescombined.active.get(
                    fromcurrency__code=wallet_transaction_obj.transaction.fromaccount.currency.code,
                    tocurrency__code=wallet_transaction_obj.currency.code)
                conversionrate = format((currency_conversion.conversionrate), '.4f')
            except Exception as e:
                logger.info(f"{e}")
                conversionrate = None
            email_context = {
                'wallet_transaction': wallet_transaction_obj,
                'conversionrate': conversionrate

            }
            if tr_status == "Executed":
                self.mail_transfer_executed(email, email_context, wallet_tr=True)
            try:
                WalletWithdrawalTransactions.active.get(slug=request.GET.get("TransactionId"))
                return redirect('/get-wallet-transaction-details?TransactionId='+request.GET.get("TransactionId"))
            except Exception as e:
                logger.info(f"{e}")
                return redirect('/wallet-transactions')
        elif action_type == "refund-transaction":
            response = {}
            status = True
            message = ""
            if request.user.adminacc_created_by.approval_level in ["Inputter",
                                                                   "Inputter / Approver"]:  # Only inputter can do refund
                refund_amount = request.POST.get("refund-amount")
                comment = request.POST.get("comment")
                wallet_transaction_id = request.POST.get("wallet_transaction_id")
                wallet_transaction_obj = WalletWithdrawalTransactions.active.get(id=wallet_transaction_id)
                total_amount = self.get_debit_amount(wallet_transaction_obj.transaction,tr_req=True)
                if float(refund_amount) > float(total_amount):
                    message = "Refund amount greater than original amount."
                    status = False
                else:
                    ref_rqst_obj = WalletWithdrawalRefundRequests.objects.create(wallet_withdrawal_transaction=wallet_transaction_obj,
                                                                                 amount=refund_amount)
                    ref_rqst_obj.requestedby = request.user.adminacc_created_by
                    ref_rqst_obj.comment = comment
                    ref_rqst_obj.save()
                    wallet_transaction_obj.verificationstatus = "Refund Requested"
                    wallet_transaction_obj.save()
                    comment_obj = self.create_comment(request, comment, wallet_transaction_obj.verificationstatus,
                                                      wallet_transaction_obj)
            else:
                status = False
                message = "Unauthorised action!"
            response['status'] = status
            response['message'] = message
            return HttpResponse(json.dumps(response), content_type='application/json')


@method_decorator(login_required, name='dispatch')
@method_decorator(admin_only,name='dispatch')
class CrosscurrencyReportView(View, ModelQueries):   
    def get(self, request):
        context = {}
        if request.GET.get('TransactionId'):
            
            t_id = request.GET.get('TransactionId')
            context['cross_currencyreport'] = Transactions.objects.filter(transactionno =t_id ).first()
            return render(request, 'crosscurrency/includes/currency-report-details.html', context)
        
        currencies = Currencies.active.all().order_by('code')
        
        crosscurrency_reports = Transactions.active.filter(transactiontype__name='Currency Conversion').order_by("-id")
        crosscurrency_reports =crosscurrency_reports.exclude(amount_type = "Conversion Fee")
        if not request.user.adminacc_created_by.test_account:
            crosscurrency_reports = crosscurrency_reports.exclude(
                createdby__customer_details__useracc_customer__test_account=True
            )
        crosscurrencyreports = self.paginate(crosscurrency_reports, page=1,
                                    per_page=50)
        context["currencies"] = currencies
        context["crosscurrencyreports"] = crosscurrencyreports
        return render(request, 'crosscurrency/crosscurrency.html', context)
    
    def post(self, request):
        
        if request.POST.get('action_type') == "filter_transactions":
            from_date = request.POST.get("fromdate").strip()
            to_date = request.POST.get("todate").strip()
            request_type = request.POST.get("request_type").strip()
            per_page = request.POST.get("per_page")
            currencycode = request.POST.get('currencycode')
            checkbox =request.POST.get('checkbox')
            page = request.POST.get("page",1)
            
            
            if not currencycode:
                transactions =  Transactions.active.filter(transactiontype__name=request_type).exclude(amount_type = "Conversion Fee").order_by("-id")
               
            else:
                transactions =  Transactions.active.filter(fromaccount__currency__code = currencycode,transactiontype__name=request_type).exclude(amount_type = "Conversion Fee").order_by("-id")
               

            if not checkbox:
                transactions = transactions.exclude(fromaccount__currency__code=F('toaccount__currency__code')).order_by("-id")
                    
          
            
            cross_currency_reports = self.get_transactions_filtered(transactions =transactions , from_date=from_date,
                                                                        to_date=to_date)
            if not request.user.adminacc_created_by.test_account:
                cross_currency_reports = cross_currency_reports.exclude(
                    createdby__customer_details__useracc_customer__test_account=True
                )
            cross_currency_reports = self.paginate(cross_currency_reports, page=page,
                                                 per_page=per_page)
            
            context = request.POST.dict()
            if request_type == 'Currency Conversion':
                currencycon_trans = Transactions.active.filter(transactiontype__name='Currency Conversion').order_by("-id")
                currencies = Currencies.active.all().order_by('code')
                if not request.user.adminacc_created_by.test_account:
                    currencycon_trans = currencycon_trans.exclude(
                        createdby__customer_details__useracc_customer__test_account=True
                    )
                currencycon_trans = self.paginate(currencycon_trans, page=page,
                                                    per_page=per_page)
          
                paginate_data = currencycon_trans
                context['paginate_data'] = paginate_data
                context['currencycon_trans'] = currencycon_trans
                context['currencies'] =currencies
                context['crosscurrencyreports'] = cross_currency_reports
            else :
                response = {}                                                                                            
                account_trans = Transactions.active.filter(transactiontype__name='Acccount To Account Transfer').order_by("-id")
                currencies = Currencies.active.all().order_by('code')
                if not request.user.adminacc_created_by.test_account:
                    account_trans = account_trans.exclude(
                        createdby__customer_details__useracc_customer__test_account=True
                    )
                account_trans = self.paginate(account_trans, page=page,
                                                    per_page=per_page)
                paginate_data = account_trans
                context['paginate_data'] = paginate_data
                context['account_trans'] = account_trans
                context['currencies'] =currencies
                context['checkbox'] = checkbox
                context['crosscurrencyreports'] = cross_currency_reports
            if request.POST.get("is_paginate"):
                response = {}
                response['statementtable_html'] = render_to_string(
                'crosscurrency/includes/currencyreport.html', context)
                return HttpResponse(json.dumps(response), content_type='application/json')
        if request.POST.get('action_type') == "export_statement":
            currencycode = request.POST.get('currencycode')
            from_date = request.POST.get("fromdate").strip()
            to_date = request.POST.get("todate").strip()
            request_type = request.POST.get("request_type").strip()
            per_page = request.POST.get("per_page")
            checkbox =request.POST.get('checkbox')
          
            response = {}
            transactions =  Transactions.active.filter(transactiontype__name=request_type,amount_type="Conversion Fee").order_by("-id")
        
            if not currencycode:
                transactions =  Transactions.active.filter(transactiontype__name=request_type).exclude(amount_type = "Conversion Fee")
                
            else:
                transactions =  Transactions.active.filter(fromaccount__currency__code = currencycode,transactiontype__name=request_type).exclude(amount_type = "Conversion Fee")
            page = request.POST.get("page",1)
            
            if not checkbox:
                transactions = transactions.exclude(fromaccount__currency__code=F('toaccount__currency__code'))
            
            cross_currency_reports = self.get_transactions_filtered(transactions =transactions , from_date=from_date,
                                                                        to_date=to_date)
          
            if not request.user.adminacc_created_by.test_account:
                    cross_currency_reports = cross_currency_reports.exclude(
                        createdby__customer_details__useracc_customer__test_account=True
                    )
            
            response['status'] = True
            filename = f"Currency Report -"+ datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d") + ".csv"
            folder = f"statements/{request.POST.get('action_type')}/"
            filepath = settings.MEDIA_ROOT + settings.MEDIA_URL + folder
            create_directory(filepath)
            header = ['Date','Type','Transaction No','Sender Name','Sender Account No','Amount','Recipient Name','Recipient Account No']
            with open(filepath+filename, 'w', encoding='UTF8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=header)
                # write the header
                writer.writeheader()
                
                for transaction in cross_currency_reports:
            # write the data
                    date = transaction.createdon.strftime("%d/%m/%Y")
                    transaction_type = self.get_transaction_type(transaction)
                    Transaction_No =  transaction.transactionno
                    Sender_Name = transaction.fromaccount.user_account.firstname 
                    Sender_Acc_No = f'{transaction.fromaccount.accountno} ({transaction.fromaccount.currency})'
                    Amount = f'{format(math.ceil(transaction.fromamount*100)/100,".2f")} ({transaction.toaccount.currency})'
                    Recipient_Name = transaction.toaccount.user_account.firstname
                    Recipient_AccNo =f'{transaction.toaccount.accountno} ({transaction.toaccount.currency})'
                    writer.writerow({
                        'Date':date,
                        'Type':transaction_type,
                        'Transaction No':Transaction_No,
                        'Sender Name':Sender_Name,
                        'Sender Account No':Sender_Acc_No,
                        'Amount':Amount,
                        'Recipient Name':Recipient_Name,
                        'Recipient Account No':Recipient_AccNo
                    })
            fileToUpload = open(filepath+filename)
            cloudfilename = folder+filename
            UtilMixins().upload_to_s3(fileToUpload,cloudfilename)
            response['filepath'] = settings.AWS_S3_BUCKET_URL + folder + filename
            return HttpResponse(json.dumps(response),content_type='application/json')
            
        if request.POST.get('action_type') == "checkbox_select":
            from_date = request.POST.get("fromdate").strip()
            to_date = request.POST.get("todate").strip()
            request_type = request.POST.get("request_type").strip()
            per_page = request.POST.get("per_page")
            checkbox = request.POST.get('checkbox')
            response = {}
          
            transactions =  Transactions.active.filter(transactiontype__name=request_type,amount_type="Net Amount").order_by("-id")
            page = request.POST.get("page",1)
            
            cross_currency_reports = self.get_transactions_filtered(transactions =transactions , from_date=from_date,
                                                                        to_date=to_date)
            if not request.user.adminacc_created_by.test_account:
                    cross_currency_reports = cross_currency_reports.exclude(
                        createdby__customer_details__useracc_customer__test_account=True
                    )
            cross_currency_reports = self.paginate(cross_currency_reports, page=page,
                                                 per_page=per_page)
            
            context = {}
            response = {}
            if request_type == 'Currency Conversion':
                currencycon_trans = Transactions.active.filter(transactiontype__name='Currency Conversion').order_by("-id")
                currencies = Currencies.active.all().order_by('code')
                if not request.user.adminacc_created_by.test_account:
                    currencycon_trans = currencycon_trans.exclude(
                        createdby__customer_details__useracc_customer__test_account=True
                    )
                currencycon_trans = self.paginate(currencycon_trans, page=page,
                                                    per_page=per_page)
          
                paginate_data = currencycon_trans
                context['paginate_data'] = paginate_data
                context['currencycon_trans'] = currencycon_trans
                context['currencies'] =currencies
                context['crosscurrencyreports'] = cross_currency_reports
            else :
                
                account_trans = Transactions.active.filter(transactiontype__name='Acccount To Account Transfer').order_by("-id")
                currencies = Currencies.active.all().order_by('code')
                if not request.user.adminacc_created_by.test_account:
                    account_trans = account_trans.exclude(
                        createdby__customer_details__useracc_customer__test_account=True
                    )
                account_trans = self.paginate(account_trans, page=page,
                                                    per_page=per_page)
                paginate_data = account_trans
                context['paginate_data'] = paginate_data
                context['account_trans'] = account_trans
                context['checkbox'] =checkbox
                context['currencies'] =currencies
                context['crosscurrencyreports'] = cross_currency_reports
        
            if request.POST.get("is_paginate"):
                response = {}
                response['statementtable_html'] = render_to_string(
                    'crosscurrency/includes/currencyreport.html', context)
                return HttpResponse(json.dumps(response), content_type='application/json')
        return render(request, 'crosscurrency/crosscurrency.html', context)
        
   