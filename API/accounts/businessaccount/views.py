
import logging
from django.template.loader import render_to_string
from django.http import HttpResponse
import json
from django.views import View
from django.contrib.auth.models import User
from utils.models import Accounts, Countries, Currencies, Industrytypes,Customers, \
    Useraccounts,Businessdetails,Transactionauthoritytypes,Businesstransactionauthorities, \
        Customerdocuments,Customerdocumentdetails,Customerdocumentfiles,Documentfields
from django.shortcuts import render, redirect
from django.conf import settings
import ast
from Transactions.mixins import ConfirmYourMail, add_log_action, randomword
from django.db.models import Q
from Transactions.mixins import OTP,PermissionEmail
import random
import string
from django.http import JsonResponse, response
logger = logging.getLogger('lessons')
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
class AccountRegistrationView(View):
    def get(self,request):
        return render (request,'accounts/openaccount/chooseaccount.html')

class BusinessAccountRegistrationView(View):
    def get(self,request):
        if request.GET.get('Edit') and request.session.get('businessaccount'):
           prevdata = request.session['businessaccount']
        else:
            prevdata = None
        industrytypes = Industrytypes.objects.filter(isdeleted=False)
        countries = Countries.objects.all()
        currencies = Currencies.objects.filter(isdeleted=False)
        authority_types=Transactionauthoritytypes.objects.filter(isdeleted=False)
        context={
            'industrytypes':industrytypes,
            'countries':countries,
            'currencies':currencies,
            'prevdata':prevdata,
            'authority_types':authority_types

        }
        return render (request,'accounts/openaccount/business/business_account_register.html',context)
    def post(self,request):
        firstName_list = request.POST.getlist('firstName')
        lastname_list = request.POST.getlist('lastName')
        middleName_list = request.POST.getlist('middleName')
        email_list = request.POST.getlist('email')
        for email in email_list:
            if User.objects.filter(email=email).exists():
                request.session['email-err'] = f"Email {email} already exist"
            else:
                pass
        user_type_list = request.POST.getlist('userType')
        main_owner_list  = request.POST.getlist('checkboxvalues')
        for value in main_owner_list:
            main_owner_list_new = (value.strip()).split(',')
        if '1' not in main_owner_list_new or main_owner_list_new.count('1') > 1 or len(email_list) != len(set(email_list)) or request.session.get('email-err'):
            user_list_main=[]
            for i in range(len(firstName_list)):
                user_list_main.append({
                    'firstName' : firstName_list[i],
                    'middleName' : middleName_list [i],
                    'lastName' : lastname_list[i],
                    'email' : email_list[i],
                    'userType' :user_type_list[i],
                    'main_owner_list_new' : main_owner_list_new[i]
                })
            industrytypes = Industrytypes.objects.filter(isdeleted=False)
            countries = Countries.objects.all()
            currencies = Currencies.objects.filter(isdeleted=False)
            authority_types=Transactionauthoritytypes.objects.filter(isdeleted=False)
            if request.session.get('businessaccount'):
                del request.session['businessaccount']
                request.session['businessaccount'] = request.POST.dict()
            else:
                request.session['businessaccount'] = request.POST.dict()
            request.session['businessaccount'].update({
                'countryName' :Countries.objects.get(shortform=request.POST.get('country')).name,
                'industryType': Industrytypes.objects.get(id=int(request.POST.get('industryType'))).name,
                'users_lists' : user_list_main,
            })
            if len(email_list) != len(set(email_list)):
                context={
                'authority_types':authority_types,
                'industrytypes':industrytypes,
                'countries':countries,
                'currencies':currencies,
                'prevdata':request.session['businessaccount'],
                'message' : "Users with same email is not allowed."
                }
            elif request.session.get('email-err'):
                context={
                'authority_types':authority_types,
                'industrytypes':industrytypes,
                'countries':countries,
                'currencies':currencies,
                'prevdata':request.session['businessaccount'],
                'message' : request.session.get('email-err')
                }
                del request.session['email-err']
            else:
                message = ''
                if '1' not in main_owner_list_new:
                    message = "Please add a user as the Ultimate Beneficial Owner"
                elif main_owner_list_new.count('1') > 1:
                    message = "Only one user can be Ultimate Beneficial Owner"
                context={
                'authority_types':authority_types,
                'industrytypes':industrytypes,
                'countries':countries,
                'currencies':currencies,
                'prevdata':request.session['businessaccount'],
                'message' : message
                }
            return render(request,'accounts/openaccount/business/business_account_register.html',context)
        else:
            user_list_main=[]
            for i in range(len(firstName_list)):
                user_list_main.append({
                    'firstName' : firstName_list[i],
                    'middleName' : middleName_list [i],
                    'lastName' : lastname_list[i],
                    'email' : email_list[i],
                    'userType' :user_type_list[i],
                    'main_owner_list_new' : main_owner_list_new[i]
                })
            if request.session.get('businessaccount'):
                del request.session['businessaccount']
                request.session['businessaccount'] = request.POST.dict()
            else:
                request.session['businessaccount'] = request.POST.dict()
            
            try:
                users = request.POST.getlist('users')
                for user in users:
                    users_lists = ast.literal_eval(user)
            except Exception as e:
                logger.info(e)
                users_lists=None
            request.session['businessaccount'].update({
                'countryName' :Countries.objects.get(shortform=request.POST.get('country')).name,
                'industryType': Industrytypes.objects.get(id=int(request.POST.get('industryType'))).name,
                'users_lists' : user_list_main,
            })
            return redirect('business-account-confirm')


class BusinessAccountConfirmView(View,ConfirmYourMail):
    def get(self,request):
        if request.session.get('businessaccount'):
            context={
            'first_currency' : Currencies.objects.get(code = request.session['businessaccount'].get('primaryCurrency')),
            'second_currency' : Currencies.objects.get(code = request.session['businessaccount'].get('secondaryCurrency'))}
            return render (request,'accounts/openaccount/business/business_account_register_confirm.html',context)
        else:
            return redirect('business-account-registration')
    def post(self,request):
        if request.session.get('businessaccount'):
            users_lists = request.session.get('businessaccount').get('users_lists')
            for usr in users_lists:
                if usr.get('main_owner_list_new')=='1':
                    indx = int(users_lists.index(usr))
            user_email = request.session['businessaccount'].get('users_lists')[indx].get('email')
            firstname = request.session['businessaccount'].get('users_lists')[indx].get('firstName')
            middlename = request.session['businessaccount'].get('users_lists')[indx].get('middleName') if request.session['businessaccount'].get('users_lists')[indx].get('middleName') else ""
            lastname = request.session['businessaccount'].get('users_lists')[indx].get('lastName')
            primary_currency = request.session['businessaccount'].get('primaryCurrency')
            secondary_currency = request.session['businessaccount'].get('secondaryCurrency')
            full_name = f"{firstname} {middlename} {lastname}"
            password = User.objects.make_random_password()
            usr_name = randomword(13)
            while True:
                if User.objects.filter(username=usr_name).exists():
                    usr_name = randomword(13)
                else:
                    break
            user = User.objects.create_user(username=usr_name,email=user_email,password=password)
            customer,status = Customers.objects.get_or_create(user=user,customertype=2,agreetermsandconditions=True,
                                createdby=user,isactive=True,ubo_customer = True)
            useraccount,status = Useraccounts.objects.get_or_create(customer=customer,firstname=firstname,middlename=middlename,
                                    lastname=lastname,
                                    # phonenumber=str(request.session['businessaccount'].get('countryCode'))+"-"+str(request.session['businessaccount'].get('phoneNo')),
                                    ultimate_ben_user=True ,createdby=customer,added_by=customer
                                    )
            business_transaction_authority = Businesstransactionauthorities.objects.get_or_create(
                useraccount=useraccount,transactionauthoritytype=Transactionauthoritytypes.objects.get(id=int(request.session['businessaccount'].get('users_lists')[indx].get('userType'))),
                createdby=user
                )  
            business_details = Businessdetails.objects.get_or_create(
                customer=customer,companyname=request.session['businessaccount'].get('companyName'),
                industrytype = Industrytypes.objects.get(name=request.session['businessaccount'].get('industryType')),
                url = request.session['businessaccount'].get('companyUrl'),
                emailaddress = user_email,
                phonenumber=request.session['businessaccount'].get('phoneNo'),
                countrycode=request.session['businessaccount'].get('countryCode'),
                address=request.session['businessaccount'].get('address'),
                country = request.session['businessaccount'].get('country'),createdby=user,
                city = request.session['businessaccount'].get('city'),
                state = request.session['businessaccount'].get('state')
            )
            for currency in [primary_currency,secondary_currency]:
                accountno_list = list(map(int, list(Accounts.objects.filter(user_account__ismaster_account=False).order_by('-accountno').values_list('accountno', flat=True))))
                accountno_list.sort(reverse = True)
                account,status = Accounts.objects.get_or_create(user_account=useraccount,accountno=int(accountno_list[0]) + 1 if accountno_list else settings.DEFAULT_ADD,
                            currency=Currencies.objects.get(code=currency),accounttype=1,isprimary=1 if currency==primary_currency else 2,createdby=user)
            
            mail_status = self.send_confirm_mail(full_name, user_email,createdby=user,transaction_type=1, dev_type=1)                   
            for user_each in users_lists:
                if users_lists.index(user_each) != indx:
                    usr_name = randomword(13)
                    while True:
                        if User.objects.filter(username=usr_name).exists():
                            usr_name = randomword(13)
                        else:
                            break
                    user_sub=User.objects.create_user(username=usr_name,email=user_each.get('email'),password=password)
                    customer_each,status = Customers.objects.get_or_create(user=user_sub,customertype=2,agreetermsandconditions=True,createdby=user,isactive=True)
                    
                    useraccount_each,status = Useraccounts.objects.get_or_create(customer=customer_each,firstname=user_each.get('firstName'),
                                middlename=user_each.get('middleName'),
                                lastname=user_each.get('lastName'),
                                added_by=customer,createdby=customer
                                )

                    business_transaction_authority_each = Businesstransactionauthorities.objects.get_or_create(
                        useraccount=useraccount_each,transactionauthoritytype=Transactionauthoritytypes.objects.get(id=int(user_each.get('userType'))),
                        createdby=user
                        )  

                    business_details = Businessdetails.objects.get_or_create(
                        customer=customer_each,companyname=request.session['businessaccount'].get('companyName'),
                        industrytype = Industrytypes.objects.get(name=request.session['businessaccount'].get('industryType')),
                        url = request.session['businessaccount'].get('companyUrl'),
                        emailaddress = user_email,
                        phonenumber=request.session['businessaccount'].get('phoneNo'),
                        countrycode=request.session['businessaccount'].get('countryCode'),
                        address=request.session['businessaccount'].get('address'),
                        country = request.session['businessaccount'].get('country'),createdby=user,
                        city = request.session['businessaccount'].get('city'),
                        state = request.session['businessaccount'].get('state')
                        ) 
                    firstname_each=user_each.get('firstName')
                    middlename_each=user_each.get('middleName')
                    lastname_each=user_each.get('lastName')
                    user_email_each=user_each.get('email')
                    full_name_each=f"{firstname_each} {middlename_each} {lastname_each}"
                    mail_status = self.send_confirm_mail(full_name_each, user_email_each,createdby=user_sub,transaction_type=1, dev_type=1)                  
                else:
                    pass
            try:
                primary_account = f"{useraccount.accnt_usr_accnt.all()[0].accountno} {useraccount.accnt_usr_accnt.all()[0].currency.code}"
                secondary_account = f"{useraccount.accnt_usr_accnt.all()[1].accountno} {useraccount.accnt_usr_accnt.all()[1].currency.code}"
            except Exception as e:
                primary_account = ""
                secondary_account = ""
                logger.info(f"Error in fetching account details->{e}")
            add_log_action(request, useraccount, status=f'Business account UBO({user_email}) has been created with accounts {primary_account} and {secondary_account}', status_id=1,user_id=user.id)
            del request.session['businessaccount']
            return render(request,'accounts/openaccount/personal-signup/signup-success.html')
        else:
            return redirect('business-account-registration')

@method_decorator(login_required, name='dispatch')
class CompanyDetailsView(View,OTP):
    def get(self,request):
        business_details = Businessdetails.objects.get(customer__user = request.user,isdeleted=False)
        country = Countries.objects.get(shortform=business_details.country)
        user_details=Useraccounts.objects.get(customer__user = request.user)
        country_of_incorporation=Countries.objects.get(shortform=business_details.country).name
        context={
            'business_details':business_details,
            'country':country,
            'city':user_details.city,
            'state':user_details.region,
            'country_of_incorporation':country_of_incorporation
            }
        
        if request.session.get('company_doc_edit_success_message'):
            message = request.session.get('company_doc_edit_success_message')
            context.update({
                'message':message,
                'status':request.session.get('status')
            })
            del request.session['company_doc_edit_success_message']
            del request.session['status']
        else:
            pass
        return render(request,'accounts/openaccount/business/company_details.html',context)
    def post(self,request):
        token = ''.join(
            random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(100))
        request.session['edit_company_details_token'] = token
        request.session['otp_send_message'] = 'OTP sent, Please verify!'
        user_account = Useraccounts.objects.get(customer__user=request.user)
        full_name = f"{user_account.firstname} {user_account.lastname}"
        self.send_email_otp(transaction_type=8, created_by=request.user, email=request.user.email, full_name=full_name, token=token, activation_code=None)
        return redirect('/verifyOTP')

@method_decorator(login_required, name='dispatch')
class EditCompanyDetailsView(View):
    def get(self,request):
        industries = Industrytypes.objects.filter(isdeleted=False)
        countries = Countries.objects.all()
        businessdetails = Businessdetails.objects.get(customer__user=request.user)
        useraccount = Useraccounts.objects.get(customer__user=request.user)
        country_code = Countries.objects.get(shortform=businessdetails.country).phonecode
        phonenumber=businessdetails.phonenumber
        context={
            'industries':industries,
            'countries':countries,
            'businessdetails':businessdetails,
            'useraccount':useraccount,
            'country_code':country_code,
            'phonenumber': phonenumber,
        }
        return render(request, 'accounts/openaccount/business/edit_company_details.html', context)
    def post(self,request):
        if request.session.get('companydetails'):
            del request.session['companydetails']
        request.session['companydetails'] = request.POST.dict()
        return redirect(f'/settings/companydetails/confirm/?accessToken={request.session["edit_company_details_token"]}')

@method_decorator(login_required, name='dispatch')
class ConfirmCompanyDetailsView(View):
    def get(self,request):
        if request.GET.get("accessToken") == request.session.get('edit_company_details_token'):
            industry_type = Industrytypes.objects.get(id=request.session['companydetails'].get('industryType'))
            country_of_incorporation = Countries.objects.get(shortform=request.session['companydetails'].get('countryOfIncorportaion'))
            context={
                'industry_type':industry_type.name,
                'country_of_incorporation':country_of_incorporation.name
            }
            return render(request, 'accounts/openaccount/business/confirm-company-details.html',context)
        else:
            return redirect('company-details-edit')
    def post(self,request):
        try:
            Businessdetails.objects.filter(id=request.session['companydetails'].get('id')).update(
                companyname=request.POST.get('companyName'),
                industrytype=Industrytypes.objects.get(name=request.POST.get('industryType')),
                url=request.POST.get('url'),
                address=request.POST.get('address'),
                phonenumber=request.session['companydetails']['phonenumber'],
                countrycode=request.session['companydetails']['countrycode'],
                country=Countries.objects.get(name=request.POST.get('countryOfIncorportaion')).shortform,
                city=request.POST.get('city'),
                state=request.POST.get('region')
                    )
   
            request.session['status'] = True
            request.session['company_doc_edit_success_message'] = "Updated successfully"
            if request.session.get('edit_company_details_token'):
                del request.session['edit_company_details_token']
            return redirect('company-details')
        except Exception as e:
            logger.info(e)
            request.session['status'] = False
            request.session['company_doc_edit_success_message'] = "Company details cann't be updated"
            return redirect('company-details-edit')
        
@method_decorator(login_required, name='dispatch')
class ViewUsers(View):
    def get(self,request):
        user_details=[]
        businessdetails = Businessdetails.objects.get(customer__user=request.user)
        matching_business_details = Businessdetails.objects.filter(companyname=businessdetails.companyname,
                url=businessdetails.url)
        for matching_business_detail in matching_business_details:
            user_details.append(Useraccounts.objects.get(customer = matching_business_detail.customer))   
        transactionauthoritytypes = Businesstransactionauthorities.objects.all()
        context = {
            'user_details':user_details,
            'transactionauthoritytypes':transactionauthoritytypes
        }
        if request.session.get('err-message'):
            message = request.session.get('err-message')
            status = request.session.get('status')
            del request.session['err-message']
            del request.session['status']
            context.update(
                {
                    'message' : message,
                    'status' : status
                }
            )
        else:
            pass
        return render(request,'accounts/openaccount/business/view-users.html',context)

@method_decorator(login_required, name='dispatch')
class ViewUserDetails(View):
    def post(self,request):
        user_account = Useraccounts.objects.get(id=request.POST.get('user-id'))
        transactionauthoritytype = Businesstransactionauthorities.objects.get(useraccount=user_account)
        context={
            'user_account' : user_account,
            'transactionauthoritytype' : transactionauthoritytype
        }
        return render (request,'accounts/openaccount/business/view-user-details.html',context)

@method_decorator(login_required, name='dispatch')
class AddMoreUser(View,ConfirmYourMail):
    def post(self,request):
        if request.POST.get('action')=='add':
            authority_types = Transactionauthoritytypes.objects.filter(isdeleted=False)
            context={
                'authority_types' : authority_types
            }
            return render(request,'accounts/openaccount/business/add-more-user.html',context)
        else:
            firstname=request.POST.get('firstName')
            middlename=request.POST.get('middleName')
            lastname=request.POST.get('lastName')
            user_email = request.POST.get('email')
            password = User.objects.make_random_password()
            if User.objects.filter(email=user_email).exists():
                request.session['err-message'] = "Email already exists"
                request.session['status'] = False
            else:  
                usr_name = randomword(13)
                while True:
                    if User.objects.filter(username=usr_name).exists():
                        usr_name = randomword(13)
                    else:
                        break
                user = User.objects.create_user(username=usr_name,email=user_email,password=password)
                customer,status = Customers.objects.get_or_create(user=user,customertype=2,agreetermsandconditions=True,
                    createdby=request.user,isactive=True,
                    ubo_customer = True if request.POST.get('mainBusinessownernew') == 'on' else False,
                    )
                current_user_added_by = Useraccounts.objects.get(customer__user=request.user).added_by
                useraccount_each,status = Useraccounts.objects.get_or_create(customer=customer,firstname=request.POST.get('firstName'),
                        middlename=request.POST.get('middleName'),
                        lastname=request.POST.get('lastName'),
                        added_by=Useraccounts.objects.get(customer__user=request.user).added_by,
                        ultimate_ben_user = True if request.POST.get('mainBusinessownernew') == 'on' else False,
                        )
                business_transaction_authority_each = Businesstransactionauthorities.objects.get_or_create(
                        useraccount=useraccount_each,transactionauthoritytype=Transactionauthoritytypes.objects.get(id=int(request.POST.get('userType')))
                        )
                ubo_user = Useraccounts.objects.get(customer__user = request.user)
                business_details = Businessdetails.objects.get(customer__user = request.user)

                business_details_new_user = Businessdetails.objects.get_or_create(
                            customer=customer,companyname=business_details.companyname,
                            industrytype=business_details.industrytype,
                            url=business_details.url,
                            emailaddress=business_details.emailaddress,
                            phonenumber=business_details.phonenumber,
                            countrycode=business_details.countrycode,
                            address=business_details.address,country=business_details.country,
                            city = business_details.city, state = business_details.state
                        )
                
                full_name = f"{firstname} {middlename} {lastname}"
                password = User.objects.make_random_password()
                mail_status = self.send_confirm_mail(full_name, user_email,createdby=user,transaction_type=1, dev_type=1)
                try:
                    customer_doc_current = Customerdocuments.objects.filter(customer__user=request.user,verificationtype__verificationtype=3).first()
                    customer_doc_details_current1 = Customerdocumentdetails.objects.filter(customerdocument=customer_doc_current,
                                field = Documentfields.objects.get(fieldtype='2',documenttype__description="Company registration document")).first()

                    customer_doc_details_current2 = Customerdocumentdetails.objects.filter(customerdocument=customer_doc_current,
                                    field = Documentfields.objects.get(fieldtype='5',documenttype__description="Company registration document")).first()

                    customer_doc_file_current = Customerdocumentfiles.objects.filter(customerdocument=customer_doc_current).first()
                    
                    customer_doc = Customerdocuments.objects.create(
                                    customer=customer,verificationtype=customer_doc_current.verificationtype,
                                    documenttype = customer_doc_current.documenttype
                                    )
                    customer_document_details1 = Customerdocumentdetails.objects.create(
                                        customerdocument=customer_doc,value=customer_doc_details_current1.value,
                                        field = Documentfields.objects.get(fieldtype='2',documenttype__description="Company registration document"),

                                    )
                    customer_document_details2 = Customerdocumentdetails.objects.create(
                                        customerdocument=customer_doc,value=customer_doc_details_current2.value,
                                        field = Documentfields.objects.get(fieldtype='5',documenttype__description="Company registration document"),

                                    )
                    customer_files = Customerdocumentfiles.objects.create(
                                        customerdocument=customer_doc,filelocation=customer_doc_file_current.filelocation
                                    )
                except:
                    pass

                request.session['err-message'] = "Updated successfully"
                request.session['status'] = True
            return redirect("/settings/users")


@method_decorator(login_required, name='dispatch')
class Dactivateaccount(View):
    def post(self,request):
        if request.POST.get('type')=='deactivate':
            account_id = request.POST.get('account_id')
            user_account = Useraccounts.objects.filter(id=account_id).update(
                activestatus="Deactivated by UBO"
            )
            data={'user_account':user_account}
            return JsonResponse(data,status=200)
        elif request.POST.get('type')=='check-account-verified':
            ubo_account = Useraccounts.objects.get(customer__user=request.user)
            check_verification = ubo_account.activestatus
            if check_verification=="Not Verified":
                data={
                    'ver_status': False
                }
            else:
                data={
                    'ver_status': True
                }
            return JsonResponse(data,status=200)
        elif request.POST.get('type')=='allow_transactions':
            ubo_account = Useraccounts.objects.get(id=request.POST.get('ubo_acc_id'))
            user_account = Useraccounts.objects.get(id=request.POST.get('account_id'))
            user_account.account_tran_status = True
            user_account.save()
            data={'user_account_status':True}
            return JsonResponse(data,status=200)
        elif request.POST.get('type')=='restrict_transactions':
            ubo_account = Useraccounts.objects.get(id=request.POST.get('ubo_acc_id'))
            user_account = Useraccounts.objects.get(id=request.POST.get('account_id'))
            user_account.account_tran_status = False
            user_account.save()
            data={'user_account_status':False}
            return JsonResponse(data,status=200)

@method_decorator(login_required, name='dispatch')
class PermissionEmail(View,PermissionEmail):
    def post(self,request):
        if request.POST.get("type")=='send-permission-req-mail':
            current_user_email = request.user.email
            user_account = Useraccounts.objects.get(customer__user=request.user)
            company = Businessdetails.objects.get(customer__user=request.user)
            all_companies = list(Businessdetails.objects.filter(companyname=company.companyname,url=company.url))
            to_email_list=[]
            for company in all_companies:
                user_account = Useraccounts.objects.get(customer=company.customer)
                if user_account.ultimate_ben_user:
                    to_email_list.append(user_account.customer.user.email)
            # addedby = user_account.added_by
            # recepient_ubo_email = addedby.user.email
            send_email = self.send_email_permission(to_email_list,current_user_email)
            response={
                'title':request.POST.get('title'),
                'message' : 'Mail successfully sent to Ultimate Beneficial Owner.',
                'status':True
            }
            return JsonResponse(response,status=200)
            


        