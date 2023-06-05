import datetime
import json
import random
import string
import re
from calendar import monthrange
from django.http import  JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from django.conf import settings
# Create your views here.
from django.views import View
from django.utils.crypto import get_random_string


from Transactions.mixins import OTP, ConfirmYourMail, CustomMail, checkNonAsciiChracters, randomword
from UserDetails.forms import UserDetailsForm
from utils.models import Useraccounts, Countries, Otps, Apiaccesskeygenerate, APIaccessToken
import logging
logger = logging.getLogger('lessons')


@method_decorator(login_required, name='dispatch')
class PersonalDetailsView(View,OTP):
    def get(self, request):
        context = {}
        user_account = Useraccounts.objects.get(customer__user=request.user)
        context['user_account'] = user_account
        if request.session.get("doc_edit_success_message"):
            context['status'] = request.session.get("status")
            context['message'] = request.session.get("doc_edit_success_message")
            del request.session["doc_edit_success_message"]
            del request.session["status"]
        if request.session.get('personal_details'):
            del request.session["personal_details"]
        if request.session.get('confirm_edit_details'):
            del request.session["confirm_edit_details"]
        return render(request, 'userdetails/personaldetails/show-details.html', context)

    def post(self, request):
        token = ''.join(
            random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(100))
        request.session['edit_doc_token'] = token
        request.session['otp_send_message'] = 'OTP sent, Please verify!'
        user_account = Useraccounts.objects.get(customer__user=request.user)
        full_name = f"{user_account.firstname} {user_account.lastname}"
        if request.session.get("mob_verification_token"):
            del request.session['mob_verification_token']
        return redirect('/verifyOTP')


@method_decorator(login_required, name='dispatch')
class OTPVerifyView(View,OTP):
    def get(self, request):
        context = {}
        user_account = Useraccounts.objects.get(customer__user=request.user)
        context['user_account'] = user_account
        context['status'] = True
        if request.session.get('otp_send_message'):
            context['message'] = request.session.get('otp_send_message')
            del request.session['otp_send_message']
        return render(request, 'common/otpverify.html', context)

    def post(self, request):
        context = {}
        otp = request.POST.get("otp")
        context['status'] = True
        if request.session.get('mob_verification_token'):
            token = request.session.get('mob_verification_token')
            transactiontype = "MobileNumber Verification"
            transactiontype_index = 1
            next_page = '/'
        elif request.session.get('edit_company_details_token'):
            token = request.session.get('edit_company_details_token')
            transactiontype = "Update Company Details"
            transactiontype_index = 8
            next_page = f"/settings/companydetails/edit/?accessToken={token}"
        else:
            token = request.session.get('edit_doc_token')
            transactiontype = "Update User Details"
            transactiontype_index = 7
            next_page = f"/settings/personal/edit/?accessToken={token}"
        if request.POST.get("action") == "resend":
            try:
                user = request.user
                user_account = Useraccounts.objects.get(customer__user=user)
                full_name = f"{user_account.firstname} {user_account.lastname}"

                context['status'] = True
                context['message'] = 'OTP resent, Please verify!'
            except Exception as e:
                logger.info(e)
                context['status'] = False
                context['message'] = 'Something went wrong! Please try again.'
            return render(request, 'common/otpverify.html', context)
        try:
            otp_obj = Otps.objects.get(code=otp,token=token,transactiontype=transactiontype,
                             createdby=request.user)
            if not otp_obj.validated:
                if otp_obj.validtill >= datetime.datetime.now().date():
                    otp_obj.validated = True
                    otp_obj.save()
                    if request.session.get('mob_verification_token'):
                        try:
                            user_account = Useraccounts.objects.get(customer__user=request.user)
                            user_account.phoneverified = True
                            user_account.save()
                            del request.session['mob_verification_token']
                        except Exception as e:
                            logger.info(e)
                            pass
                    request.session['otp_success_message'] = "OTP Verified!"
                    return redirect(next_page)
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
        user_account = Useraccounts.objects.get(customer__user=request.user)
        context['user_account'] = user_account
        return render(request, 'common/otpverify.html', context)


@method_decorator(login_required, name='dispatch')
class EditPersonalDetailsView(View):
    def get(self, request):
        year = datetime.datetime.today().year
        year_choices = list(range(year-16, year - 125, -1))
        months_choices = []
        for i in range(1,13):
            months_choices.append(datetime.date(2022, i, 1).strftime('%B'))
        day_choices = []
        for day in range(1,(monthrange(2022, 3)[1])+1):
            day_choices.append(day)
        if request.GET.get("accessToken") == request.session['edit_doc_token']:
            if not request.session.get('confirm_edit_details'):
                user_account = Useraccounts.objects.get(customer__user=request.user)
                context = {'id': user_account.id, 'firstname': user_account.firstname,
                           'middlename': user_account.middlename,
                           'lastname': user_account.lastname, 'email': user_account.customer.user.email,
                           'dateofbirth': user_account.dateofbirth, 'street_address': user_account.street_address,
                           'city': user_account.city, 'region': user_account.region, 'zipcode': user_account.zipcode,
                           'phonenumber': user_account.phonenumber, 'user_account': user_account,
                           'country': user_account.country.id if user_account.country else None,
                           'nationality': user_account.nationality.id if user_account.nationality else None,
                           'countrycode': user_account.countrycode,
                           'countries': Countries.objects.all().order_by('name'),
                           'is_not_edit':True
                           }
            else:
                context = json.loads(request.session['confirm_edit_details'])
                context['country'] = int(context['country']) if context['country'] else None
                if request.POST.get('month') and request.POST.get('year') and request.POST.get('day'):
                    datetime_object = datetime.datetime.strptime(context.get('month'), "%B")
                    month_number = str(datetime_object.month)
                    dateofbirth = f"{context.get('day')}-{month_number}-{context.get('year')}"
                    context['dateofbirth'] = dateofbirth
                user_account = Useraccounts.objects.get(customer__user=request.user)
                if user_account.dateofbirth:
                    context['dateofbirth'] = user_account.dateofbirth
                    context['is_not_edit'] = True
                context['countries'] = Countries.objects.all().order_by('name')
            if request.session.get("otp_success_message"):
                context['status'] = True
                context['message'] = request.session.get("otp_success_message")
                del request.session["otp_success_message"]
            context['year_choices'] = year_choices
            context['months_choices'] = months_choices
            context['day_choices'] = day_choices
            return render(request, 'userdetails/personaldetails/edit-details.html', context)
        else:
            return redirect("/")

    def post(self, request):
        instance = get_object_or_404(Useraccounts, id=request.POST.get('id'))
        form = UserDetailsForm(request.POST, instance=instance)
        context = json.loads(json.dumps(request.POST))
        if request.POST.get("nationality"):
            context['nationality'] = int(request.POST.get("nationality")) if request.POST.get("nationality") else None
        else:
            context['nationality'] = instance.nationality.id if instance and instance.nationality else None
        context['id'] = request.POST.get('id')
        context['firstname'] = instance.firstname
        context['lastname'] = instance.lastname
        context['middlename'] = instance.middlename
        context['email'] = request.user.email
        if request.POST.get('month') and request.POST.get('year') and request.POST.get('day'):
            datetime_object = datetime.datetime.strptime(request.POST.get('month'), "%B")
            month_number = str(datetime_object.month)
            dateofbirth = f"{request.POST.get('day')}-{month_number}-{request.POST.get('year')}"
            context['dateofbirth'] = dateofbirth
            dateofbirth_to_db = f"{request.POST.get('year')}-{month_number}-{request.POST.get('day')}"
            context['dateofbirth_to_db'] = dateofbirth_to_db
        request.session['confirm_edit_details'] = json.dumps(context)
        context['form'] = form
        if not request.POST.get('month') and not request.POST.get('year') and not request.POST.get('day'):
            context['dateofbirth'] = datetime.datetime.strptime(request.POST.get("dateofbirth"), "%Y-%m-%d")
        context['countries'] = Countries.objects.all().order_by('name')
        if form.is_valid():
            return redirect(f'/settings/personal/confirm/?accessToken={request.session["edit_doc_token"]}')
        year = datetime.datetime.today().year
        year_choices = list(range(year-16, year - 125, -1))
        months_choices = []
        for i in range(1,13):
            months_choices.append(datetime.date(2022, i, 1).strftime('%B'))
        day_choices = []
        for day in range(1,(monthrange(2022, 3)[1])+1):
            day_choices.append(day)
        context['year_choices'] = year_choices
        context['months_choices'] = months_choices
        context['day_choices'] = day_choices
        try:
            if instance.dateofbirth:
                context['is_not_edit'] = True
        except Exception as e:
            logger.info(e)
        return render(request, 'userdetails/personaldetails/edit-details.html', context)


@method_decorator(login_required, name='dispatch')
class ConfirmEditDetailsView(View):
    def get(self, request):
        if request.GET.get("accessToken") == request.session.get('edit_doc_token') or request.session.get('initial'):
            if request.session.get('personal_details'):
                user_data = request.session.get('personal_details')
                dateofbirth = datetime.datetime.strptime(request.session['personal_details']['dateofbirth'], "%d-%m-%Y")
            else:
                user_data = json.loads(request.session['confirm_edit_details'])
                if user_data.get('month') and user_data.get('year') and user_data.get('day'):
                    dateofbirth = datetime.datetime.strptime(user_data.get('dateofbirth'), "%d-%m-%Y")
                else:
                    dateofbirth = datetime.datetime.strptime(user_data.get('dateofbirth'), "%Y-%m-%d")
            country = Countries.objects.get(id=user_data.get('country')).name if Countries.objects.filter(id=user_data.get('country')) else None
            nationality = Countries.objects.get(id=user_data.get('nationality')).name if Countries.objects.filter(id=user_data.get('nationality')) else None
            context = {'firstname': user_data.get('firstname'), 'middlename': user_data.get('middlename'),
                       'lastname': user_data.get('lastname'), 'email': user_data.get('email'),
                       'dateofbirth': dateofbirth, 'street_address': user_data.get('street_address'),
                       'city': user_data.get('city'), 'region': user_data.get('region'),
                       'zipcode': user_data.get('zipcode'),
                       'phonenumber': user_data.get('phonenumber'), 'user_account': user_data.get('user_account'),
                       'country': country,
                       'nationality': nationality,
                       'countrycode': user_data.get('countrycode')}

            if request.session.get("otp_success_message"):
                context['status'] = True
                context['message'] = request.session.get("otp_success_message")
                del request.session["otp_success_message"]
            if request.session.get('personal_details'):
                return render(request, 'accounts/openaccount/personal-signup/personal-confirm-details.html', context)
            return render(request, 'userdetails/personaldetails/confirm-details.html', context)
        else:
            return redirect("/")

    def post(self, request):
        if request.POST.get("action") and request.POST.get("action") == "goto_edit":
            if request.session.get('personal_details'):
                return redirect('/pageStatus/?page=1')
            return redirect(f"/settings/personal/edit/?accessToken={request.session['edit_doc_token']}")
        if not request.session.get('confirm_edit_details') and not request.session.get('personal_details'):
            request.session['status'] = False
            request.session['doc_edit_success_message'] = "Something went wrong! Please try again."
            return redirect('/settings/personal')
        if request.session.get('confirm_edit_details'):
            user_data = json.loads(request.session['confirm_edit_details'])
        elif request.session.get('personal_details'):
            user_data = request.session['personal_details']
        instance = Useraccounts.objects.get(id=user_data.get('id')) if Useraccounts.objects.filter(id=user_data.get('id')) else None
        if instance:
            if instance.phonenumber != user_data.get('phonenumber'):
                instance.phoneverified = False
                instance.save()
            form = UserDetailsForm(user_data, instance=instance)
            if form.is_valid():
                form_save = form.save(commit=False)
                form_save.country = Countries.objects.get(id=user_data.get('country')) if Countries.objects.filter(id=user_data.get('country')) else None
                if user_data.get('nationality'):
                    form_save.nationality = Countries.objects.get(
                        id=user_data.get('nationality')) if Countries.objects.filter(
                        id=user_data.get('nationality')) else None
                if user_data.get('dateofbirth_to_db'):
                    form_save.dateofbirth = user_data.get('dateofbirth_to_db')
                form_save.save()
                if request.session.get('personal_details'):
                    form_save.dateofbirth = user_data.get('dateofbirth_to_db')
                    form_save.save()
                    return redirect('/pageStatus/?page=2')
                request.session['status'] = True
                request.session['doc_edit_success_message'] = "Updated successfully"
                del request.session['confirm_edit_details']
                return redirect('/settings/personal')


@method_decorator(login_required, name='dispatch')
class EditTwoFactorAuthenticationView(View):
    def get(self,request):
        context = {}
        return render(request, 'userdetails/2FA/edit-2FA.html', context)

    def post(self,request):
        tf_status = request.POST.get("tf_status")
        context = {}
        try:
            user_account = Useraccounts.objects.get(customer__user=request.user)
            if tf_status == "1":
                user_account.twofactorauth = True
            else:
                user_account.twofactorauth = False
            user_account.save()
            message = "Successfully Saved!"
            status = True
        except Exception as e:
            logger.info(e)
            message = "User details not found"
            status = False
        context['message'] = message
        context['status'] = status
        return render(request, 'userdetails/2FA/edit-2FA.html', context)


@method_decorator(login_required, name='dispatch')
class EditOTPMethodView(View):
    def get(self,request):
        context = {}

        return render(request, 'userdetails/OTP_method/edit-otp_method.html', context)

    def post(self,request):
        otp_method = request.POST.get("otp_method")
        context = {}
        try:
            user_account = Useraccounts.objects.get(customer__user=request.user)
            if str(otp_method) in ["1","2"]:
                user_account.otptype = int(otp_method)
                user_account.save()
                message = "Successfully Saved!"
                status = True
            else:
                message = "Invalid option!"
                status = False
        except Exception as e:
            logger.info(e)
            message = "User details not found"
            status = False
        context['message'] = message
        context['status'] = status
        return render(request, 'userdetails/OTP_method/edit-otp_method.html', context)


@method_decorator(login_required, name='dispatch')
class ChangePassword(View):
    def get(self,request):
        if request.GET.get('OTP') == 'True':
            context = {}
            if request.session.get('changepassword_details'):
                context = json.loads(request.session.get('changepassword_details'))
                del request.session['changepassword_details']
            return render(request, 'userdetails/changePassword/change-password-otp.html', context)
        else:
            if request.session.get('changepassword'):
                del request.session['changepassword']
            if request.session.get('prevPasswordToken'):
                del request.session['prevPasswordToken']
            if request.session.get('changepassword_details'):
                del request.session['changepassword_details']
            if request.session.get('user_cred'):
                del request.session['user_cred']
            token = ''.join(
                random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(100))
            request.session['changepassword'] = token
            return render(request, 'userdetails/changePassword/change-password.html')
        
    def post(self,request):
        user_account = Useraccounts.objects.get(customer__user=request.user)
        full_name = f"{user_account.firstname} {user_account.lastname}"
        if request.POST.get('action_type') == 'otp_verfy':
            def opt_validate():
                if request.session.get('changepassword'):
                    try:
                        otp = Otps.objects.get(code=request.POST.get('otp'),
                                        transactiontype='Change Password',
                                        validated=False,
                                        createdby=request.user,token=request.session['prevPasswordToken'],isdeleted=False)
                    except Exception as e:
                        logger.info(e)
                        return {
                            'status' : False,
                            'message' : "Verification failed, wrong user or otp"
                        }
                    valid_till = datetime.datetime.now()
                    valid_till = valid_till.date().strftime(settings.DATE_FORMAT)
                    valid_date = datetime.datetime.strptime(valid_till, settings.DATE_FORMAT)
                    if valid_date.date() <= otp.validtill:
                        otp.validated = True
                        otp.save()
                    else:
                        return {
                            'status' : False,
                            'message' : 'Verification failed, expired otp'
                        }
                    data = {}
                    if request.session.get('user_cred'):
                        user_cred = json.loads(request.session.get('user_cred'))
                        del request.session['user_cred']
                        data = {
                            'old_password' : user_cred['oldpassword'],
                            'new_password1' : user_cred['newpassword'],
                            'new_password2' : user_cred['confirmpassword']
                        }
                    form = PasswordChangeForm(request.user, data)
                    if form.is_valid():
                        user = form.save()
                        update_session_auth_hash(request, user)  # Important!
                        return {
                            'status' : True,
                            'message' : 'Your password was successfully updated!'
                        }
                    else:
                        return {
                            'status' : False,
                            'message' : 'something went wrong'
                        }
                else:
                    return {
                            'status' : False,
                            'message' : 'Verification failed, wrong user or otp'
                        }
            response = opt_validate()
            if response and not response.get('status'):
                context = {
                    'message' : response.get('message'),
                    'status' : False,
                }
                return render(request, 'userdetails/changePassword/change-password-otp.html', context)
            elif response.get('status'):
                context = {
                    'message' : response.get('message'),
                    'status' : True,
                }
                return render(request, 'userdetails/changePassword/change-password.html', context)
            
        elif request.POST.get('action_type') == 'resent otp':
            otp_status=OTP()
            if otp_status:
                if request.session.get('prevPasswordToken'):
                    del request.session['prevPasswordToken']
                request.session['prevPasswordToken'] = request.session.get('changepassword')
                del request.session['changepassword']
                token = ''.join(
                random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(100))
                request.session['changepassword'] = token
                return JsonResponse({
                    'message' : 'OTP sent, Please verify!'
                    })
            else:
                return JsonResponse({
                    'message' : 'Error while sending OTP!'
                    })
        else:
            if request.session.get('changepassword'):
                
                oldpassword = request.POST.get('oldpassword').strip()
                newpassword = request.POST.get('password').strip()
                confirmpassword = request.POST.get('confirmPassword').strip()
                def validate():
                    if not oldpassword:
                        return {
                            'status' : False,
                            'message' : "Please enter current password"
                        }
                    elif not newpassword:
                        return {
                            'status' : False,
                            'message' : "Please enter new password"
                        }
                    elif not confirmpassword:
                        return {
                            'status' : False,
                            'message' : "Please re-enter new password"
                        }
                    elif not check_password(oldpassword,request.user.password):
                        return {
                            'status' : False,
                            'message' : "Current password is invalid!"
                        }
                    elif newpassword != confirmpassword:
                        return {
                            'status' : False,
                            'message' : "Your passwords does not match"
                        }
                    elif (len(newpassword)<10 or len(newpassword)>50):
                        return {
                        'status' : False,
                        'message' : f"New password not valid ! Total characters should be between 10 and 50"
                        }
                    elif not re.search("[A-Z]",newpassword):
                        return {
                        'status' : False,
                        'message' : f"New password not valid ! It should contain one letter between [A-Z]"
                        }
                    elif not re.search("[a-z]",newpassword):
                        return {
                        'status' : False,
                        'message' : f"New password not valid ! It should contain one letter between [a-z]"
                        }
                    elif not re.search("[1-9]",newpassword):
                        return {
                        'status' : False,
                        'message' : f"New password not valid ! It should contain one letter between [1-9]"
                        }
                    elif not re.search("[~!@#$%^&*]",newpassword):
                        return {
                        'status' : False,
                        'message' : f"New password not valid ! It should contain at least one letter in [~!@#$%^&*]"
                        }
                    elif re.search("[\s]",newpassword):
                        return {
                        'status' : False,
                        'message' : f"New password not valid ! It should not contain any space"
                        }
                    else:
                        return {
                            'status' : True,
                            'message' : f"Password changed successfully"
                        }
                response = validate()
                if response and not response.get('status'):
                    context = {
                        'message' : response.get('message'),
                        'status' : False,
                        'oldpassword' :oldpassword if oldpassword else '' ,
                        'password' :newpassword if newpassword else '' ,
                        'confirmPassword' :confirmpassword if confirmpassword else '' ,
                    }
                    return render(request, 'userdetails/changePassword/change-password.html', context)
                elif response.get('status'):
                    otp_status=OTP()
                    if otp_status:
                        if request.session.get('prevPasswordToken'):
                            del request.session['prevPasswordToken']
                        request.session['prevPasswordToken'] = request.session.get('changepassword')
                        del request.session['changepassword']
                        token = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(100))
                        request.session['changepassword'] = token
                        context = {
                        'message' : 'OTP sent successfully',
                        'status' : True,
                        'user_email' : request.user.email ,
                        }
                        data = {
                        'oldpassword' :oldpassword ,
                        'newpassword' :newpassword,
                        'confirmpassword' :confirmpassword,
                        }
                        request.session['user_cred'] = json.dumps(data)
                        request.session['changepassword_details'] = json.dumps(context)
                        return redirect('/settings/changePassword?OTP=True')
                    else:
                        context = {
                        'message' : 'Error while sending OTP!',
                        'status' : False,
                        }
                        return render(request, 'userdetails/changePassword/change-password.html', context)
            else:
                return redirect('/')

@method_decorator(login_required, name='dispatch')
class CancelPasswordChange(View):
    def get(self, request):
        if request.session.get('user_cred'):
            del request.session['user_cred']
        if request.session.get('changepassword_details'):
            del request.session['changepassword_details']
        if request.session.get('prevPasswordToken'):
            del request.session['prevPasswordToken']
        return redirect('/settings/changePassword')

        
            

@method_decorator(login_required, name='dispatch')
class VerificationOTPSendView(View,OTP):
    def post(self,request):
        token = ''.join(
            random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(100))
        request.session['mob_verification_token'] = token
        request.session['otp_send_message'] = 'OTP resent, Please verify!'
        user_account = Useraccounts.objects.get(customer__user=request.user)
        full_name = f"{user_account.firstname} {user_account.lastname}"

        return redirect('/verifyOTP')

class ForgotPassword(View,ConfirmYourMail):
    def get(self, request):
        return render(request,"userdetails/forgotPassword/forgot-password.html")
    def post(self, request):
        email = request.POST.get('Email').strip()

        def validate():
            if not email:
                return {
                    'status': False,
                    'message': 'Email required'
                }
            email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            if email and not re.search(email_regex, email):
                return {
                    'status': False,
                    'message': 'Invalid Email format'
                }
            elif not Useraccounts.objects.filter(customer__user__email=email, isdeleted=False).exists():
                return {
                    'status': False,
                    'message': 'Account Does not exist'
                }
            try:
                user = User.objects.get(email=email)
                user_account = Useraccounts.objects.get(customer__user=user, isdeleted=False)
                full_name = f"{user_account.firstname} {user_account.lastname}"
                mail_status = self.send_confirm_mail(full_name, email,createdby=user,transaction_type=2, dev_type=1)
            except Exception as e:
                logger.info(f"{e}")
                return {
                    'status': False,
                    'message': 'Error Occured'
                }
            return {
                'status': True,
            }
        data = validate()
        if data.get('status'):
            return redirect("/forgotPasswordSuccess")
        else:
            context = request.POST.dict()
            context['status'] = data.get('status')
            context['message'] = data.get('message')
            return render(request,"userdetails/forgotPassword/forgot-password.html",context)

class ForgotPasswordSuccess(View):
    def get(self, request):
        return render(request, "userdetails/forgotPassword/forgot-password-success.html")

@method_decorator(login_required, name='dispatch')
class ReferFriend(View,CustomMail):
    def get(self, request):
        reference_code = randomword(10)
        user_account = Useraccounts.objects.get(customer__user=request.user, isdeleted=False)
        context = {}
        if not user_account.referencecode:
            user_account.referencecode = reference_code
            user_account.save()
        refer_link = f"{settings.CURRENT_DOMAIN}/refer/{user_account.referencecode}"
        context['link'] = refer_link
        return render(request,'userdetails/refer-friend/refer-friend.html',context)
    def post(self, request):
        firstName = request.POST.get('firstName').strip()
        lastName = request.POST.get('lastName').strip()
        email = request.POST.get('email').strip()
        email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        link = request.POST.get('link').strip()
        user_account = Useraccounts.objects.get(customer__user=request.user, isdeleted=False)
        def validate():
            if not firstName:
                return {
                    'status' : False,
                    'message' : 'First name is required'
                }
            elif not lastName:
                return {
                    'status' : False,
                    'message' : 'Last name is required'
                }
            elif not email:
                return {
                    'status' : False,
                    'message' : 'Email is required'
                }
            elif email and not re.search(email_regex, email):
                return {
                    'status': False,
                    'message': 'Invalid Email format'
                }
            elif not checkNonAsciiChracters([firstName,lastName]):
                return {
                    'status': False,
                    'message': 'Fancy characters are not allowed'
                }
            return{
                'status': True,
            }
        data = validate()
        context = {}
        if data.get('status'):
            full_name = f"{firstName} {lastName}"
            subject = 'Invitation from Entrebiz' 
            refer_link = f"{settings.CURRENT_DOMAIN}/refer/{user_account.referencecode}"
            content = f"{refer_link}"
            self.send_refferal_mail(full_name,subject,content,email)
            context['link'] = refer_link
            context['status'] = True
            context['message'] = "Invitation mail sent successfully."
        else:
            context = request.POST.dict()
            context['status'] = False
            context['message'] = data.get('message')
        return render(request,'userdetails/refer-friend/refer-friend.html',context)

@method_decorator(login_required, name='dispatch')
class Referrals(View):
    def get(self, request):
        user_account = Useraccounts.objects.get(customer__user=request.user,isdeleted=False)
        referees = user_account.user_referred_by.filter(isdeleted=False,show_referee=True).order_by('-id')
        context = {
            "referees" : referees
        }
        return render(request,"userdetails/refer-friend/refferals.html",context)
    
class CheckReferCode(View):
    def get(self, request, code):
        try:
            user_account = Useraccounts.active.get(referencecode=code)
            request.session['referFriend'] = { "refferer_id" : user_account.id }
            return redirect("/register/account")
        except Exception as e:
            logger.info(f"{e}")
            return redirect("/")
@method_decorator(login_required, name='dispatch')
class ExternalApiView(View):
    def get(self,request):

        user = request.user
        try:
            apiuser=Apiaccesskeygenerate.objects.get(user=user)
        except:
            apiuser=Apiaccesskeygenerate.objects.create(user=user, apikey=get_random_string(length=109))
        context={'apiuser':apiuser.apikey}

        return render(request,"userdetails/Api/externalapi.html",context)
    def post(self,request):

        user = request.user
        APIaccessToken.objects.filter(user=request.user).delete()
        try:
            apiuser = Apiaccesskeygenerate.objects.get(user=user)
            apiuser.apikey = get_random_string(length=109)
            apiuser.save()
            context = {'apiuser': apiuser.apikey}
        except:
            context = {"error":"Something went wrong"}
            return render(request, "userdetails/Api/externalapi.html", context)


        return render(request,"userdetails/Api/externalapi.html",context)