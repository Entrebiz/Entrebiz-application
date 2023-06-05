import email
from lib2to3.pgen2 import token
from multiprocessing import context
from django.http import JsonResponse
import re
from urllib import response
import stripe
import json
import os
import datetime
from os.path import exists
from pytz import unicode
from decimal import Decimal
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.contrib.auth.hashers import check_password
from Transactions.views import render_pdf
from Transactions.mixins import OTP, ConfirmYourMail, ModelQueries, PermissionEmail, TransactionMail, FindAccount, \
    add_log_action, checkNonAsciiChracters, acc_list, randomword, CustomMail, transaction_lock_fn
from rest_framework import exceptions
from api.v1.mixins import APIV1UtilMixins
from Transactions.mixins import ConfirmYourMail ,randomword
from api.v1.utils.permissions import APIAccessTokenPermissions, TransactionPermission, AccountTransactionPermission, \
    AccountlockedPermissionforextapi, AccountVerifiedPermission

from utils.mixins import UtilMixins
from utils.models import Accounts, Externalbeneficiaries,Businesstransactionauthorities, Countries, Customerdocumentdetails, Customerdocumentfiles, Customerdocuments, Documentfields, Industrytypes, Transactionauthoritytypes, Useraccounts, Transactionpurposetype, Activitylog, Otps, \
    Currencies, Currencyconversionmargins, Currencyconversionratescombined, Transactiontypes, Transactions, \
    Businessdetails, Customers, Internalbeneficiaries, Bankdetail, Receivemoney, InvoiceDocument, Cablecharges, Internationaltransactions, Incomingtracepayment,\
        Stripe_Customer,Stripe_Transaction
from rest_framework import generics
from api.v1.serializers import CompanyPermissionSerializer, IndustrytypesSerializer, UserAuthenticateSerializer, \
    AccountListsSerializer, \
    CurrenciesListSerializer, CountriesListSerializer, TranscationPurposeListSerializer, TwoFactUserAccountSerializer, \
    EditOTPmethodSerializer, ChangePasswordSerializer, MobileOTPmethodSerializer, PersonalDetailSerializer, \
    UserDetailsSerializer, CountryNameSerializer, ForgotPasswordSerializer, CurrencyConversionSerializer, \
    AccountToAccountSerilaizer, AccountToAccountValidateSerilaizer, AccountToAccountEmailSerializer, \
    InwardRemittanceSerializer, InternationalWireTransferSerializer, InwardAccountSerializer, BankdetailSerializer,\
    ReportMissingSerializer, ReportMissingSerializerList, UpdateCurrencyStatusSerializer, ReferfrndSerializer, \
    OTPVerifyPersonalDetailSerializer, TwoStepVerificationSerializer,ImageUploadSerializer,GetaccountSerializer,\
        CheckoutSerializer,International_WireTransfer_Serializer,Currency_ConversionSerializer,Personal_DetailSerializer

from Transactions.accounttoaccount.views import render_pdf as pdf
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.response import Response
from entrebiz import settings
from rest_framework import status
from django.db.models import Q
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
import logging
logger = logging.getLogger('lessons')


class AuthenticateView(APIView,OTP,APIV1UtilMixins):

    def post(self, request):
        request_type = eval(request.data.get("get_user_data")) if request.data.get("get_user_data") else ""
        serializer = UserAuthenticateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        useraccount = get_object_or_404(Useraccounts, customer__user=user)
        token, created = Token.objects.get_or_create(user=user)

        user_nationality=get_object_or_404(Useraccounts, customer__user=user)
        nationalityserilaizer=CountryNameSerializer(user_nationality.nationality)

        if nationalityserilaizer.data.get('name'):
            nationality=nationalityserilaizer.data.get('name')
        else:
            nationality=None
        if useraccount.otptype:
            otptype=useraccount.otptype
        else:
            otptype=1
        if not request_type:
            if useraccount.twofactorauth:
                full_name = f"{useraccount.firstname} {useraccount.lastname}"
                
            else:
                Activitylog.objects.create(user=user, activity="login",
                                        activitytime=datetime.datetime.now())
        image = None
        try:
            image = Useraccounts.objects.get(customer__user=user).image
        except Exception as e:
            logger.info(e) 
        if image:
            imgpath = settings.AWS_S3_BUCKET_URL + settings.AWS_S3_MEDIA_URL + str(image)
        else:
            imgpath = settings.AWS_S3_BUCKET_URL +settings.NO_IMAGE
        content = {
            'status': 1,
            'data': {
                'token': unicode(token.key),
                'first_name': useraccount.firstname if useraccount.firstname else "",
                'middle_name': useraccount.middlename if useraccount.middlename else "",
                'last_name': useraccount.lastname if useraccount.lastname else "",
                'email': user.email if user.email else "",
                'hidden_email': self.hide_characters(user.email) if user.email else "",
                'phonenumber': f'{useraccount.countrycode} {useraccount.phonenumber}' if useraccount.phonenumber else "",
                'hidden_phonenumber': f'{useraccount.countrycode} {self.hide_characters(useraccount.phonenumber)}' if useraccount.phonenumber else "",
                'last_login': UtilMixins().get_last_login(user),
                'iscompany': True if useraccount.customer.customertype == 2 else False,
                'ubo_customer' : useraccount.customer.ubo_customer,
                'transaction_permission' : True if useraccount.customer.customertype == 2 and (useraccount.account_tran_status or useraccount.ultimate_ben_user) and useraccount.activestatus == "Verified" else False,
                'companyname':Businessdetails.objects.get(customer=useraccount.customer).companyname if useraccount.customer.customertype == 2 else '',
                'image': imgpath ,
                'twofactor':useraccount.twofactorauth,
                'emailverified':useraccount.emailverified,
                'phoneverified':useraccount.phoneverified,
                'addressverified':Customerdocuments.active.filter(customer__user=user, verificationtype__verificationtype=2).exists(),
                'idverified':Customerdocuments.active.filter(customer__user=user, verificationtype__verificationtype=1).exists(),
                'companyverified':Customerdocuments.active.filter(customer__user=user, verificationtype__verificationtype=3).exists(),
                'dateofbirth':useraccount.dateofbirth,
                'nationality':nationality,
                'personaldetails': False if not nationality or not useraccount.dateofbirth  or not useraccount.phonenumber else True,
                'activestatus':useraccount.activestatus,
                'otptype': otptype,
                'transactionlocked':True if self.transaction_lockedforapi(useraccount) else False,
                # temp url
            },
            'message': 'success'
        }

        return Response(content, status=status.HTTP_200_OK)


class DashboardAccountsListView(APIView):
    serializer_class = AccountListsSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        This view should return a list of all the accounts
        for the currently authenticated user.
        """
        # get token from request
        serializer_data = {}
        user_from_token = request.user
        try:
            user_details = Useraccounts.active.get(customer__user=request.user)
            accounts = Accounts.active.filter(
                user_account__customer__user=user_from_token, isdeleted=False).order_by(
                "-createdon")
            if user_details.added_by:
                accounts = acc_list(user_details)
            pr_accounts = list(accounts.filter(isprimary=1).values())
            sc_accounts = list(accounts.filter(isprimary=2).values())
            accounts = accounts.filter(isprimary=3)
            serializer = AccountListsSerializer(accounts, many=True)
            serializer_data['status'] = 1
            data_list = []
            
            def generate_account_details_dict(query_set):
                data_list1 = []
                for account_itr in query_set:
                    currency = Currencies.objects.get(id=account_itr.get('currency') if account_itr.get('currency')
                    else account_itr.get('currency_id'))
                    data_list1.append({
                        'currency_code': currency.code,
                        'flag': currency.flag.url,
                        'account_number': account_itr.get('accountno'),
                        'account_id': account_itr.get('id'),
                        'isprimary': account_itr.get('isprimary'),
                        'balance': str(round(Decimal(account_itr.get('balance')),2))
                    })
                return data_list1
            data_list += generate_account_details_dict(pr_accounts)  # append primary account as first
            data_list += generate_account_details_dict(sc_accounts)  # append secondary account as second
            data_list += generate_account_details_dict(serializer.data)
            serializer_data['data'] = data_list
            serializer_data['message'] = "success"
            return Response(serializer_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.info(e)
            context = {
                "status": 0,
                "data" : [],
                "message" : "Failed To Get contents."
            }
            return Response(context, status=status.HTTP_200_OK)
    def post(self, request):
        """
        add account/ add currency for the currently authenticated user.
        """
        user_from_token = request.user
        user_details = Useraccounts.objects.get(customer__user=user_from_token)
        loggeduser = user_from_token
        content = {}
        try:
            if user_details.added_by:
                loggeduser = user_details.added_by.user
            currency_id = request.data.get("currency_id")
            currency_obj = Currencies.objects.get(id=currency_id)
            accountno_list = list(map(int, list(Accounts.objects.filter(user_account__ismaster_account=False).order_by(
                '-accountno').values_list('accountno', flat=True))))
            accountno_list.sort(reverse=True)
            accountno = int(accountno_list[0]) + 1 if accountno_list else settings.DEFAULT_ADD
            acc_obj, created = Accounts.objects.get_or_create(
                user_account=Useraccounts.objects.get(customer__user=loggeduser),
                currency=currency_obj, createdby=loggeduser, isdeleted=False)
            if created:
                accounts = Accounts.active.filter(user_account__customer__user=loggeduser,
                                                  isdeleted=False)
                if not accounts.filter(isprimary=1):
                    isprimary = 1
                elif accounts.filter(isprimary=1) and not accounts.filter(isprimary=2):
                    isprimary = 2
                else:
                    isprimary = 3
                acc_obj.accountno = accountno
                acc_obj.isprimary = isprimary
                acc_obj.save()
                content['status'] = 1
                content['data'] = {}
                content['message'] = "{} Currency added to your account successfully!".format(currency_obj.code)
                return Response(content, status=status.HTTP_200_OK)
            else:
                content['status'] = 0
                content['data'] = {}
                content['message'] = "Currency already exists!"
                return Response(content, status=status.HTTP_200_OK)
        except Exception as e:
            logger.info(e)
            content['status'] = 0
            content['data'] = {}
            content['message'] = "Invalid data"
            return Response(content, status=status.HTTP_200_OK)

class CurrenciesListView(generics.ListAPIView):
    """
    This view should return a list of all Currencies
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = CurrenciesListSerializer

    def get_queryset(self):
        currencies = Currencies.objects.all()
        return currencies

    def get(self, request):
        try:
            data = CurrenciesListSerializer(self.get_queryset(), many=True).data
            context = {
                "status": 1,
                "data": data,
                "message": "Success",
            }
            return Response(context, status=status.HTTP_200_OK)
        except Exception as e:
            logger.info(e)
            context = {
                "status": 0,
                "data": {},
                "message": "Failed To Get contents.",
            }
            return Response(context, status=status.HTTP_200_OK)


class CountriesListView(generics.ListAPIView):
    """
    This view should return a list of all Countries
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = CountriesListSerializer

    def get_queryset(self):
        countries = Countries.active.all().order_by('name')
        return countries

    def get(self, request):
        try:
            data = CountriesListSerializer(self.get_queryset(), many=True).data
            context = {
                "status": 1,
                "data": data,
                "message": "Success",
            }
            return Response(context, status=status.HTTP_200_OK)
        except Exception as e:
            logger.info(e)
            context = {
                "status": 0,
                "data": {},
                "message": "Failed To Get contents.",
            }
            return Response(context, status=status.HTTP_200_OK)


class TranscationPurposeTypes(generics.ListAPIView):
    """
    This view should return a list of all Transcation purposeTypes(Purpose of remittance)
    """
    serializer_class = TranscationPurposeListSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        transcationpurposetypes = Transactionpurposetype.objects.all()
        return transcationpurposetypes

    def get(self, request):
        try:
            data = TranscationPurposeListSerializer(self.get_queryset(), many=True).data
            context = {
                "status": 1,
                "data": data,
                "message": "Success",
            }
            return Response(context, status=status.HTTP_200_OK)
        except Exception as e:
            logger.info(e)
            context = {
                "status": 0,
                "data": {},
                "message": "Failed To Get contents.",
            }
            return Response(context, status=status.HTTP_200_OK)


class Logout(APIView, APIV1UtilMixins):
    """
    Logout user
    """

    def get(self, request):
        token = self.fetch_token(request)
        try:
            token = Token.objects.get(key=token)
            token.delete()
            content = {
                'status': 1,
                'data': {},
                'message': 'success'
            }
        except:
            exc_resp = {
                'message': 'Invalid token.',
                'status': 0
            }
            raise exceptions.APIException(exc_resp)
        return Response(content, status=status.HTTP_200_OK)


class EditOTPMethodAPIView(APIView):
    serializer_class = EditOTPmethodSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self,request):
        otp_method = request.data.get("otp_method")
        context={}
        user_from_token = request.user
        try:
            user_account = Useraccounts.objects.get(customer__user=user_from_token)

            if str(otp_method) in ["1","2"]:
                user_account.otptype = int(otp_method)
                user_account.save()
                message = "Successfully Saved!"
                status = True
                if str(otp_method) == '1': 
                    data= 'Email'
                elif str(otp_method) == '2':
                    data='Both Email & Phone Number'           
            else:
                message = "Invalid option!"
                data = None
                status = False
        except Exception as e:
            logger.info(e)
            message = "User details not found"
            data = None
            status = False
        
        context['message'] = message
        context['data'] = data
        context['status'] = status
        return Response(context)

class ChangePasswordAPIView(APIView,APIV1UtilMixins):
    serializer_class =ChangePasswordSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self,request):
        if request.data.get('type')== "sendotp":
            password = request.data.get('password')
            new_password = request.data.get('new_password')
            confirmpassword = request.data.get('confirmpassword')
            user_from_token = request.user
            user_account = Useraccounts.objects.get(customer__user=user_from_token)
            full_name = user_account.customer.user.first_name 
            token = self.fetch_token(request)
            
            def validate():               
                if not check_password(password,request.user.password):
                    return {
                    'status' : 0,
                        'error':
                            {
                                "password": ["Current password is invalid!"]
                        },
                    'message' : "Validation error"
                    }
                elif new_password==password:
                    return {
                        'status' : 0,
                        'error': {
                                "new_password": ["Your new password cannot be the same as your current password"]},
                        'message' : "Validation error",
                        
                        }
                elif new_password != confirmpassword:
                    return {
                    'status' : 0,
                    'error':
                            {
                                
                                "confirmpassword": ["Your passwords does not match!"]
                        },
                        'message' : "Validation error",
                        }

                elif (len(new_password)<10 or len(new_password)>50):
                    return {
                    'status' : 0,
                        'error':
                            {
                                
                                "new_password": [f"New password not valid ! Total characters should be between 10 and 50"]
                        },
                        'message' : "Validation error"
                        }
                elif not re.search("[A-Z]",new_password):
                    return {
                    'status' : 0,
                    'error':
                    {
                        "new_password":[f"New password not valid ! It should contain one letter between [A-Z]"]

                    },
                        'message' :"Validation error"
                        }
                elif not re.search("[a-z]",new_password):
                    return {
                'status' : 0,
                'error':
                {
                    "new_password":[f"New password not valid ! It should contain one letter between [a-z]"]
                },
                'message' :"Validation Error"
                    }
                elif not re.search("[1-9]",new_password):
                    return {
                    'status' : 0,
                    'error':
                        {
                        "new_password":[f"New password not valid ! It should contain one letter between [1-9]"]
                        },
                    'message' :"Validation error",
                    }
                elif not re.search("[~!@#$%^&*]",new_password):
                    return {
                    'status' : 0,
                    'error':
                    {
                        "new_password":
                            [f"New password not valid ! It should contain at least one letter in [~!@#$%^&*]"]
                        },
                    
                    'message' :"Validation Error"
                        }
                elif re.search("[\s]",new_password):
                    return {
                    'status' : 0,
                        
                    'error':
                    {
                        ' new_password':[f"New password not valid ! It should not contain any space"]
                    },
                    'message' :"Validation Error"
                    }
                else:
                    otp_status=OTP()
                if otp_status:
                    return {
                        'status' : 1,
                        'message' : f"OTP send successfully",
                        'data': {
                                "password":request.data.get('password'),
                                "new_password": request.data.get('new_password'),
                                "confirmpassword":request.data.get('confirmpassword')
                                },
                    }
                else:

                    return {
                        'status' : 0,
                        'message' : f"OTP send failed"
                    }
        
            response = validate()
            return Response(response)
        elif request.data.get('type')== "validateotp":
            seriliazer=ChangePasswordSerializer(data=request.data)             
            if seriliazer.is_valid():
                otp = request.POST.get('otp')
                if otp:
                    otp = otp.strip()
                token = self.fetch_token(request)
            
                def opt_validate():
                    if token:
                        try:
                            otp_obj = Otps.objects.get(code=otp,
                                        transactiontype='Change Password',
                                        validated=False,
                                        createdby=request.user,token=token,isdeleted=False)

                        except Exception as e:
                            logger.info(e)
                            return {
                                'status' : 0,
                                'message' : "Verification failed, wrong user or otp"
                            }
                        valid_till = datetime.datetime.now()
                        valid_till = valid_till.date().strftime(settings.DATE_FORMAT)
                        valid_date = datetime.datetime.strptime(valid_till, settings.DATE_FORMAT)
                        if valid_date.date() <= otp_obj.validtill:
                            otp_obj.validated = True
                            otp_obj.save()
                        
                        else:
                            return {
                                'status' :0,
                                'message' : 'Verification failed, expired otp'
                            }
                        serializer = ChangePasswordSerializer(data=request.data, context={'request':request})
                        if serializer.is_valid():
                            serializer.save()
                            return {
                                    'status' : 1,
                                    'message' : 'Your password was successfully updated!',
                                    'Password':request.data.get('new_password')
                                }
                        else:

                            return {
                
                                'status' : 0,
                                'message' : 'Password Change Failed ',
                                
                            }
                    else:
                        return {
                                'status' :0,
                                'message' : 'Verification failed, wrong user or otp'
                            }         
                response = opt_validate()
                return Response(response)     
            else:
                context={
                'status':0,
                'error':seriliazer.errors,
                'message':"Validation error"
            }
            return Response(context)

        elif request.data.get('type')== "resendotp":
            user_from_token = request.user
            user_account = Useraccounts.objects.get(customer__user=user_from_token)
            full_name = user_account.customer.user.first_name 
            token = self.fetch_token(request)   
              
            def validate():
                if token:
                    try:
                        otp_status=OTP()
                        if otp_status:
                            return {
                            'status' : 1,
                            'message' : f"OTP resent, Please verify!",
                            }
                        else:

                            return {
                            'status' : 0,
                            'message' : f"Something went wrong! Please try again."
                        }
                    except Exception as e:
                        logger.info(e)
                        return{
                                'status':0,
                                'message':'Something went wrong! Please try again'
                                }
            response = validate()
            return Response(response) 

class RemoveCurrencyView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self,request):
        logged_user = request.user
        accounts = Accounts.active.filter(isprimary=3, user_account__customer__user=logged_user,
                                          balance=0).order_by("currency__code")
        if not accounts:
            user_details = Useraccounts.objects.get(customer__user = request.user, isdeleted = False)
            customer = user_details.added_by
            accounts = Accounts.objects.filter(isprimary=3, user_account__customer=customer, isdeleted=False,
                                               balance=0).order_by("currency__code")
        serializer = AccountListsSerializer(accounts, many=True)
        data_list = []
        for account_itr in serializer.data:
            currency = Currencies.objects.get(id=account_itr.get('currency'))
            data_list.append({
                'currency_code': currency.code,
                'flag': currency.flag.url,
                'account_number': account_itr.get('accountno'),
                'account_id': account_itr.get('id'),
            })
        context={
            "status": 1,
            "data": data_list,
            "message": 'success',
                        }
        return Response(context)

    def delete(self,request):
        account_id = request.data.get('id')
        try:
            account_obj = Accounts.objects.get(~Q(isprimary=1)&~Q(isprimary=2),id=account_id)
            if not account_obj.isdeleted:
                account_obj.isdeleted = True
                account_obj.save()

                context={
                    "status" : 1,
                    "data" : {},
                    "message" : "Account Deleted Successfully!",
                        }
                return Response(context, status=status.HTTP_200_OK)
            else:
                context = {"status": 0,
                           "data": {},
                           "message": "Account not found",
                           }
                return Response(context, status=status.HTTP_200_OK)
        except Exception as e:
            context={"status":0,
                    "data": {},
                     "message":"Account not found",
            }
            return Response(context,status=status.HTTP_404_NOT_FOUND)


class TwoFactorAuthenticationAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        tf_status = request.data.get("tf_status")
        context = {}
        try:
            user_account = Useraccounts.objects.get(customer__user=request.user)
            if tf_status == '1':
                user_account.twofactorauth = True
                user_account.save()
                status = 1
                message = "Successfully Saved!"
            else:
                user_account.twofactorauth = False
                user_account.save()
                status = 1
                message = "Successfully Saved!"
            serializer = TwoFactUserAccountSerializer(user_account)
            data = serializer.data
        except Exception as e:
            status = 0
            data={}
            message = "User details not found"
        context['status'] = status
        context['data']= data
        context['message'] = message
        return Response(context)


class TwoStepVerificationAPIView(APIView,APIV1UtilMixins):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.data.get("action") == "resend":
            try:
                user = User.objects.get(email=request.user)
                otp_token = self.fetch_token(request)

                user_account = Useraccounts.objects.get(customer__user=request.user)
                full_name = f"{user_account.firstname} {user_account.lastname}"
                OTP()
                context={
                    'status':True,
                    'message':'OTP resent, Please verify!'
                }

            except Exception as e:
                context={
                    'status':False,
                    'message':'Something went wrong! Please try again.'
                }
            return Response(context)
        serializer=TwoStepVerificationSerializer(data=request.data)
        if serializer.is_valid():
            context = {}
            otp = request.data.get("otp")
            try:
                user = User.objects.get(email=request.user)
                try:
                    token1 = self.fetch_token(request)

                    otp_obj = Otps.objects.get(code=otp,
                                               transactiontype="Login",
                                               createdby=user, token=token1)
                    if not otp_obj.validated:
                        if otp_obj.validtill >= datetime.datetime.now().date():
                            otp_obj.validated = True
                            otp_obj.save()
                            useraccount = get_object_or_404(Useraccounts, customer__user=user)
                            user_nationality = get_object_or_404(Useraccounts, customer__user=user)
                            nationalityserilaizer = CountryNameSerializer(user_nationality.nationality)

                            if nationalityserilaizer.data.get('name'):
                                nationality = nationalityserilaizer.data.get('name')
                            else:
                                nationality = None
                            if useraccount.otptype:
                                otptype = useraccount.otptype
                            else:
                                otptype = 1
                            Activitylog.objects.create(user=user, activity="login",
                                                       activitytime=datetime.datetime.now())
                            context = {
                                'status': 1,
                                'data': {
                                    'first_name': useraccount.firstname if useraccount.firstname else "",
                                    'middle_name': useraccount.middlename if useraccount.middlename else "",
                                    'last_name': useraccount.lastname if useraccount.lastname else "",
                                    'email': user.email if user.email else "",
                                    'phonenumber': f'{useraccount.countrycode} {useraccount.phonenumber}' if useraccount.phonenumber else "",
                                    'last_login': UtilMixins().get_last_login(user),
                                    'iscompany': True if useraccount.customer.customertype == 2 else False,
                                    'companyname': Businessdetails.objects.get(
                                        customer=useraccount.customer).companyname if useraccount.customer.customertype == 2 else '',
                                    'image': 'https://i.picsum.photos/id/866/200/300.jpg?hmac=rcadCENKh4rD6MAp6V_ma-AyWv641M4iiOpe1RyFHeI',
                                    'twofactor': useraccount.twofactorauth,
                                    'emailverified': useraccount.emailverified,
                                    'phoneverified': useraccount.phoneverified,
                                    'addressverified': useraccount.addressverified,
                                    'idverified': useraccount.idverified,
                                    'otptype': otptype,
                                    'activestatus': useraccount.activestatus,
                                    'dateofbirth': useraccount.dateofbirth,
                                    'nationality': nationality,
                                    'transactionlocked':True if useraccount.transaction_locked_for else False,
                                },
                                'message': 'OTP Verified!'
                            }
                        else:
                            context['status'] = False
                            context['message'] = 'verification failed, otp expired'
                    else:
                        context['status'] = False
                        context['message'] = 'verification failed, already validated'
                except Exception as e:
                    context['status'] = False
                    context['message'] = 'verification failed, wrong user or otp'
            except Exception as e:
                context['status'] = False
                context['message'] = 'Something went wrong! Please try login again.'
            return Response(context)
        else:
            context={
                'status':False,
                'error':serializer.errors,
                'message':"Validation error"
            }
            return Response(context)

class CurrencyConversionAPIView(APIView,APIV1UtilMixins,TransactionMail,FindAccount):
    serializer_class =AccountListsSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, TransactionPermission]       
    def get(self,request):
        accounts = Accounts.objects.filter(user_account__customer__user=request.user, isdeleted=False)
        user_details = Useraccounts.active.get(customer__user=request.user,isdeleted=False)
        if not accounts:
            user_details = Useraccounts.objects.get(customer__user = request.user, isdeleted = False)
            customer = user_details.added_by
            accounts = Accounts.objects.filter(isprimary=3, user_account__customer=customer, isdeleted=False).order_by("currency__code")
        serializer = AccountListsSerializer(accounts, many=True)
        data_list = []
        for account_itr in serializer.data:
            currency = Currencies.objects.get(id=account_itr.get('currency'))
            data_list.append({
                'currency_code': currency.code,
                'flag': currency.flag.url,
                'account_number': account_itr.get('accountno'),
                'account_id': account_itr.get('id'),
            })
        context={
            "status": 1,
            "data": data_list,
            "message": 'success!',
                        }
        return Response(context)
    def post(self,request):
        if request.data.get('type')=='currencyconversion':
            try:
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
                user_account = Useraccounts.objects.get(customer__user=request.user)
                debit_acc_balance = debit_account.balance
            except Exception as e:
                logger.info(e)
                debit_acc_balance = None
            context = json.loads(json.dumps(request.data))
            def validate():
                seriliazer = CurrencyConversionSerializer(data=request.data, context = {
                    'debit_account_balance' : debit_acc_balance,'currencyconversion': True,
                })

                if seriliazer.is_valid():
                    currency_conversion = Currencyconversionratescombined.objects.get(fromcurrency__code=debit_acc_curr_code,
                                                                                    tocurrency__code=credit_acc_curr_code,
                                                                                isdeleted=False)
                    conversionrate = round(currency_conversion.conversionrate,4)
                    
                    try:
                        currency_margin = Currencyconversionmargins.objects.get(fromcurrency__code=debit_acc_curr_code,tocurrency__code=credit_acc_curr_code,isdeleted=False)
                        margin_rate = currency_margin.marginpercent
                        conversionrate = conversionrate - (conversionrate* Decimal(float(margin_rate)/100))
                    except Exception as e:
                        logger.info(e)
                        pass
                    credit_amount = round(net_amount * conversionrate,2)

            
                    return{
                            "status": 1,
                            "message": 'Success!',
                            "data":{
                                'debit_acc_no':debit_acc_no,
                                'balance':str(round(debit_account.balance,2)),
                                'debit_acc_curr_code':debit_acc_curr_code,
                                'credit_acc_no':credit_acc_no,
                                'credit_acc_curr_code':credit_acc_curr_code,
                                'conversionrate':str(round(conversionrate,4)),
                                'net_amount':str(net_amount),
                                'note':note,
                                'conversion_fee':str(conversion_fee),
                                'debit_amount':str(debit_amount),
                                'credit_amount':str(credit_amount)
                            }
                    }
                else:
                    return {
                        "status": 0,
                        "error": seriliazer.errors,
                        "message" : "validation error"
                    }
                        
            response = validate()
            return Response(response)
            
        elif request.data.get('type')== "confirmdetails":
            user_account = Useraccounts.objects.get(customer__user=request.user)
            token = self.fetch_token(request)   

            full_name = f"{user_account.firstname} {user_account.lastname}"

            otp_status=OTP()
            if otp_status:
                    context={
                "status": 1,
                "message": 'OTP sent, Please verify!'
                }      
            else:
                    context= {
                        'status' : 0,
                        'message' : f"OTP send failed"  
                    }
            return Response(context)
       
        elif request.data.get('type')=='otpresend':
            user_account = Useraccounts.objects.get(customer__user=request.user)
            token = self.fetch_token(request)   

            full_name = f"{user_account.firstname} {user_account.lastname}"             

            def validate():
                if token:
                    try:
                        otp_status=OTP()
                        if otp_status:
                            return {
                            'status' : 1,
                            'message' : f"OTP resent, Please verify!",
                            }
                        else:

                            return {
                            'status' : 0,
                            'message' : f"Something went wrong! Please try again."
                        }
                    except Exception as e:
                        logger.info(e)
                        return{
                                'status':0,
                                'message':'Something went wrong! Please try again'
                                }
            response = validate()
            return Response(response)  

        elif request.data.get('type')=='otpvalidate':
            seriliazer =CurrencyConversionSerializer(data=request.data, context={'otpvalidate' : True})
            if seriliazer.is_valid():  
                    debit_account = Accounts.objects.get(accountno=request.POST.get("debit_account"))
                    credit_account = Accounts.objects.get(accountno=request.POST.get("credit_account"))
                    net_amount = round(Decimal(request.POST.get("net_amount")),2)
                    debit_acc_no = debit_account.accountno
                    note = request.POST.get("note")
                    conversion_fee = round(net_amount * Decimal(0.5 / 100),2)
                    debit_amount = net_amount + conversion_fee
                    user_account = Useraccounts.objects.get(customer__user=request.user)
                    otp = request.POST.get('otp')
                    debit_acc_curr_code = debit_account.currency.code
                    credit_acc_no = credit_account.accountno
                    credit_acc_curr_code = credit_account.currency.code
                    token = self.fetch_token(request)
                    currency_conversion = Currencyconversionratescombined.objects.get(
                        fromcurrency__code=debit_acc_curr_code,tocurrency__code=credit_acc_curr_code, isdeleted=False)
                    conversionrate = round(currency_conversion.conversionrate,4)
                    currency_margin = Currencyconversionmargins.objects.get(fromcurrency__code=debit_acc_curr_code,tocurrency__code=credit_acc_curr_code,isdeleted=False)
                    margin_rate = currency_margin.marginpercent
                    conversionrate = conversionrate - (conversionrate* Decimal(float(margin_rate)/100))     
                
                    if token:
                        if otp:
                            otp = otp.strip()
                            try:
                                otp_obj = Otps.objects.get(code=otp, token=token, transactiontype="Currency Conversion",
                                                createdby=request.user)
                                transaction_lock_fn(request,is_lock=False)
                            except Exception as e:
                                logger.info(e)
                                transaction_state = transaction_lock_fn(request)
                                context= {
                                    'otp_error' : True,
                                    'status' :transaction_state.get("status"),
                                    'message' : transaction_state.get("message")
                                    }
                                return Response(context)

                            if not otp_obj.validated:
                                if otp_obj.validtill >= datetime.datetime.now().date():
                                    otp_obj.validated = True
                                    otp_obj.save()
                                    try:
                                        account_number_prev = Transactions.objects.latest('transactionno').transactionno
                                    except Exception as e:
                                        logger.info(e)
                                        account_number_prev = 10000000
                                    try:
                                        transactionno = int(account_number_prev) + 1
                                        debit_accountno = debit_account.accountno
                                        credit_accountno=credit_acc_no
                                        fromamount= net_amount
                                        toamount = round(net_amount * conversionrate,2)
                                        conversion_fee = conversion_fee
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
                                                conversionrate = conversionrate,
                                                toamount=toamount,
                                                transactiontype=Transactiontypes.objects.get(name='Currency Conversion'),
                                                createdby=request.user,
                                                note=request.data.get('note'),
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
                                            invoice = f"transaction{transactionno}.pdf"
                                            context ={
                                                'status':1,
                                                'message':"Transaction successfully completed ",
                                                'data':{
                                                    'debit_acc_no':debit_acc_no,
                                                    'balance':str(round(debit_account.balance,2)),
                                                    'debit_acc_curr_code':debit_acc_curr_code,
                                                    'credit_acc_no':credit_acc_no,
                                                    'credit_acc_curr_code':credit_acc_curr_code,
                                                    'conversionrate':str(round(conversionrate,4)),
                                                    'net_amount':str(net_amount),
                                                    'note':note,
                                                    'conversion_fee':str(conversion_fee),
                                                    'debit_amount':str(debit_amount),
                                                    'credit_amount':str(toamount),
                                                    'transactionnumber': transactionno,
                                                    'transaction_id': tr_deb_amount.id,
                                                    'date_and_time': datetime.datetime.utcnow().strftime("%d %b %Y, %-H:%M UTC"),
                                                    'curr_conversion': True,
                                                    'request':request,
                                                    'filepath':''                                                    
                                                    }
                                                }
                                            TransactionMail().transaction_success_or_failure_mail(email=request.user.email,email_data=context['data'],status=True,transaction_type=2)

                                            if context['data']['request']:
                                                del context['data']['request']

                                            if context['data'].get("domain"):
                                                del context['data']['domain']
                                            return Response(context)
                                        except Exception as e:
                                            logger.info(e)
                                            context={
                                                'status' :0,
                                                'message' :'Something went wrong! Please try again'
                                            }
                                        return Response(context)
                                    except Exception as e:
                                        logger.info(e)
                                        context={
                                            'status' :0,
                                            'message' : 'Verification failed, wrong user or otp'
                                        }
                                        return Response(context)

                                else:
                                    context={
                                    'status' :0,
                                    'message' : 'verification failed, otp expired'
                                    } 
                                    return Response(context)
                                    
                            else:
                                context = {
                                'status' :0,
                                'message' : 'verification failed, already validated'
                                }  
                                return Response(context)
                        else:
                            context = {
                            'status' :0,
                            'message' : 'Verification failed, wrong user or otp'
                                }  
                            return Response(context)
                    else:
                        context = {
                            'status' :0,
                            'message' : 'Verification failed, wrong user or otp'
                        }   
                        return Response(context)
            else: 
                context = {
                    'status':0,
                    'message':'validation error',
                    'errors':seriliazer.errors
                }
                return Response(context)            

        elif request.data.get('type')== 'email_send':
            seriliazer =CurrencyConversionSerializer(data=request.data, context={'email_send':True})
            if seriliazer.is_valid():
                transactionno=request.data.get('transaction_no')
                try:
                    transaction = Transactions.objects.get(transactionno=int(transactionno),amount_type="Net Amount")
                except Exception as e:
                    logger.info(e)
                    return Response({"status":0,
                        "message":"No transaction found"})
                transaction_amount = transaction.fromamount
                debit_acc_curr_code = transaction.fromaccount.currency.code
                debit_account = transaction.fromaccount.accountno         
                data = {
                'mail_attach' : True,
                'net_amount' : transaction_amount,
                'debit_acc_curr_code' : debit_acc_curr_code,
                'debit_account':debit_account,
                'request': request,

                }
                
                invoice = f"transaction{transactionno}.pdf"
                filepath = 'invoices/'+invoice
                if exists(filepath):
                    attach = open(filepath, "r")
                else:
                    attach = render_pdf('transactions/currency_conversion/transaction-invoice.html', data, invoice)
                self.transaction_success_or_failure_mail(email=request.user.email, email_data=data, status=True,attach=attach,
                                                        transaction_type=2)
                context = {
                    'status':1,
                    'message':'Email send successfully',
                }
            else: 
                context = {
                    'status':0,
                    'message':'validation error',
                  'errors':seriliazer.errors
                }

            return Response(context)

class VerificationOTPSendAPIView(APIView,OTP,APIV1UtilMixins):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self,request):
        context = {}
        token  = self.fetch_token(request)
        user_account = Useraccounts.objects.get(customer__user=request.user)
        full_name = f"{user_account.firstname} {user_account.lastname}"
        context['status'] = True
        context['message'] = 'OTP send, Please verify!'
        return Response(context)


class OTPVerifyAPIView(APIView,OTP,APIV1UtilMixins):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        context = {}
        user_account = Useraccounts.objects.get(customer__user=request.user)
        mobileverification=MobileOTPmethodSerializer(user_account)
        context['user_account'] = mobileverification.data
        context['message']='successfully'
        context['status'] = True
        return Response(context)

    def post(self, request):
        context = {}
        if request.data.get("action") == "resend":
            try:
                user = request.user
                token = self.fetch_token(request)
                user_account = Useraccounts.objects.get(customer__user=user)
                full_name = f"{user_account.firstname} {user_account.lastname}"
            
                context['status'] = True
                context['message'] = 'OTP resent, Please verify!'
            except Exception as e:
                logger.info(e)
                context['status'] = False
                context['message'] = 'Something went wrong! Please try again.'
            return Response(context)
        otp = request.data.get("otp")
        error_res = {"status": False,
                     "message": "validation error"
                     }
        d = {}
        attrs_dict = {"otp":otp}

        none_list = []
        for i in attrs_dict:
            if not attrs_dict[i]:
                none_list.append(i)
        if len(none_list) != 0:
            for i in none_list:
                d[i] = ["This field is required"]
            error_res["error"] = d

            return Response(error_res)
        context['status'] = True
        try:
            transactiontype = "MobileNumber Verification"
            token = self.fetch_token(request)
            otp_obj = Otps.objects.get(code=otp,token=token,transactiontype=transactiontype,
                             createdby=request.user)
            if not otp_obj.validated:
                if otp_obj.validtill >= datetime.datetime.now().date():
                    otp_obj.validated = True
                    otp_obj.save()
                    try:
                        user_account = Useraccounts.objects.get(customer__user=request.user)
                        user_account.phoneverified = True
                        user_account.save()
                        context['message'] = "Phone number verified successfully!"
                    except Exception as e:
                        logger.info(e)
                        pass
                        context['message'] = "OTP Verified!"
                        return Response(context)
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
        mobileverification = MobileOTPmethodSerializer(user_account)
        context['user_account'] = mobileverification.data
        return Response(context)

class ForgotPasswordAPIView(APIView):
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            content = {
                "status": 1,
                "message": "A password reset link has been sent."
            }
            return Response(content)
        content = {
                "status": 0,
                "error": serializer.errors,
                "message" : "validation error"
            }
        return Response(content, status=status.HTTP_200_OK)

class PersonalDetailsAPIView(APIView,OTP,APIV1UtilMixins):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        context = {}
        user_account = Useraccounts.objects.get(customer__user=request.user)
        user_personaldetail = PersonalDetailSerializer(user_account)
        context['status'] = 1
        context['user_account'] = user_personaldetail.data
        context['user_account']['email'] = request.user.email
        context['message']='success'
        return Response(context)

    def post(self, request):
        context={}
        user = request.user
        token = self.fetch_token(request)
        user_account = Useraccounts.objects.get(customer__user=user)
        full_name = f"{user_account.firstname} {user_account.lastname}"
        context['message']='OTP sent, Please verify!'
        context['status']=True
        return Response(context)


class OTPVerifyPersonalDetailAPIView(APIView,OTP,APIV1UtilMixins):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer=OTPVerifyPersonalDetailSerializer(data=request.data)
        if serializer.is_valid():
            context = {}
            otp = request.data.get("otp")
            context['status'] = True
            if request.data.get("action") == "resend":
                try:
                    user = request.user
                    token = self.fetch_token(request)
                    user_account = Useraccounts.objects.get(customer__user=user)
                    full_name = f"{user_account.firstname} {user_account.lastname}"
                   
                    context['status'] = True
                    context['message'] = 'OTP resent, Please verify!'
                except Exception as e:
                    logger.info(e)
                    context['status'] = False
                    context['message'] = 'Something went wrong! Please try again.'
                return Response(context)
            try:

                transactiontype = "Update User Details"
                token = self.fetch_token(request)
                otp_obj = Otps.objects.get(code=otp, token=token, transactiontype=transactiontype,
                                           createdby=request.user)
                if not otp_obj.validated:
                    if otp_obj.validtill >= datetime.datetime.now().date():
                        otp_obj.validated = True
                        otp_obj.save()

                        context['message'] = 'OTP verified'
                        user_account = Useraccounts.objects.get(customer__user=request.user)
                        Personaldetailserializer = PersonalDetailSerializer(user_account)
                        context['user_account'] = Personaldetailserializer.data
                        context['user_account']['email'] = request.user.email
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
            return Response(context)
        else:
            context={
                'status':False,
                'error':serializer.errors,
                'message':'Validation error'
            }
            return Response(context)
class ConfirmEditDetailsAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        phonenumber = request.data.get('phonenumber')
        country = request.data.get('country')
        nationality = request.data.get('nationality')
        dateofbirth = request.data.get('dateofbirth_to_db')
        street_address = request.data.get('street_address')
        city = request.data.get('city')
        region = request.data.get('region')
        zipcode = request.data.get('zipcode')

        error_res = {"status": False,
                     "message": "validation error"
                     }
        d = {}
        attrs_dict = {"phonenumber": phonenumber, "country": country, "nationality": nationality,
                      'dateofbirth': dateofbirth, 'street_address': street_address,
                      'city': city, 'region': region, 'zipcode': zipcode}

        none_list = []
        for i in attrs_dict:
            if not attrs_dict[i]:
                none_list.append(i)
        if len(none_list) != 0:
            for i in none_list:
                d[i] = ["This field is required"]
            error_res["error"] = d

            return Response(error_res)
        context = {}
        instance = Useraccounts.objects.get(id=request.data.get('id')) if Useraccounts.objects.filter(
            id=request.data.get('id')) else None
        if request.data.get("action") == "goto_edit":
            instance = get_object_or_404(Useraccounts, id=request.data.get('id'))
            serializer = UserDetailsSerializer(data=request.data, instance=instance)
            if request.data.get("nationality"):
                context['nationality'] = int(request.data.get("nationality")) if request.data.get(
                    "nationality") else None
            else:
                context['nationality'] = instance.nationality.id if instance and instance.nationality else None
            context['id'] = request.data.get('id')
            context['firstname'] = instance.firstname
            context['lastname'] = instance.lastname
            context['middlename'] = instance.middlename
            context['email'] = request.user.email
            if serializer.is_valid():
                context['data'] = serializer.data
                return Response(context)
            return Response(context)
        if instance:
            if instance.phonenumber != request.data.get('phonenumber'):
                instance.phoneverified = False
                instance.save()
            serializer = UserDetailsSerializer(data=request.data, instance=instance)
            if serializer.is_valid():
                serializer_save = serializer.save()
                serializer_save.country = Countries.objects.get(
                    id=request.data.get('country')) if Countries.objects.filter(
                    id=request.data.get('country')) else None
                countryserializer = CountryNameSerializer(serializer_save.country)
                if request.data.get('nationality'):
                    serializer_save.nationality = Countries.objects.get(
                        id=request.data.get('nationality')) if Countries.objects.filter(
                        id=request.data.get('nationality')) else None
                if request.data.get('dateofbirth_to_db'):
                    serializer_save.dateofbirth = request.data.get('dateofbirth_to_db')
                serializer_save.save()
                context['data'] = serializer.data
                context['data']['country'] = countryserializer.data.get('name')
                context['status'] = True
                context['message'] = "Updated successfully"
                return Response(context)
            else:
                context['status'] = False
                context['errors'] = serializer.errors
                context['message'] = 'verification failed'
                return Response(context)


class InternationalWireTransferAPIView(APIView,APIV1UtilMixins,TransactionMail,ModelQueries,UtilMixins):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated,TransactionPermission]
    def post(self,request):
        data=request.data              
        def validate_invoice_doc(data):
            invoice_doc=data
            if invoice_doc:
                
                ext = os.path.splitext(invoice_doc.name)[1]
                filesize = invoice_doc.size
                if not ext in settings.ALLOWED_FORMATS:
                    return {
                        "status": 0,
                        "message": "validation error",
                        "error": {
                            "invoice_doc": [
                                "Incorrect file format."
                            ]
                                }
                     }
                
                elif filesize > settings.MAX_FILE_SIZE:
                    return {
                        "status": 0,
                        "message": "validation error",
                        "error": {
                            "invoice_doc": [
                               "Maximum file size allowed is 10 MB"
                            ]
                                }
                    }
                elif not all(ord(c) < 128 for c in invoice_doc.name):
                    return {
                        "status":0,
                        "message": "validation error",
                        "error": {
                            "invoice_doc": [
                               "Special characters should not be in file name"
                            ]
                                }
                    }
                else:
                    return {
                "status":1,
                }                 
            return invoice_doc
        if data.get('invoice_doc'):
            outcome= validate_invoice_doc(data.get('invoice_doc'))
            if not outcome.get("status"):
                return Response(outcome)
        if request.data.get('type')=='InternationalWireTransfer':
            seriliazer=InternationalWireTransferSerializer(data=data,context={'InternationalWireTransfer':True}) 
            is_ext_ben = Externalbeneficiaries.objects.filter(Q(accountnumber=request.data.get('beneficiary_account')) | Q(name=request.POST.get('beneficiaryname')),isdeleted=False,createdby=request.user).exists()
            if seriliazer.is_valid():
                amount = round(Decimal(request.data.get('debit_amount')),2)
                from_amount = amount  
                from_account = Accounts.objects.get(accountno=request.data.get('debit_account'), isdeleted=False)
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
                if from_account_balance < debit_amount:
                    context={
                        'status':0,
                        'message':"You don't have enough funds to make this transaction"
                    }
                    return Response(context)
                elif from_amount < self.min_tr_amount:
                    context={
                        'status':0,
                        'message': f'Minimum amount required for the transaction is {format(self.min_tr_amount, ".2f")} {from_currency_code}'
                    }
                    return Response(context)
             
                elif request.POST.get('ownaccount') == '1' and request.POST.get('has_invoice')=='0':  
                    if request.data.get('purpose_note'):                      
                        context={
                                'status':1,
                                'message':'Success!',
                                'data':{
                                    'fromaccount':request.data.get('debit_account'),
                                    'debit_acc_curr_code' : from_currency_code,
                                    'beneficiary_account':request.data.get('beneficiary_account'),
                                    'currency' : request.data.get('Currency'),
                                    'amount':format(float(request.data['debit_amount']), ".2f"),
                                    'beneficiaryname':request.data.get('beneficiaryname'),
                                    'bankname':request.data.get('bankname'),
                                    'swiftcode':request.data.get('swiftcode'),
                                    'city':request.data.get('city'),
                                    'country':request.data.get('country'),
                                    'account_type':request.data.get('account_type') if request.data.get('account_type') else "Personal",
                                    'purpose':request.data.get('purpose'),
                                    'purpose_note':request.data.get('purpose_note'),
                                    'email':request.data.get('email'),
                                    'note':request.data.get('note'),
                                    "ownaccount":int(request.data['ownaccount']),
                                    'invoice':None,
                                    'conversion_fee' : format(self.conversion_fee, ".2f"),
                                    'wire_tr_fee' : format(self.wire_transfer_fee, ".2f"),
                                    'cable_charge' : format(self.cable_charge, ".2f"),
                                    'credit_amount' : format(self.credit_amount, ".2f"),
                                    'debit_amount' : format(debit_amount, ".2f"),
                                    'is_ext_ben':is_ext_ben
                                    }
                                    }
                        if context['data'].get("domain"):
                            del context['data']['domain']
                        return Response(context)
                        
                    else:
                        context={
                                'status':1,
                                'message':'Success!',
                                'data':{
                                    'fromaccount':request.data.get('debit_account'),
                                    'debit_acc_curr_code' : from_currency_code,
                                    'beneficiary_account':request.data.get('beneficiary_account'),
                                    'currency' : request.data.get('Currency'),
                                    'amount':format(float(request.data['debit_amount']), ".2f"),
                                    'beneficiaryname':request.data.get('beneficiaryname'),
                                    'bankname':request.data.get('bankname'),
                                    'swiftcode':request.data.get('swiftcode'),
                                    'city':request.data.get('city'),
                                    'country':request.data.get('country'),
                                    'account_type':request.data.get('account_type') if request.data.get('account_type') else "Personal",
                                    'purpose':request.data.get('purpose'),
                                    'email':request.data.get('email'),
                                    "ownaccount":int(request.data['ownaccount']),
                                    'invoice':None,
                                    'note':request.data.get('note'),
                                    'conversion_fee' : format(self.conversion_fee, ".2f"),
                                    'wire_tr_fee' : format(self.wire_transfer_fee, ".2f"),
                                    'cable_charge' : format(self.cable_charge, ".2f"),
                                    'credit_amount' : format(self.credit_amount, ".2f"),
                                    'debit_amount' : format(debit_amount, ".2f"),
                                    'is_ext_ben':is_ext_ben
                                    }
                                }
                        if context['data'].get("domain"):
                            del context['data']['domain']
                        return Response(context)

                elif request.POST.get('ownaccount') == '0' and request.POST.get('has_invoice')=='0':
                        if request.data.get('purpose_note'): 
                            context={
                                    'status':1,
                                    'message':'Success!',
                                    'data':{
                                        'fromaccount':request.data.get('debit_account'),
                                        'debit_acc_curr_code' : from_currency_code,
                                        'beneficiary_account':request.data.get('beneficiary_account'),
                                        'currency' : request.data.get('Currency'),
                                        'amount':format(float(request.data['debit_amount']), ".2f"),
                                        'beneficiaryname':request.data.get('beneficiaryname'),
                                        'bankname':request.data.get('bankname'),
                                        'swiftcode':request.data.get('swiftcode'),
                                        'city':request.data.get('city'),
                                        'country':request.data.get('country'),
                                        'purpose':request.data.get('purpose'),
                                        'account_type':request.data.get('account_type') if request.data.get('account_type') else "Personal",
                                        'purpose_note':request.data.get('purpose_note'),
                                        'email':request.data.get('email'),
                                        'note':request.data.get('note'),
                                        "ownaccount":int(request.data['ownaccount']),
                                        'box_no':request.data.get('user_box_no'),
                                        'street':request.data.get('user_street'),
                                        'user_city':request.data.get('user_city'),
                                        'state':request.data.get('user_state'),
                                        'user_country':request.data.get('user_country'),
                                        'user_phone':request.data.get('user_phone'),
                                        'invoice':None,
                                        'conversion_fee' : format(self.conversion_fee, ".2f"),
                                        'wire_tr_fee' : format(self.wire_transfer_fee, ".2f"),
                                        'cable_charge' : format(self.cable_charge, ".2f"),
                                        'credit_amount' : format(self.credit_amount, ".2f"),
                                        'debit_amount' : format(debit_amount, ".2f"),
                                        'is_ext_ben':is_ext_ben
                                        }
                                    }
                            if context['data'].get("domain"):
                                del context['data']['domain']
                            return Response(context)
                       
                       
                        else:
                            context={
                                'status':1,
                                'message':'Success!',
                                'data':{
                                    'fromaccount':request.data.get('debit_account'),
                                    'debit_acc_curr_code' : from_currency_code,
                                    'beneficiary_account':request.data.get('beneficiary_account'),
                                    'currency' : request.data.get('Currency'),
                                    'amount':format(float(request.data['debit_amount']), ".2f"),
                                    'beneficiaryname':request.data.get('beneficiaryname'),
                                    'bankname':request.data.get('bankname'),
                                    'swiftcode':request.data.get('swiftcode'),
                                    'city':request.data.get('city'),
                                    'country':request.data.get('country'),
                                    'purpose':request.data.get('purpose'),
                                    'account_type':request.data.get('account_type') if request.data.get('account_type') else "Personal",
                                    'email':request.data.get('email'),
                                    'note':request.data.get('note'),
                                    "ownaccount":int(request.data['ownaccount']),
                                    'box_no':request.data.get('user_box_no'),
                                    'street':request.data.get('user_street'),
                                    'user_city':request.data.get('user_city'),
                                    'state':request.data.get('user_state'),
                                    'user_country':request.data.get('user_country'),
                                    'user_phone':request.data.get('user_phone'),
                                    'invoice':None,
                                    'conversion_fee' : format(self.conversion_fee, ".2f"),
                                    'wire_tr_fee' : format(self.wire_transfer_fee, ".2f"),
                                    'cable_charge' : format(self.cable_charge, ".2f"),
                                    'credit_amount' : format(self.credit_amount, ".2f"),
                                    'debit_amount' : format(debit_amount, ".2f"),
                                    'is_ext_ben':is_ext_ben
                                    }
                                }
                        if context['data'].get("domain"):
                            del context['data']['domain']
            
                        return Response(context)
                elif request.POST.get('ownaccount') == '1' and request.POST.get('has_invoice')=='1':
                    if request.data.get('purpose_note'): 
                        context={
                            'status':1,
                            'message':'Success!',
                            'data':{
                                'fromaccount':request.data.get('debit_account'),
                                'debit_acc_curr_code' : from_currency_code,
                                'currency':request.data.get('beneficiary_account'),
                                'recipient_currency_code' : request.data.get('Currency'),
                                'amount':format(float(request.data['debit_amount']), ".2f"),
                                'beneficiaryname':request.data.get('beneficiaryname'),
                                'bankname':request.data.get('bankname'),
                                'swiftcode':request.data.get('swiftcode'),
                                'city':request.data.get('city'),
                                'country':request.data.get('country'),
                                'purpose':request.data.get('purpose'),
                                'account_type':request.data.get('account_type') if request.data.get('account_type') else "Personal",
                                'purpose_note':request.data.get('purpose_note'),
                                'email':request.data.get('email'),
                                'note':request.data.get('note'),
                                "ownaccount":int(request.data['ownaccount']),
                                'conversion_fee' : format(self.conversion_fee, ".2f"),
                                'wire_tr_fee' : format(self.wire_transfer_fee, ".2f"),
                                'cable_charge' : format(self.cable_charge, ".2f"),
                                'credit_amount' : format(self.credit_amount, ".2f"),
                                'debit_amount' : format(debit_amount, ".2f"),
                                'invoice':True,
                                'invoice_doc' : request.FILES['invoice_doc'].name,
                                'is_ext_ben':is_ext_ben
                                }
                            }
                        if context['data'].get("domain"):
                            del context['data']['domain']
                        return Response(context)
                      
                    else: 
                        context={
                            'status':1,
                            'message':'Success!',
                            'data':{
                                'fromaccount':request.data.get('debit_account'),
                                'debit_acc_curr_code' : from_currency_code,
                                'beneficiary_account':request.data.get('beneficiary_account'),
                                'currency' : request.data.get('Currency'),
                                'amount':format(float(request.data['debit_amount']), ".2f"),
                                'beneficiaryname':request.data.get('beneficiaryname'),
                                'bankname':request.data.get('bankname'),
                                'swiftcode':request.data.get('swiftcode'),
                                'city':request.data.get('city'),
                                'country':request.data.get('country'),
                                'purpose':request.data.get('purpose'),
                                'account_type':request.data.get('account_type') if request.data.get('account_type') else "Personal",
                                'email':request.data.get('email'),
                                'note':request.data.get('note'),
                                "ownaccount":int(request.data['ownaccount']),
                                'conversion_fee' : format(self.conversion_fee, ".2f"),
                                'wire_tr_fee' : format(self.wire_transfer_fee, ".2f"),
                                'cable_charge' : format(self.cable_charge, ".2f"),
                                'credit_amount' : format(self.credit_amount, ".2f"),
                                'debit_amount' : format(debit_amount, ".2f"),
                                'invoice':True,
                                'invoice_doc' : request.FILES['invoice_doc'].name,   
                                'is_ext_ben':is_ext_ben             
                                }
                            }
                        if context['data'].get("domain"):
                            del context['data']['domain']
                        return Response(context)
                                         
                elif request.POST.get('ownaccount') == '0' and request.POST.get('has_invoice')=='1':   
                    if request.data.get('purpose_note'): 
                        context={
                            'status':1,
                            'message':'Success!',
                            'data':{
                                'fromaccount':request.data.get('debit_account'),
                                'debit_acc_curr_code' : from_currency_code,
                                'beneficiary_account':request.data.get('beneficiary_account'),
                                'currency' : request.data.get('Currency'),
                                'amount':format(float(request.data['debit_amount']), ".2f"),
                                'beneficiaryname':request.data.get('beneficiaryname'),
                                'bankname':request.data.get('bankname'),
                                'swiftcode':request.data.get('swiftcode'),
                                'city':request.data.get('city'),
                                'country':request.data.get('country'),
                                'purpose':request.data.get('purpose'),
                                'account_type':request.data.get('account_type') if request.data.get('account_type') else "Personal",
                                'purpose_note':request.data.get('purpose_note'),
                                'email':request.data.get('email'),
                                'note':request.data.get('note'),
                                "ownaccount":int(request.data['ownaccount']),
                                'box_no':request.data.get('user_box_no'),
                                'street':request.data.get('user_street'),
                                'user_city':request.data.get('user_city'),
                                'state':request.data.get('user_state'),
                                'user_country':request.data.get('user_country'),
                                'user_phone':request.data.get('user_phone'),
                                'conversion_fee' : format(self.conversion_fee, ".2f"),
                                'wire_tr_fee' : format(self.wire_transfer_fee, ".2f"),
                                'cable_charge' : format(self.cable_charge, ".2f"),
                                'credit_amount' : format(self.credit_amount, ".2f"),
                                'debit_amount' : format(debit_amount, ".2f"),
                                'invoice':True,
                                'invoice_doc' : request.FILES['invoice_doc'].name,
                                'is_ext_ben':is_ext_ben
                                }
                            }
                        if context['data'].get("domain"):
                            del context['data']['domain']
                        return Response(context)
                    
                    else:
                        context={
                            'status':1,
                            'message':'Success!',
                            'data':{
                                'fromaccount':request.data.get('debit_account'),
                                'debit_acc_curr_code' : from_currency_code,
                                'beneficiary_account':request.data.get('beneficiary_account'),
                                'currency' : request.data.get('Currency'),
                                'amount':format(float(request.data['debit_amount']), ".2f"),
                                'beneficiaryname':request.data.get('beneficiaryname'),
                                'bankname':request.data.get('bankname'),
                                'swiftcode':request.data.get('swiftcode'),
                                'city':request.data.get('city'),
                                'country':request.data.get('country'),
                                'purpose':request.data.get('purpose'),
                                'account_type':request.data.get('account_type') if request.data.get('account_type') else "Personal",
                                'email':request.data.get('email'),
                                'note':request.data.get('note'),
                                "ownaccount":int(request.data['ownaccount']),
                                'box_no':request.data.get('user_box_no'),
                                'street':request.data.get('user_street'),
                                'user_city':request.data.get('user_city'),
                                'state':request.data.get('user_state'),
                                'user_country':request.data.get('user_country'),
                                'user_phone':request.data.get('user_phone'),
                                'conversion_fee' : format(self.conversion_fee, ".2f"),
                                'wire_tr_fee' : format(self.wire_transfer_fee,".2f"),
                                'cable_charge' : format(self.cable_charge, ".2f"),
                                'credit_amount' : format(self.credit_amount, ".2f"),
                                'debit_amount' : format(debit_amount, ".2f"),
                                'invoice':True,
                                'invoice_doc' : request.FILES['invoice_doc'].name,
                                'is_ext_ben':is_ext_ben
                                }
                        }
                        if context['data'].get("domain"):
                            del context['data']['domain']
                        return Response(context)
                       
            else:
                context= {
                   "status": 0,
                    "message" : "validation error",
                    "error": seriliazer.errors,
                    }
                return Response(context)

        elif request.data.get('type')=='otp_send':
            user_account = Useraccounts.objects.get(customer__user=request.user)
            token = self.fetch_token(request)   
            full_name = f"{user_account.firstname} {user_account.lastname}"
            otp_status=OTP()
            if otp_status:
                    context={
                "status": 1,
                "message": 'OTP sent, Please verify!'
                }      
                    return Response(context)
            else:
                    context= {
                        'status' : 0,
                        'message' : f"OTP send failed"  
                    }
                    return Response(context)
            
        elif request.data.get('type')=='otp_validate':
            is_ext_ben = Externalbeneficiaries.objects.filter(Q(accountnumber=request.data.get('beneficiary_account')) | Q(name=request.POST.get('beneficiaryname')),isdeleted=False,createdby=request.user).exists()
            user_account = Useraccounts.objects.get(customer__user=request.user)
            token = self.fetch_token(request)
            seriliazer=InternationalWireTransferSerializer(data=request.data,context={'otp_validate':True})    
            if seriliazer.is_valid():
                amount = round(Decimal(request.data.get('debit_amount')),2)
                from_amount = amount
                conversion_fee = round(from_amount * Decimal(0.5/100),2)
                from_account = Accounts.objects.get(accountno=request.data.get('debit_account'), isdeleted=False)
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
                    currency_conversion = Currencyconversionratescombined.objects.get(fromcurrency__code=from_currency_code,tocurrency__code=request.data.get('Currency'), isdeleted=False)
                    
                    conversionrate = round(currency_conversion.conversionrate,4)

                    try:
                        currency_margin = Currencyconversionmargins.objects.get(fromcurrency__code=from_currency_code,tocurrency__code=request.data.get('Currency'),isdeleted=False)
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
    
                        to_dollar = Currencyconversionratescombined.objects.filter(fromcurrency__code=request.data.get('debit_acc_curr_code'),tocurrency__code=from_currency_code, isdeleted=False)
                        if to_dollar.exists():
                            amount =Decimal(amount) / to_dollar.conversionrate
                        else:
                            amount=0
                            pass
                    conversion_fee = round(from_amount * Decimal(0.5/100),2)
                    conversion_charges(amount)
                conversion_rates(amount, from_currency_code, conversion_fee, self.wire_transfer_fee, self.cable_charge)
                debit_amount = self.wire_transfer_fee + self.cable_charge + self.conversion_fee + from_amount

                if token:
                    try:          
                        otp = Otps.objects.get(code=request.data.get('otp').strip(),
                                        transactiontype='International Wire Transfer',
                                        validated=False,
                                        createdby=request.user,token=token,isdeleted=False)
                        transaction_lock_fn(request,is_lock=False)
                     
                    except Exception as e:
                        logger.info(e)
                        transaction_state = transaction_lock_fn(request)
                        context= {
                            'otp_error' : True,
                            'status' :transaction_state.get("status"),
                            'message' : transaction_state.get("message")
                            }
                        return Response(context)
                    valid_till = datetime.datetime.now()
                    valid_till = valid_till.date().strftime(settings.DATE_FORMAT)
                    valid_date = datetime.datetime.strptime(valid_till, settings.DATE_FORMAT)
                    if valid_date.date() <= otp.validtill:
                        otp.save()
                    else:
                        context= {
                            'otp_error' : True,
                            'status':0,
                            'message' : 'Verification failed, expired otp'
                        }
                        return Response(context)
                    try:
                        customer_type = Customers.objects.get(user=request.user,isdeleted=False).customertype
                        if customer_type == 1:
                            user = Useraccounts.objects.get(customer__user=request.user, isdeleted=False)
                            sender_name = f'{user.firstname} {user.lastname}'
                        else:
                            sender_name = Businessdetails.objects.get(customer__user=request.user,isdeleted=False).companyname

                  
                    except Exception as e:
                       
                        logger.info(e)
                        context= {
                            'status':0,
                            'message' : 'Your Transaction has been declined due to invalid Customer or Business details'
                        }
                        return Response(context)
               
                    try:
                        last_transactionno = Transactions.objects.latest('transactionno').transactionno
                       
                    except Exception as e:
                        logger.info(e)

                        last_transactionno = 10000000
                    def transaction_fn(last_transactionno, from_amount,charge,parent_tr=None,toamount=None, inl_tr=None, commission_charges=None,cable_charge=None,last_transaction=None):
                        try:
                            try:
                                account = Accounts.objects.get(accountno=request.data.get('debit_account'),isdeleted=False)
                            except Exception as e:
                                logger.info(e)
                                context= {
                                    'status':0,
                                    'message':'Your Transaction has been declined due to invalid source account'
                                    }
                                return context
                          
                            if account.balance < Decimal(from_amount):
                                raise Exception()
                            account_balance = account.balance - Decimal(from_amount)
                            account.balance = account_balance
                            account.save()
                        except Exception as e:
                            logger.info(e)
                            context= {
                                'status':0,
                                'message' : 'Your Transaction has been declined due to insufficient fund'
                            }
                            return context
                        if cable_charge:
                            cablecharge_obj = Cablecharges.objects.create(
                                        parenttransaction=parent_transaction,
                                        chargeamount=Decimal(from_amount),
                                        currency=Currencies.objects.get(code=request.data.get('Currency'), isdeleted=False),
                                        createdby=request.user,
                                        transaction=last_transaction
                                    )
                            add_log_action(request, cablecharge_obj, status=f'cable charge created for transaction {parent_transaction.transactionno}', status_id=1)
                            return {
                                'status':1,
                            }
                        else:
                            if commission_charges:
                                try:
                                    toaccount = Accounts.objects.get(user_account__ismaster_account=True,currency__code=from_currency_code,isdeleted=False)
                                   
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
                                                            fromaccount=Accounts.objects.get(accountno=request.data.get('debit_account'), isdeleted=False),
                                                            toaccount=None,
                                                            fromamount=from_amount,
                                                            toamount=toamount,
                                                            conversionrate=self.conversionrate,
                                                            initiatedby=request.user,
                                                            transactiontype=Transactiontypes.objects.get(name='Third Party Transfer'),
                                                            createdby=request.user,
                                                            note=request.data.get('note'),
                                                            recipientname=request.data.get('beneficiaryname'),
                                                            fromaccountbalance=account_balance,
                                                            toaccountbalance=to_account_balance,
                                                            parenttransaction=parent_tr,
                                                            amount_type = charge_type,
                                                            affiliate_fee_percentage = Customers.objects.get(isdeleted=False,user=request.user).outgoingtansactionfee if Customers.objects.get(isdeleted=False,user=request.user).outgoingtansactionfee else 0
                                                            )
                                add_log_action(request, self.transaction, status=f"transaction(International Wire transfer : amount type {self.transaction.amount_type}) created for account {str(self.transaction.fromaccount.accountno)}", status_id=1)
                                if inl_tr:
                                    try:
                                        invoice_doc=InvoiceDocument.objects.create(invoice_doc=request.data.get('invoice_doc'))
                                        invoice_doc.transaction=self.transaction
                                        invoice_doc.save()
                                    except Exception as e:
                                        logger.info(e)
                                    
                                    inl_tr = Internationaltransactions.objects.create(
                                                    transaction=self.transaction,
                                                        bankname=request.data['bankname'],
                                                        swiftcode=request.data['swiftcode'],
                                                        accountnumber=request.data['beneficiary_account'],
                                                        accountholdername=request.data['beneficiaryname'],
                                                        currency=Currencies.objects.get(code=request.data['Currency'], isdeleted=False),
                                                        createdby=request.user,
                                                        city=request.data['city'],
                                                        country=Countries.objects.get(name=request.data['country']),
                                                        email=request.data['email'],
                                                        purpose=Transactionpurposetype.objects.get(transactionpurpose=request.data['purpose'], isdeleted=False),
                                                        other_purpose_note=request.data['purpose_note'] if request.data.get('purpose_note') else None,
                                                        # account_type = request.data['account_type'] if request.data.get('account_type') else "Personal",
                                                        user_box_no=request.data['user_box_no'] if request.data.get('user_box_no') else None,
                                                        user_street=request.data['user_street'] if request.data.get('user_street') else None,
                                                        user_city=request.data['user_city'] if request.data.get('user_city') else None,
                                                        user_state=request.data['user_state'] if request.data.get('user_state') else None,
                                                        user_country=Countries.objects.get(name=request.data['user_country']) if request.data.get('user_country') else None,
                                                        user_phone=request.data['user_phone'] if request.data.get('user_phone') else None
                                    )
                                    add_log_action(request, inl_tr, status=f'international transaction created for account {str(self.transaction.fromaccount.accountno)}', status_id=1)
                            except Exception as e:
                                logger.info(e)
                                context= {
                                    'status':0,
                                    'message':'Your Transaction has been declined due to some error'
                                }
                                return context
                  
                    response = transaction_fn(last_transactionno, request.data['debit_amount'],toamount= self.credit_amount, charge=1, inl_tr= True)
                    if response and not response.get('status'):
                        return Response(response)
                    parent_transaction =  self.transaction
                    charge = 3
                    response = transaction_fn(last_transactionno, self.wire_transfer_fee, charge, parent_transaction,toamount=self.wire_transfer_fee, commission_charges=True)
                   
                    if response and not response.get('status'):
                        return Response(response)
                    charge = 2
                    response = transaction_fn(last_transactionno, self.conversion_fee, charge,parent_transaction,toamount=self.conversion_fee, commission_charges=True)
                    if response and not response.get('status'):
                        return Response(response)
                    last_transaction =  self.transaction

                    response = transaction_fn(last_transactionno, self.cable_charge,parent_transaction, cable_charge=True, last_transaction=last_transaction)
                    if response and not response.get('status'):
                       return Response(response)

                if response and not response.get('status')==1:
                    if response.get('otp_error') == True:
                        context = {
                            'statust':0,
                            'message' : response.get('message')
                        }
                        return Response(context)
               
                    user_account = Useraccounts.objects.get(customer__user=request.user)
                    full_name = f"{user_account.firstname} {user_account.lastname}"
                    debit_acc_curr_code = request.data.get('debit_acc_curr_code')
                    data = {
                        'user' : full_name.title(), 
                        'mail_attach' : True,
                        'error' : 1,
                        'debit_acc_curr_code':debit_acc_curr_code,
                        'message' : response.get('message'),
                        'year':str(datetime.date.today().year),
                    }
                    
                    TransactionMail.transaction_success_or_failure_mail(email=request.user.email,email_data=data,status=False,transaction_type=4)                
                elif response.get('status')==1:
                    customer_account = Useraccounts.objects.get(customer__user=request.user)
                    from_currency_code = from_account.currency.code
                    invoice = f"transaction{parent_transaction.transactionno}.pdf"
                    if data['has_invoice']=='0' and data['ownaccount']=='0':
                            if data['purpose']=='Other Remittance':
                                    if 'purpose_note' in data:
                                        if data['purpose_note']!='':
                                            context ={
                                                'status':1,
                                                'message':"Transaction successfully completed",
                                                'data':{
                                                'wire_transfer' : True,
                                                'wire_transfer_success' : True,
                                                'transactionno':parent_transaction.transactionno,
                                                'transaction_id':parent_transaction.id,
                                                'transaction_datetime_utc':datetime.datetime.utcnow().strftime("%d %b %Y, %-H:%M UTC"),
                                                'sender_name':sender_name,
                                                'from_currency_code':from_currency_code,
                                                'fromaccount':request.data['debit_account'],
                                                'beneficiary_accno':request.data['beneficiary_account'],
                                                'beneficiary_name':request.data['beneficiaryname'],
                                                'amount':format(float(request.data['debit_amount']), ".2f"),
                                                'bank_name':request.data['bankname'],
                                                'swift_code':request.data['swiftcode'],
                                                'city':request.data['city'],
                                                'country':request.data['country'],
                                                'currency':request.data['Currency'],
                                                'purpose_type':request.data['purpose'],
                                                'purpose_note':request.data['purpose_note'],
                                                'note':request.data['note'],
                                                'email':request.data['email'],
                                                "ownaccount":int(request.data['ownaccount']),
                                                'box_no':request.data['user_box_no'] if request.data.get('user_box_no') else None,
                                                'street':request.data['user_street'] if request.data.get('user_street') else None,
                                                'user_city':request.data['user_city'] if request.data.get('user_city') else None,
                                                'state':request.data['user_state'] if request.data.get('user_state') else None,
                                                'user_counrty':request.data['user_country'] if request.data.get('user_country') else None,
                                                'phone_no':request.data['user_phone'] if request.data.get('user_phone') else None,
                                                'conversion_fee' : format(conversion_fee, ".2f"),
                                                'wire_tr_fee' : format(self.wire_transfer_fee,".2f"),
                                                'cable_charge' : format(self.cable_charge, ".2f"),
                                                'debit_amount' : format(debit_amount, ".2f"),
                                                'credit_amount' : format(self.credit_amount, ".2f"),
                                                'is_ext_ben':is_ext_ben,
                                                'has_invoice':int(request.data['has_invoice']),
                                                'invoice':None,
                                                'year':str(datetime.date.today().year),
                                                'filepath':""
                                                    }
                                                }
                                            TransactionMail().transaction_success_or_failure_mail(email=request.user.email,email_data=context['data'],status=True)
                                            if context['data'].get("domain"):
                                                del context['data']['domain']
                                            return Response(context)
                                        
                            elif data['purpose']!='Other Remittance':
                                if 'purpose_note' not in data:
                                    context ={
                                        'status':1,
                                        'message':"Transaction successfully completed ",
                                        'data':{
                                        'wire_transfer' : True,
                                        'wire_transfer_success' : True,
                                        'transactionno':parent_transaction.transactionno,
                                        'transaction_id':parent_transaction.id,
                                        'transaction_datetime_utc':datetime.datetime.utcnow().strftime("%d %b %Y, %-H:%M UTC"),
                                        'sender_name':sender_name,
                                        'from_currency_code':from_currency_code,
                                        'fromaccount':request.data['debit_account'],
                                        'beneficiary_accno':request.data['beneficiary_account'],
                                        'beneficiary_name':request.data['beneficiaryname'],
                                        'amount':format(float(request.data['debit_amount']), ".2f"),
                                        'bank_name':request.data['bankname'],
                                        'swift_code':request.data['swiftcode'],
                                        'city':request.data['city'],
                                        'country':request.data['country'],
                                        'currency':request.data['Currency'],
                                        'purpose_type':request.data['purpose'],
                                        'note':request.data['note'],
                                        'email':request.data['email'],
                                        "ownaccount":int(request.data['ownaccount']),
                                        'box_no':request.data['user_box_no'] if request.data.get('user_box_no') else None,
                                        'street':request.data['user_street'] if request.data.get('user_street') else None,
                                        'user_city':request.data['user_city'] if request.data.get('user_city') else None,
                                        'state':request.data['user_state'] if request.data.get('user_state') else None,
                                        'user_counrty':request.data['user_country'] if request.data.get('user_country') else None,
                                        'phone_no':request.data['user_phone'] if request.data.get('user_phone') else None,
                                        'conversion_fee' : format(conversion_fee, ".2f"),
                                        'wire_tr_fee' : format(self.wire_transfer_fee,".2f"),
                                        'cable_charge' : format(self.cable_charge, ".2f"),
                                        'debit_amount' : format(debit_amount, ".2f"),
                                        'credit_amount' : format(self.credit_amount, ".2f"),
                                        'is_ext_ben':is_ext_ben,
                                        'has_invoice':int(request.data['has_invoice']),
                                        'invoice':None,
                                        'year':str(datetime.date.today().year),
                                        'filepath':""
                                            }
                                        }
                                    TransactionMail().transaction_success_or_failure_mail(email=request.user.email,email_data=context['data'],status=True)
                                    if context['data'].get("domain"):
                                        del context['data']['domain']

                                    return Response(context) 

                    elif request.data['has_invoice']=='0' and request.data['ownaccount']=='1':
                        if 'invoice_doc' not in request.data:
                            if data['purpose']=='Other Remittance':
                                if 'purpose_note' in data:
                                    if data['purpose_note']!='':
                                        context ={
                                            'status':1,
                                            'message':"Transaction successfully completed ",
                                        
                                            'data':{
                                            'wire_transfer' : True,
                                            'wire_transfer_success' : True,
                                            'transactionno':parent_transaction.transactionno,
                                            'transaction_id':parent_transaction.id,
                                            'transaction_datetime_utc':datetime.datetime.utcnow().strftime("%d %b %Y, %-H:%M UTC"),
                                            'sender_name':sender_name,
                                            'from_currency_code':from_currency_code,
                                            'fromaccount':request.data['debit_account'],
                                            'beneficiary_accno':request.data['beneficiary_account'],
                                            'beneficiary_name':request.data['beneficiaryname'],
                                            'amount':format(float(request.data['debit_amount']), ".2f"),
                                            'bank_name':request.data['bankname'],
                                            'swift_code':request.data['swiftcode'],
                                            'city':request.data['city'],
                                            'country':request.data['country'],
                                            'currency':request.data['Currency'],
                                            'purpose_type':request.data['purpose'],
                                            'purpose_note':request.data['purpose_note'],
                                            'note':request.data['note'],
                                            'email':request.data['email'],
                                            "ownaccount":int(request.data['ownaccount']),
                                            'phone_no':request.data['user_phone'] if request.data.get('user_phone') else None,
                                            'conversion_fee' : format(conversion_fee, ".2f"),
                                            'wire_tr_fee' : format(self.wire_transfer_fee,".2f"),
                                            'cable_charge' : format(self.cable_charge, ".2f"),
                                            'debit_amount' : format(debit_amount, ".2f"),
                                            'credit_amount' : format(self.credit_amount, ".2f"),
                                            'is_ext_ben':is_ext_ben,
                                            'has_invoice':int(request.data['has_invoice']),
                                            'invoice':None,
                                            'year':str(datetime.date.today().year),
                                            'filepath':""
                                                }
                                            }
                                        TransactionMail().transaction_success_or_failure_mail(email=request.user.email,email_data=context['data'],status=True)
                                        if context['data'].get("domain"):
                                            del context['data']['domain']
                                        return Response(context)
                                 
                            elif request.data['purpose']!='Other Remittance':
                                if 'purpose_note' not in data:
                                    context ={
                                        'status':1,
                                        'message':"Transaction successfully completed ",
                                        'data':{
                                        'wire_transfer' : True,
                                        'wire_transfer_success' : True,
                                        'transactionno':parent_transaction.transactionno,
                                        'transaction_id':parent_transaction.id,
                                        'transaction_datetime_utc':datetime.datetime.utcnow().strftime("%d %b %Y, %-H:%M UTC"),
                                        'sender_name':sender_name,
                                        'from_currency_code':from_currency_code,
                                        'fromaccount':request.data['debit_account'],
                                        'beneficiary_accno':request.data['beneficiary_account'],
                                        'beneficiary_name':request.data['beneficiaryname'],
                                        'amount':format(float(request.data['debit_amount']), ".2f"),
                                        'bank_name':request.data['bankname'],
                                        'swift_code':request.data['swiftcode'],
                                        'city':request.data['city'],
                                        'country':request.data['country'],
                                        'currency':request.data['Currency'],
                                        'purpose_type':request.data['purpose'],
                                        'note':request.data['note'],
                                        'email':request.data['email'],
                                        "ownaccount":int(request.data['ownaccount']),
                                        'phone_no':request.data['user_phone'] if request.data.get('user_phone') else None,
                                        'conversion_fee' : format(conversion_fee, ".2f"),
                                        'wire_tr_fee' : format(self.wire_transfer_fee,".2f"),
                                        'cable_charge' : format(self.cable_charge, ".2f"),
                                        'debit_amount' : format(debit_amount, ".2f"),
                                        'credit_amount' : format(self.credit_amount, ".2f"),
                                        'is_ext_ben':is_ext_ben,
                                        'has_invoice':int(request.data['has_invoice']),
                                        'invoice':None,
                                        'year':str(datetime.date.today().year),
                                        'filepath':""
                                            }
                                        }
                                    TransactionMail().transaction_success_or_failure_mail(email=request.user.email,email_data=context['data'],status=True)
                                    if context['data'].get("domain"):
                                        del context['data']['domain']

                                    return Response(context)
                    elif data['has_invoice']=='1' and data['ownaccount']=='0':
                        if 'invoice_doc' in data:
                            if data['purpose']=='Other Remittance':
                                if 'purpose_note' in data:
                                    if data['purpose_note']!='':
                                        context ={
                                                    'status':1,
                                                    'message':"Transaction successfully completed ",
                                                'data':{
                                                'wire_transfer' : True,
                                                'wire_transfer_success' : True,
                                                'transactionno':parent_transaction.transactionno,
                                                'transaction_id':parent_transaction.id,
                                                'transaction_datetime_utc':datetime.datetime.utcnow().strftime("%d %b %Y, %-H:%M UTC"),
                                                'sender_name':sender_name,
                                                'from_currency_code':from_currency_code,
                                                'fromaccount':request.data['debit_account'],
                                                'beneficiary_accno':request.data['beneficiary_account'],
                                                'beneficiary_name':request.data['beneficiaryname'],
                                                'amount':format(float(request.data['debit_amount']), ".2f"),
                                                'bank_name':request.data['bankname'],
                                                'swift_code':request.data['swiftcode'],
                                                'city':request.data['city'],
                                                'country':request.data['country'],
                                                'currency':request.data['Currency'],
                                                'purpose_type':request.data['purpose'],
                                                'purpose_note':request.data['purpose_note'],
                                                'note':request.data['note'],
                                                'email':request.data['email'],
                                                "ownaccount":int(request.data['ownaccount']),
                                                'box_no':request.data['user_box_no'] if request.data.get('user_box_no') else None,
                                                'street':request.data['user_street'] if request.data.get('user_street') else None,
                                                'user_city':request.data['user_city'] if request.data.get('user_city') else None,
                                                'state':request.data['user_state'] if request.data.get('user_state') else None,
                                                'user_counrty':request.data['user_country'] if request.data.get('user_country') else None,
                                                'phone_no':request.data['user_phone'] if request.data.get('user_phone') else None,
                                                'conversion_fee' : format(conversion_fee, ".2f"),
                                                'wire_tr_fee' : format(self.wire_transfer_fee,".2f"),
                                                'cable_charge' : format(self.cable_charge, ".2f"),
                                                'debit_amount' : format(debit_amount, ".2f"),
                                                'credit_amount' : format(self.credit_amount, ".2f"),
                                                'is_ext_ben':is_ext_ben,
                                                'invoice':True,
                                                'invoice_doc' : request.FILES['invoice_doc'].name,
                                                'year':str(datetime.date.today().year),
                                                'filepath':""
                                                    }
                                                }
                                        TransactionMail().transaction_success_or_failure_mail(email=request.user.email,email_data=context['data'],status=True)
                                        if context['data'].get("domain"):
                                            del context['data']['domain']
                                        return Response(context)   
                                        
                            elif data['purpose']!='Other Remittance':
                                if 'purpose_note' not in data: 
                                    context ={
                                        'status':1,
                                        'message':"Transaction successfully completed ",
                                        
                                        # 'test_user' : customer_account.test_account,
                                        'data':{
                                        'wire_transfer' : True,
                                        'wire_transfer_success' : True,
                                        'transactionno':parent_transaction.transactionno,
                                        'transaction_id':parent_transaction.id,
                                        'transaction_datetime_utc':datetime.datetime.utcnow().strftime("%d %b %Y, %-H:%M UTC"),
                                        'sender_name':sender_name,
                                        'from_currency_code':from_currency_code,
                                        'fromaccount':request.data['debit_account'],
                                        'beneficiary_accno':request.data['beneficiary_account'],
                                        'beneficiary_name':request.data['beneficiaryname'],
                                        'amount':format(float(request.data['debit_amount']), ".2f"),
                                        'bank_name':request.data['bankname'],
                                        'swift_code':request.data['swiftcode'],
                                        'city':request.data['city'],
                                        'country':request.data['country'],
                                        'currency':request.data['Currency'],
                                        'purpose_type':request.data['purpose'],
                                        'note':request.data['note'],
                                        'email':request.data['email'],
                                        "ownaccount":int(request.data['ownaccount']),
                                        'box_no':request.data['user_box_no'] if request.data.get('user_box_no') else None,
                                        'street':request.data['user_street'] if request.data.get('user_street') else None,
                                        'user_city':request.data['user_city'] if request.data.get('user_city') else None,
                                        'state':request.data['user_state'] if request.data.get('user_state') else None,
                                        'user_counrty':request.data['user_country'] if request.data.get('user_country') else None,
                                        'phone_no':request.data['user_phone'] if request.data.get('user_phone') else None,
                                        'conversion_fee' : format(conversion_fee, ".2f"),
                                        'wire_tr_fee' : format(self.wire_transfer_fee,".2f"),
                                        'cable_charge' : format(self.cable_charge, ".2f"),
                                        'debit_amount' : format(debit_amount, ".2f"),
                                        'credit_amount' : format(self.credit_amount, ".2f"),
                                        'is_ext_ben':is_ext_ben,
                                        'invoice':True,
                                        'invoice_doc' : request.FILES['invoice_doc'].name,
                                        'year':str(datetime.date.today().year),
                                        'filepath':""
                                            }
                                        }
                                    TransactionMail().transaction_success_or_failure_mail(email=request.user.email,email_data=context['data'],status=True)
                                    if context['data'].get("domain"):
                                        del context['data']['domain']
                                    return Response(context)               
                    elif data['has_invoice']=='1' and data['ownaccount']=='1':
                        if 'invoice_doc' in data:
                            if data['purpose']=='Other Remittance':
                                if 'purpose_note' in data:
                                    if data['purpose_note']!='':
                                        context ={
                                            'status':1,
                                            'message':"Transaction successfully completed ",
                                            'data':{
                                            'wire_transfer' : True,
                                            'wire_transfer_success' : True,
                                            'transactionno':parent_transaction.transactionno,
                                            'transaction_id':parent_transaction.id,
                                            'transaction_datetime_utc':datetime.datetime.utcnow().strftime("%d %b %Y, %-H:%M UTC"),
                                            'sender_name':sender_name,
                                            'from_currency_code':from_currency_code,
                                            'fromaccount':request.data['debit_account'],
                                            'beneficiary_accno':request.data['beneficiary_account'],
                                            'beneficiary_name':request.data['beneficiaryname'],
                                            'amount':format(float(request.data['debit_amount']), ".2f"),
                                            'bank_name':request.data['bankname'],
                                            'swift_code':request.data['swiftcode'],
                                            'city':request.data['city'],
                                            'country':request.data['country'],
                                            'currency':request.data['Currency'],
                                            'purpose_type':request.data['purpose'],
                                            'purpose_note':request.data['purpose_note'],
                                            'note':request.data['note'],
                                            'email':request.data['email'],
                                            "ownaccount":int(request.data['ownaccount']),
                                            'phone_no':request.data['user_phone'] if request.data.get('user_phone') else None,
                                            'conversion_fee' : format(conversion_fee, ".2f"),
                                            'wire_tr_fee' : format(self.wire_transfer_fee,".2f"),
                                            'cable_charge' : format(self.cable_charge, ".2f"),
                                            'debit_amount' : format(debit_amount, ".2f"),
                                            'credit_amount' : format(self.credit_amount, ".2f"),
                                            'is_ext_ben':is_ext_ben,
                                            'invoice':True,
                                            'invoice_doc' : request.FILES['invoice_doc'].name,
                                            'year':str(datetime.date.today().year),
                                            'filepath':""
                                                }
                                            }
                                    TransactionMail().transaction_success_or_failure_mail(email=request.user.email,email_data=context['data'],status=True)
                                    if context['data'].get("domain"):
                                        del context['data']['domain']
                                    return Response(context)   
                                
                            elif data['purpose']!='Other Remittance':
                                if 'purpose_note' not in data: 
                                    context ={
                                        'status':1,
                                        'message':"Transaction successfully completed ",
                                        'data':{
                                        'wire_transfer' : True,
                                        'wire_transfer_success' : True,
                                        'transactionno':parent_transaction.transactionno,
                                        'transaction_id':parent_transaction.id,
                                        'transaction_datetime_utc':datetime.datetime.utcnow().strftime("%d %b %Y, %-H:%M UTC"),
                                        'sender_name':sender_name,
                                        'from_currency_code':from_currency_code,
                                        'fromaccount':request.data['debit_account'],
                                        'beneficiary_accno':request.data['beneficiary_account'],
                                        'beneficiary_name':request.data['beneficiaryname'],
                                        'amount':format(float(request.data['debit_amount']), ".2f"),
                                        'bank_name':request.data['bankname'],
                                        'swift_code':request.data['swiftcode'],
                                        'city':request.data['city'],
                                        'country':request.data['country'],
                                        'currency':request.data['Currency'],
                                        'purpose_type':request.data['purpose'],
                                        'note':request.data['note'],
                                        'email':request.data['email'],
                                        "ownaccount":int(request.data['ownaccount']),
                                        'phone_no':request.data['user_phone'] if request.data.get('user_phone') else None,
                                        'conversion_fee' : format(conversion_fee, ".2f"),
                                        'wire_tr_fee' : format(self.wire_transfer_fee,".2f"),
                                        'cable_charge' : format(self.cable_charge, ".2f"),
                                        'debit_amount' : format(debit_amount, ".2f"),
                                        'credit_amount' : format(self.credit_amount, ".2f"),
                                        'invoice':True,
                                        'invoice_doc' : request.FILES['invoice_doc'].name,
                                        'is_ext_ben':is_ext_ben,
                                        'year':str(datetime.date.today().year),
                                        'filepath':""
                                            }
                                        }
                                TransactionMail().transaction_success_or_failure_mail(email=request.user.email,email_data=context['data'],status=True)
                                if context['data'].get("domain"):
                                    del context['data']['domain']
                                    return Response(context)    

                    else:
                        context= {
                            'status':0,
                            'message' : 'Your Transaction has been declined due to Security reason'
                        }
                        return Response(context)       

            else:
                context= {
                    "status": 0,
                    "message" : "validation error",
                    "error": seriliazer.errors,
                    }
                return Response(context)


        elif request.data.get("type") == "save_ben":  
            external_ben, status = Externalbeneficiaries.objects.get_or_create(
                name = request.data['beneficiaryname'],
                accountnumber = request.data['beneficiary_account'],
                currency = Currencies.objects.get(code=request.data['Currency']),
                swiftcode = request.data['swiftcode'],
                country = Countries.objects.get(name=request.data['country']),
                city = request.data['city'],
                bankname = request.data['bankname'],
                createdby = request.user,
                account_type = request.data['account_type'] if request.data['account_type'] else "Personal",
                customer = Customers.objects.get(user=request.user)
            )
            external_ben.email = request.data['email']
            external_ben.save()
            context={
                'status':1,
                'Message':'Successfully added beneficiary account'
            }
            return Response(context)


        elif request.data.get("type") == "export_pdf":
            user_account = Useraccounts.objects.get(customer__user=request.user)
            try:
                transactionno = request.data.get("transactionno")
                seriliazer = InternationalWireTransferSerializer(data=request.data, context={"email_send": True})
                if seriliazer.is_valid():
                    transaction = Transactions.active.get(transactionno=transactionno, amount_type="Net Amount")
                    invoice = f"transaction{ transaction.transactionno}.pdf"
                    file = f"invoices/{invoice}"
                    filepath = settings.MEDIA_ROOT + settings.MEDIA_URL + file
                    if transaction.fromaccount.user_account.customer.customertype == 1:
                        full_name = f"{transaction.fromaccount.user_account.firstname} {transaction.fromaccount.user_account.lastname}"
                    else:
                        full_name =  Businessdetails.objects.get(customer__user=request.user, isdeleted=False).companyname
                    transaction_amounts = self.get_transaction_amounts(transaction, from_amount=True)
                    isExist = self.check_cloudfile_exists(file)
                    if not isExist:
                        context = {
                            "wire_transfer": True,
                            "transactionno": transaction.transactionno,
                            'transaction_id':parent_transaction.id,
                            "transaction_datetime_utc": transaction.createdon.strftime("%d %b %Y, %-H:%M UTC"),
                            "sender_name": full_name,
                            "from_currency_code": transaction.fromaccount.currency.code,
                            "fromaccount": transaction.fromaccount.accountno,
                            "beneficiary_accno": transaction.inltransaction_tr.all()[0].accountnumber,
                            "beneficiary_name": transaction.inltransaction_tr.all()[0].accountholdername,
                            "bank_name": transaction.inltransaction_tr.all()[0].bankname,
                            "swift_code": transaction.inltransaction_tr.all()[0].swiftcode,
                            "city": transaction.inltransaction_tr.all()[0].city,
                            "country": transaction.inltransaction_tr.all()[0].country.shortform,
                            "currency": transaction.inltransaction_tr.all()[0].currency.code,
                            "purpose_type": transaction.inltransaction_tr.all()[0].purpose.transactionpurpose,
                            "purpose_note": transaction.inltransaction_tr.all()[0].other_purpose_note if transaction.inltransaction_tr.all()[0].other_purpose_note else "",
                            "email": transaction.inltransaction_tr.all()[0].email,
                            "box_no": transaction.inltransaction_tr.all()[0].user_box_no if transaction.inltransaction_tr.all()[0].user_box_no else None,
                            "street": transaction.inltransaction_tr.all()[0].user_street if transaction.inltransaction_tr.all()[0].user_street else None,
                            "user_city": transaction.inltransaction_tr.all()[0].user_city if transaction.inltransaction_tr.all()[0].user_city else None,
                            "state": transaction.inltransaction_tr.all()[0].user_state if transaction.inltransaction_tr.all()[0].user_state else None,
                            "user_counrty": transaction.inltransaction_tr.all()[0].user_country.shortform if transaction.inltransaction_tr.all()[0].user_country else None,
                            "phone_no": transaction.inltransaction_tr.all()[0].user_phone if transaction.inltransaction_tr.all()[0].user_phone else None,
                            "amount": transaction_amounts.get("net_amount"),
                            "conversion_fee": transaction_amounts.get("conversion_fee"),
                            "wire_tr_fee": transaction_amounts.get("wire_fee"),
                            "cable_charge": transaction_amounts.get("cable_charge"),
                            "debit_amount": self.get_debit_amount(transaction, "True"),
                            "credit_amount": round(transaction.toamount, 2),
                            "note": transaction.note,
                            "year": str(datetime.date.today().year),
                        }
                        context.update({"invoice": self.get_transaction_receipt(transaction)})
                        file = render_pdf("accounts/wire_transfer/transaction-pdf-template.html",context,invoice,)
                    content = {
                        "status": 1,
                        "data": settings.AWS_S3_BUCKET_URL + "invoices/" + invoice,
                        "message": "success",
                    }
                    if request.data.get("send_mail"):
                        context = {
                            "user": f"{user_account.firstname} {user_account.lastname}".title(),
                            "mail_attach": True,
                            "from_currency_code": transaction.fromaccount.currency.code,
                            "amount": transaction_amounts.get("net_amount"),
                            "year": str(datetime.date.today().year),
                        }
                        self.transaction_success_or_failure_mail(
                            email=request.user.email,
                            email_data=context,
                            status=True,
                            attach=filepath,
                        )
                        content["message"] = "Email sent successfully!"
                        content["data"] = {}
                    return Response(content, status=status.HTTP_200_OK)
                else:
                    context = {
                        "status": 0,
                        "message": "validation error",
                        "error": seriliazer.errors,
                    }
                return Response(context)
            except Exception as e:
                logger.info(e)
                context = {
                    "status": 0,
                    "message": "validation error",
                    "error": {"transactionno": ["This field is required."]},
                }
                return Response(context)
                  

        elif request.data.get('type')== "resend_otp":
                user_from_token = request.user
                user_account = Useraccounts.objects.get(customer__user=request.user)
                full_name = f"{user_account.firstname} {user_account.lastname}"
                token = self.fetch_token(request)   
                
                def validate():
                    if token:
                        try:
                            otp_status=OTP()
                            if otp_status:
                                return {
                                'status' : 1,
                                'message' : f"OTP resent, Please verify!",
                                }
                            else:

                                return {
                                'status' : 0,
                                'message' : f"Something went wrong! Please try again."
                            }
                        except Exception as e:
                            logger.info(e)
                            return{
                                    'status':0,
                                    'message':'Something went wrong! Please try again'
                                    }
                response = validate()
                return Response(response) 
            
    

class AccountToAccountTransferViewAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated,TransactionPermission]

    def post(self, request):
        serializer = AccountToAccountSerilaizer(data=request.data)
        if serializer.is_valid():
            context = {}
            ben_acc_number = request.data.get('beneficiary_accountnumber')

            if ben_acc_number in list(
                    Accounts.objects.filter(accountno=ben_acc_number, isdeleted=False,
                                            createdby=request.user).values_list(
                        'accountno', flat=True)):
                context = {
                    'message': 'Debit and credit account cannot be from same user',
                    'status': False,
                }
                return Response(context)
            note=request.data.get('note')
            if not checkNonAsciiChracters(note):
                context = {
                    'message': 'Fancy Characters are not allowed',
                    'status': False,
                }
                return Response(context)
            debit_account_number = request.data.get('debit_account')
            try:
                debit_account = Accounts.objects.get(accountno=debit_account_number)
            except Exception as e:
                logger.info(e)
                context = {
                    'message': 'Invalid debit account!',
                    'status': False,
                }
                # return redirect('accTransaction')
                return Response(context)
            if float(request.data.get('amount')) < float(debit_account.balance):
                beneficiary_account_number = request.data.get('beneficiary_accountnumber')
                try:
                    internal_beneficiary = Internalbeneficiaries.objects.get(createdby=request.user,
                                                                             account=Accounts.objects.get(
                                                                                 accountno=beneficiary_account_number),
                                                                             isdeleted=False)
                    beneficiary_name = internal_beneficiary.receivername
                except Exception as e:
                    logger.info(e)
                    beneficiary_name = ''
                benefiary_account = Accounts.objects.get(accountno=beneficiary_account_number)
                from_amount = round(Decimal(request.data.get('amount')), 2)
                if debit_account.currency.code == benefiary_account.currency.code:
                    conversion_fee = Decimal(0.00)
                else:
                    conversion_fee = round(from_amount * Decimal(0.5 / 100), 2)
                try:
                    currency_conversion = Currencyconversionratescombined.objects.get(
                        fromcurrency__code=debit_account.currency.code,
                        tocurrency__code=benefiary_account.currency.code,
                        isdeleted=False)
                except Exception as e:
                    logger.info(e)
                    context = {
                        'message': 'Having trouble with selected account! Please try with another.',
                        'status': False,
                    }
                    return Response(context)
                conversionrate = round(currency_conversion.conversionrate, 4)
                try:
                    currency_margin = Currencyconversionmargins.objects.get(
                        fromcurrency__code=debit_account.currency.code,
                        tocurrency__code=benefiary_account.currency.code,
                        isdeleted=False)
                    margin_rate = currency_margin.marginpercent
                    conversionrate = conversionrate - (conversionrate * Decimal(float(margin_rate) / 100))
                except Exception as e:
                    logger.info(e)
                    pass

                credit_amount = round(from_amount * conversionrate, 2)
                debit_amount = from_amount + conversion_fee
                if debit_amount > float(debit_account.balance):
                    context = {
                        'message': 'Insufficient Balance',
                        'status': False,
                    }
                    return Response(context)
                context['status']=True
                context['accounttoaccounttransfer'] = ({
                    'beneficiary_accountnumber': ben_acc_number,
                    'currency_code_beneficiary': benefiary_account.currency.code,
                    'debit_account_number':debit_account_number,
                    'currency_code_debit': debit_account.currency.code,
                    'beneficiary_name': beneficiary_name,
                    'conversion_fee': format(conversion_fee, '.2f'),
                    'credit_amount': format(credit_amount, '.2f'),
                    'debit_amount': format(debit_amount, '.2f'),
                    'net_amount': format(from_amount, '.2f'),
                    'note': note,
                    'conversionrate' : format(conversionrate,'.2f'),
                })
                context['message']='successfully'
                return Response(context)
            else:
                context = {
                    'message': 'Insufficient Balance',
                    'status': False,
                }
                # return redirect('accTransaction')
                return Response(context)
        else:
            context={}
            context['status']=False
            context['errors']=serializer.errors

            context['message']='Invalid data'
            return Response(context)


class AccountToAccountOTPSendAPIView(APIView,APIV1UtilMixins):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated,TransactionPermission]

    def post(self, request):

        if request.data.get('type') == 'otpresend':
            token = self.fetch_token(request)
            user_account = Useraccounts.objects.get(customer__user=request.user)
            full_name = f"{user_account.firstname} {user_account.lastname}"

            otp_status = OTP()
            if otp_status:
                context = {
                    'status':True,
                    'message': 'OTP resent, Please verify!'
                }
                return Response(context)
            else:
                context = {
                    'status': False,
                    'message': 'Could not send OTP'
                }
                return Response(context)

        elif request.data.get('sendOtp') == 'sendOtp':
            token = self.fetch_token(request)
            user_account = Useraccounts.objects.get(customer__user=request.user)
            full_name = f"{user_account.firstname} {user_account.lastname}"
            otp_status = OTP()
            if otp_status:
                context = {
                    'status': True,
                    'message': 'OTP sent, Please verify!'
                }

                return Response(context)
            else:
                context = {
                    'status': False,
                    'message': 'Could not send OTP'
                }
                return Response(context)


class ReferFriendView(APIView, CustomMail):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            firstname= request.data.get('firstname')
            lastname= request.data.get('lastname')
            email= request.data.get('email')
            error_res={"status":False,
            "message":"validation error"}
            d={}
            attrs_dict={"firstname":firstname, "lastname":lastname,"email":email}
            none_list=[]
            for i in attrs_dict:
                if not attrs_dict[i]:
                    none_list.append(i)
            if len(none_list) != 0:
                for i in none_list:
                    d[i]=["This field may not be blank"]
                error_res["error"]= d

                return Response(error_res)
            email_regex= r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            if email and not re.search(email_regex, email):
                return Response({
                    "status":False,
                    "message":"validaton error",
                    "error":{"email":["Invalid Email format"]}
                })
            elif not checkNonAsciiChracters([firstname]):
                return Response({
                    "status":False,
                    "message":"validaton error",
                    "error":{"firstname":["Fancy Charecters are not allowed"]}
                })
            elif not checkNonAsciiChracters([lastname]):
                return Response({
                    "status":False,
                    "message":"validaton error",
                    "error":{"lastname":["Fancy Charecters are not allowed"]}
                })
            user_account = Useraccounts.objects.get(customer__user=request.user, isdeleted=False)

            serializer= ReferfrndSerializer(data= request.data)
            if serializer.is_valid():
                subject = 'Invitation from Entrebiz' 
                refer_link = f"{settings.CURRENT_DOMAIN}/refer/{user_account.referencecode}"
                firstName= serializer.validated_data['firstname']
                lastName= serializer.validated_data['lastname']
                email=serializer.validated_data['email']
                content = f"{refer_link}"
                full_name = f"{firstName} {lastName}"
                self.send_refferal_mail(full_name, subject,content,email)

                return Response({
                    "status":True,
                    "message":"Invitation mail sent successfully."
                })
        
            return Response({
                    "error":serializer.errors,
                    "status":False
                })
        except Exception as e:
            logger.info(e)
            return Response({
                    "error":"Error while inviting",
                    "status":False
                }) 


    def get(self, request):
        try:
            reference_code = randomword(10)
            user_account = Useraccounts.objects.get(customer__user=request.user, isdeleted=False)
            if not user_account.referencecode:
                user_account.referencecode = reference_code
                user_account.save()
            refer_link = f"{settings.CURRENT_DOMAIN}/refer/{user_account.referencecode}"
            return Response({
                "status":True,
                "data":{refer_link},
                "message":"success"
            })
        except Exception as e:
            logger.info(e)
            return Response({"message":"Error occured",
            "status":False})

class ReferalApiView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user_account = Useraccounts.objects.get(customer__user=request.user,isdeleted=False)
            refferee= Useraccounts.active.filter(referred_by= user_account, show_referee= True)
            d=[]
            emails=""
            for useraccount in refferee:
                primary_balance=0
                secondary_balance=0
                primary_currency=""
                secondary_currency=""
                emails+= (useraccount.customer.user.email)
                ob= useraccount.customer
                bc= Businessdetails.objects.filter(customer= ob, isdeleted= False).first()
                
                if bc:
                    cpnyname=bc.companyname
                else:
                    cpnyname= None
                if useraccount.added_by:
                    customer = useraccount.added_by
                else:
                    customer = useraccount.customer
                acc= Accounts.objects.filter(user_account__customer= customer)
                for account in acc:
                    if account.isprimary == 1:																																								
                        primary_currency+= " "+account.currency.code
                        primary_balance+= account.balance
                    elif account.isprimary == 2:
                        secondary_balance+= account.balance
                        secondary_currency+= " "+account.currency.code
                d.append({"email":emails,
                "primary_balance":str(format(primary_balance, '.2f'))+primary_currency,
                "secondary_balance":str(format(secondary_balance, '.2f'))+secondary_currency,
                "company_name":cpnyname})
                emails=""            
            return Response({"status":True,
                "Data":d,
                "message":"success"})

        except Exception as e:
            logger.info(e)
            return Response({"status":False,
                "message":"Error while getting"})



class AccountToAccountOTPValidateAPIView(APIView,APIV1UtilMixins,TransactionMail,FindAccount):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated,TransactionPermission]

    def post(self, request):
        serializer = AccountToAccountValidateSerilaizer(data=request.data)
        if serializer.is_valid():
            try:
                token = self.fetch_token(request)
                def validation_fn():
                    if not token:
                        return {
                            'status': False,
                            'error': 'Your Transaction has been declined due to Security reason'
                        }
                    try:
                        otp=request.POST.get('otp')
                        otp = Otps.objects.get(code=otp,
                                               transactiontype='Account to Account Transfer',
                                               validated=False,
                                               createdby=request.user, token=token)
                        transaction_lock_fn(request, is_lock=False)
                    except Exception as e:
                        logger.info(e)
                        transaction_state = transaction_lock_fn(request)
                        return {
                            'status': False,
                            'otp_error': True,
                            'transcition_lock_status_data':transaction_state.get("status"),
                            'error': transaction_state.get("message")
                        }
                    valid_till = datetime.datetime.now()
                    valid_till = valid_till.date().strftime(settings.DATE_FORMAT)
                    valid_date = datetime.datetime.strptime(valid_till, settings.DATE_FORMAT)

                    if valid_date.date() <= otp.validtill:
                        otp.validated = True
                        otp.save()
                        try:
                            debit_account_number = request.data.get('debit_account_number')
                            try:
                                debit_account = Accounts.objects.get(
                                    accountno=debit_account_number
                                    )
                                debit_account_code=debit_account.currency.code
                            except Exception as e:
                                return {
                                    'status':False,
                                    'message':'Invalid debit account',
                                    'debit_account':True
                                }
                            beneficiary_account_number = request.data.get('beneficiary_accountnumber')
                            try:
                                credit_account = Accounts.objects.get(
                                    accountno=beneficiary_account_number
                                )
                                beneficiary_code= credit_account.currency.code
                            except Exception as e:
                                return {

                                    'status':False,
                                    'message':'invalid credit account',
                                    'credit_account':True
                                }
                            note = request.data.get('note')
                            try:
                                internal_beneficiary = Internalbeneficiaries.objects.get(createdby=request.user,
                                                                                         account=Accounts.objects.get(
                                                                                             accountno=beneficiary_account_number),
                                                                                         isdeleted=False)
                                beneficiary_name = internal_beneficiary.receivername
                            except Exception as e:
                                logger.info(e)
                                beneficiary_name = ''
                            debit_amount = Decimal(request.data.get('debit_amount'))
                            net_amount = Decimal(request.data.get('net_amount'))
                            conversion_fee = Decimal(request.data.get('conversion_fee'))
                            credit_amount = Decimal(request.data.get('credit_amount'))
                            db_account_balance = debit_account.balance
                            if db_account_balance < debit_amount:
                                # raise Exception()
                                return {
                                    'status': False,
                                    'error': 'Your Transaction has been declined due to insufficient fund'
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

                            def create_transaction(transactionno, debit_account, credit_account, fromamount, toamount,
                                                   debit_balance, credit_balance, amount_type, parent_transaction=None):
                                transaction_obj = Transactions.objects.create(
                                    transactionno=transactionno,
                                    fromaccount=debit_account,
                                    toaccount=credit_account,
                                    fromamount=fromamount,
                                    toamount=toamount,
                                    conversionrate = request.data.get('conversionrate'),
                                    transactiontype=Transactiontypes.objects.get(name='Acccount To Account Transfer'),
                                    createdby=request.user,
                                    note=note,
                                    recipientname=beneficiary_name,
                                    fromaccountbalance=debit_balance,
                                    toaccountbalance=credit_balance,
                                    amount_type=amount_type,
                                    parenttransaction=parent_transaction
                                )
                                add_log_action(request, transaction_obj,
                                               status=f"transaction(Account to Account : amount type {transaction_obj.amount_type}) created for account {str(transaction_obj.fromaccount.accountno)}",
                                               status_id=1)
                                return transaction_obj

                            try:
                                net_amount = net_amount
                                amount_type = "Net Amount"
                                parent_transaction = create_transaction(transactionno, debit_account, credit_account,
                                                                        net_amount,
                                                                        credit_amount,
                                                                        debit_accountbalance, credit_accountbalance,
                                                                        amount_type)
                            except Exception as e:
                                logger.info(e)
                                return {
                                    'status': False,
                                    'error': 'Something went wrong! Please try again.'
                                }
                            try:
                                master_credit_account, converted_conversion_fee = self.find_master_account_convert_amount(
                                    debit_account, conversion_fee, debit_account.user_account.test_account)
                                debit_account.balance -= Decimal(conversion_fee)
                                master_credit_account.balance += Decimal(converted_conversion_fee)
                                debit_account.save()
                                master_credit_account.save()
                                debit_balance = debit_account.balance
                                master_credit_balance = master_credit_account.balance

                                amount_type = "Conversion Fee"
                                create_transaction(transactionno, debit_account, master_credit_account, conversion_fee,
                                                   converted_conversion_fee,
                                                   debit_balance, master_credit_balance, amount_type, parent_transaction)

                            except Exception as e:
                                logger.info(e)
                                return {
                                    'status': False,
                                    'error': 'Something went wrong! Please try again.'
                                }
                            # send success mail here
                            return {
                                'status': True,
                                'transactionnumber': transactionno,
                                'transaction_id': parent_transaction.id,
                                'beneficiary_code':beneficiary_code,
                                'debit_account_code':debit_account_code,
                                'debit_account_number':debit_account_number,
                                'beneficiary_account_number':beneficiary_account_number,
                                'beneficiary_name':beneficiary_name,
                                'net_amount':net_amount,
                                'conversion_fee':conversion_fee,
                                'debit_amount':debit_amount,
                                'credit_amount':credit_amount,
                                'note':note
                            }
                            # return redirect('accSuccess', request.session['token'])
                        except Exception as e:
                            logger.info(e)
                            context={}
                            return Response(context)
                    else:
                        return {
                            'status': False,
                            'error': 'Your Transaction has been declined due to Expired OTP you entered'
                        }

                response = validation_fn()
                if response.get('credit_account')==True:
                    context={
                        'status':False,
                        'message':'Invalid beneficiary account!'
                    }
                    return Response(context)
                if response.get('debit_account')==True:
                    context={
                        'status':False,
                        'message':'Invalid debit account!'
                    }
                    return Response(context)
                if response.get('otpnull')==True:
                    context={}
                    context['status'] = False
                    context['message'] = 'Please provide otp for validations'
                    return Response(context)

                if response and not response.get('status'):
                    # SEND FAILURE EMAIL HERE
                    # messages.error(request,response.get('error'))
                    request.session['Otpfailuremsg'] = response.get('error')
                    if response.get('otp_error') == True:
                        context = {}
                        context['status']=response.get('transcition_lock_status_data')
                        context['message'] = response.get('error')
                        return Response(context)
                    user_account = Useraccounts.objects.get(customer__user=request.user)
                    full_name = f"{user_account.firstname} {user_account.lastname}"
                    context = {
                        'error': True,
                        'message': response.get('error'),
                        'year': str(datetime.date.today().year),
                        'user': full_name
                    }
                    transaction_mail_status = TransactionMail().transaction_success_or_failure_mail(
                        email=request.user.email, email_data=context, status=False)
                    return Response(context)

                elif response.get('status'):
                    data={
                        'acc_acc_transfer': True,
                        'transaction_number': response.get('transactionnumber'),
                        'transaction_id': response.get('transaction_id'),
                        'transactionno': response.get('transactionnumber'),
                        'debit_account': response.get('debit_account_number'),
                        'fromaccount': response.get('debit_account_number'),
                        'debit_currency_code': response.get('debit_account_code'),
                        'from_currency_code': response.get('debit_account_code'),
                        'credit_account': response.get('beneficiary_account_number'),
                        'credit_currency_code': response.get('beneficiary_code'),
                        'beneficiary_accno':response.get('beneficiary_account_number'),
                        'beneficiary_name': response.get('beneficiary_name'),
                        'net_amount': str(response.get('net_amount')),
                        'amount':str(response.get('net_amount')),
                        'conversion_fee': str(response.get('conversion_fee')),
                        'debit_amount': str(response.get('debit_amount')),
                        'credit_amount': str(response.get('credit_amount')),
                        'note': response.get('note'),
                        'Date_and_Time': datetime.datetime.utcnow().strftime("%d %b %Y, %-H:%M UTC"),
                        'transaction_datetime_utc': datetime.datetime.utcnow().strftime("%d %b %Y, %-H:%M UTC"),
                        'year': str(datetime.date.today().year),
                    }
                    context = {
                        'status':1,
                        'data':data,
                        'message': "Transaction successfully completed",
                    }
                    transaction_mail_status = TransactionMail().transaction_success_or_failure_mail(
                        email=request.user.email, email_data=context['data'], status=True, attach=None)
                    if context['data']['domain']:
                        del context['data']['domain']
                    context['data']['file'] = ''
                    return Response(context)

            except Exception as e:
                logger.info(e)
                # logout
                # SEND FAILURE EMAIL HERE
                user_account = Useraccounts.objects.get(customer__user=request.user)
                full_name = f"{user_account.firstname} {user_account.lastname}"
                context = {
                    'user': full_name,
                    'year': str(datetime.date.today().year),
                }
                send_email = TransactionMail().transaction_success_or_failure_mail(email=request.user.email,
                                                                                   email_data=context, status=False,
                                                                                   attach=None)
                if send_email and request.user:
                    # messages.error(request,'Verification failed, wrong user or otp')
                    return Response(context)
                else:
                    return Response(context)
        else:
            context={}
            context['status'] = False
            context['error']=serializer.errors
            context['message']='Transaction Not Allowed!'
            return Response(context)

class AccountToAccountSuccessEmailAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated,TransactionPermission]

    def post(self,request):
        serializer=AccountToAccountEmailSerializer(data=request.data)
        if serializer.is_valid():
            transaction_number=request.data.get('transaction_number')
            try:
                transaction = Transactions.objects.get(transactionno=transaction_number, amount_type ='Net Amount')
                user_account = Useraccounts.objects.get(customer__user=request.user)
                full_name = f"{user_account.firstname} {user_account.lastname}"
                email_data = {
                    'mail_attach': True,
                    'from_currency_code':transaction.fromaccount.currency.code,
                    'amount':format(transaction.fromamount,'.2f'),
                    'year': str(datetime.date.today().year),
                    'user': full_name
                }
                context = {
                    'status':True,
                    'data':email_data,
                    'message':'Email sent successfully!'
                }
                transaction_mail_status = TransactionMail().transaction_success_or_failure_mail(email=request.user.email,
                                                                                                email_data=context['data'],status=True)
                if context['data']['domain']:
                    del context['data']['domain']
                return Response(context)
            except Exception as e:
                context={
                    'status':False,
                    'message':'Invalid transaction number'
                }
                return Response(context)
        else:
            context={}
            context['status']=False
            context['errors']=serializer.errors
            context['message']='Not allowed'
            return Response(context)



class NormalUserCreateView(APIView, ConfirmYourMail):

    def post(self, request):

        username= randomword(13)
        user_email= request.data.get('email')
        password = User.objects.make_random_password()
        firstname= request.data.get('firstname')
        middlename= request.data.get('middlename')
        lastname= request.data.get('lastname')
        primary_currency= request.data.get('primary_currency')
        secondary_currency= request.data.get('secondary_currency')
        full_name = str(str(firstname)+" "+str(lastname))
        error_res={"status":False,
        "message":"validation error"
        }
        d={}
        attrs_dict={"user_email":user_email, "firstname":firstname,"lastname":lastname, "primary_currency":primary_currency, "secondary_currency":secondary_currency}
        none_list=[]
        for i in attrs_dict:
            if not attrs_dict[i]:
                none_list.append(i)
        if len(none_list) != 0:
            for i in none_list:
                d[i]=["This field may not be blank"]
            error_res["error"]= d

            return Response(error_res)
        if User.objects.filter(email= user_email).exists():
            return Response({
                "status": False,
                "message":" Email already exist"
                })
        elif User.objects.filter(username= username).exists():
            username= randomword(13)

        user = User.objects.create_user(username= username ,email=user_email ,password= password)
        customer,status = Customers.objects.get_or_create(user=user,customertype=1,agreetermsandconditions=True,createdby=user,isactive=True)
        useraccount,status = Useraccounts.objects.get_or_create(customer=customer,firstname=firstname,middlename=middlename,lastname=lastname)
        for currency in [primary_currency,secondary_currency]:
            accountno_list = list(map(int, list(Accounts.objects.filter(user_account__ismaster_account=False).order_by('-accountno').values_list('accountno', flat=True))))
            accountno_list.sort(reverse = True)
            account,status= Accounts.objects.get_or_create(user_account=useraccount,accountno = int(accountno_list[0]) + 1 if accountno_list else settings.DEFAULT_ADD,
                currency= Currencies.objects.get(code=currency),accounttype=1,isprimary=1 if currency==primary_currency else 2,createdby=user)
                
        try:
            primary_account = f"{useraccount.accnt_usr_accnt.all()[0].accountno} {useraccount.accnt_usr_accnt.all()[0].currency.code}"
            secondary_account = f"{useraccount.accnt_usr_accnt.all()[1].accountno} {useraccount.accnt_usr_accnt.all()[1].currency.code}"
        except Exception as e:
            primary_account = ""
            secondary_account = ""
            logger.info(f"Error in fetching account details->{e}")
        add_log_action(request, useraccount, status=f'Personal account({user_email}) has been created with accounts {primary_account} and {secondary_account}', status_id=1,user_id=user.id)
        email= user_email
        mail_status = self.send_confirm_mail(full_name, email,createdby=user,transaction_type=1, dev_type=1)
        return Response({
                "status":True,
                'data':{'username':full_name, 'email':email},
                "message":"created"
                })

class ReportMissingPaymet(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
       
        account= request.data.get('account')
        amount= request.data.get('amount')
        currency= request.data.get('currency')
        error_res={"status":False,
        "message":"validation error"
        }
        d={}
        attrs_dict={"account":account, "amount":amount,"currency":currency}

        none_list=[]
        for i in attrs_dict:
            if not attrs_dict[i]:
                none_list.append(i)
        if len(none_list) != 0:
            for i in none_list:
                d[i]=["This field may not be blank"]
            error_res["error"]= d

            return Response(error_res)
        serializer= ReportMissingSerializer(data= request.data)     
        if serializer.is_valid():
            serializer.validated_data['account']=  Accounts.objects.get(id= request.data['account'])
            serializer.validated_data['currency']= Currencies.objects.get(id =request.data['currency'])
            serializer.validated_data['createdby']= request.user
            # serializer.validated_data['amount']=str(round(serializer.validated_data['amount'], 2))

            serializer.save()
            return Response({
                "status": True,
                'data': serializer.data,
                
                "message": "Submitted Successfully"
            })
        return Response({
                "status": False,
                'error': serializer.errors,
                "message": "error"
            })

    def get(self, request):
        try:
            qs= Incomingtracepayment.objects.filter(createdby= request.user, isdeleted= False)
            serializer= ReportMissingSerializerList(data= qs, many= True)

            serializer.is_valid()
            data= serializer.data

            return Response({
                "Status": True,
                "data": data,
                "Message":" Success"
            })
        except Exception as e:
            logger.info(e)
            return Response({
                "Status": False,
                "data":{},
                "Message": "Unable to get reports"
            })
    def put(self, request, pk):
        try:
            tracepayment= Incomingtracepayment.objects.get(id =pk)
            if tracepayment.isdeleted == True:
                return Response({
                    "Status": True,
                    "Message": "Report not found"})
            tracepayment.isdeleted = True
            tracepayment.save()

            return Response({
                "Status": True,
                "Message": "Deleted Successfully"})
        except Exception as e:
            logger.info(e)
            return Response({
                "Status": True,
                "Message": "Report not found"})


class BusinessAccountCreation(APIView, ConfirmYourMail):
    def post(self,request): 
        companyname= request.data.get('companyname')
        industrytype= request.data.get('industrytype')
        companyurl= request.data.get('companyurl')
        country= request.data.get('country')
        address= request.data.get('address')
        city= request.data.get('city')
        state= request.data.get('state')
        phoneno= request.data.get('phoneno')
        primary_currency= request.data.get('primary_currency')
        secondary_currency= request.data.get('secondary_currency')

        users_lists = request.data.get('users_lists')
        for i in users_lists:
            e= i.get('email')
            if User.objects.filter(email= e).exists():
                return Response({
                    "status":False,
                    "message":"Email already exist",
                    "mail": e })
            else:
                pass
            
        for i in users_lists:
            if i.get('main_owner_list_new')=='1':
                    indx = int(users_lists.index(i))
        user_email = request.data['users_lists'][indx]['email']
        firstname = request.data['users_lists'][indx]['firstname']
        middlename = request.data['users_lists'][indx]['middlename']
        lastname = request.data['users_lists'][indx]['lastname']
        #primary_currency = request.data['user_lists'][indx]['primary_account']
        # secondary_currency = request.data['user_lists'][indx]['secondary_Account']
        user_type= request.data['users_lists'][indx]['user_type']
        primary_currency= request.data.get('primary_currency')
        secondary_currency= request.data.get('secondary_currency')
        
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
        user_type_obj= Transactionauthoritytypes.objects.filter(name=user_type).first()
        business_transaction_authority = Businesstransactionauthorities.objects.get_or_create(
                useraccount=useraccount,transactionauthoritytype=user_type_obj,
                createdby=user)  

        companyname=request.data.get('companyname')
        industrytype = Industrytypes.objects.get(name=request.data.get('industrytype'))
        url = request.data.get('companyurl')
        emailaddress = user_email
        phonenumber=request.data.get('phoneno')
        country_code=Countries.objects.filter(phonecode=request.data.get('countrycode')).first()
        address=request.data.get('address')
        country = request.data.get('country')
        company_country = Countries.objects.filter(shortform=request.data.get('country')).first(),
        city = request.data.get('city')
        state = request.data.get('state')

        business_details = Businessdetails.objects.get_or_create(customer= customer, companyname= companyname,
            industrytype= industrytype,
            url= url,
            emailaddress= emailaddress,
            phonenumber= phonenumber,
            countrycode= country_code,
            address= address,
            country= company_country,
            createdby= user,
            city= city,
            state= state,
            )
    
        for currency in [primary_currency,secondary_currency]:
            accountno_list = list(map(int, list(Accounts.objects.filter(user_account__ismaster_account=False).order_by('-accountno').values_list('accountno', flat=True))))
            accountno_list.sort(reverse = True)
            account,status = Accounts.objects.get_or_create(user_account=useraccount,accountno=int(accountno_list[0]) + 1 if accountno_list else settings.DEFAULT_ADD,
                            currency=Currencies.objects.get(code=currency),accounttype=1,isprimary=1 if currency==primary_currency else 2,createdby=user)

        mail_status = self.send_confirm_mail(full_name, user_email,createdby=user,transaction_type=1, dev_type=1)                   
        for i in users_lists:
            if users_lists.index(i) != indx:
                usr_name = randomword(13)
                while True:
                        if User.objects.filter(username=usr_name).exists():
                            usr_name = randomword(13)
                        else:
                            break
                user_sub=User.objects.create_user(username=usr_name,email=i.get('email'),password=password)
                customer_each,status = Customers.objects.get_or_create(user=user_sub,customertype=2,agreetermsandconditions=True,createdby=user,isactive=True)

                useraccount_each,status = Useraccounts.objects.get_or_create(customer=customer_each,firstname=i.get('firstname'),
                                middlename=i.get('middlename'),
                                lastname=i.get('lastname'),
                                added_by=customer,createdby=customer
                                )
                user_type= i.get('user_type')
                user_type_obj= Transactionauthoritytypes.objects.filter(name=user_type).first()
                business_transaction_authority = Businesstransactionauthorities.objects.get_or_create(
                useraccount=useraccount,transactionauthoritytype=user_type_obj,
                createdby= user)  
                
                companyname=request.data.get('companyname')
                industrytype = Industrytypes.objects.get(name=request.data.get('industrytype'))
                url = request.data.get('companyurl')
                emailaddress = user_email
                phonenumber=request.data.get('phoneno')
                countrycode=request.data.get('countrycode')
                address=request.data.get('address')
                country = request.data.get('country')
                city = request.data.get('city')
                state = request.data.get('state')

                business_details = Businessdetails.objects.get_or_create(
                        customer=customer_each,companyname=companyname,
                        industrytype = industrytype,
                        url = url,
                        emailaddress = emailaddress,
                        phonenumber=phonenumber,
                        countrycode=request.data.get('countryCode'),
                        address=address,
                        country = country,
                        city = city,
                        state = state
                        ) 
                firstname_each=i.get('firstname')
                middlename_each=i.get('middlename')
                lastname_each=i.get('lastname')
                user_email_each=i.get('email')
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
            
        return Response({
            "message":"success",
            "status":True
            })


class InwardRemittanceAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self,request):
        try:
            account = Accounts.objects.filter(isdeleted=False)
        except Exception as e:
            context={
                'status':False,
                'message':'account is not available in this position'
            }
            return Response(context)
        data_list=[]
        for acc in account:
            account_id=acc.id
            account_number=acc.accountno
            currency_code = acc.currency.code
            currencyflag=acc.currency.flag.url
            currency_id=acc.currency.id
            bank_details = Bankdetail.objects.filter(currency__code=currency_code, isdeleted=False).values()
            data={
                'account_id': account_id,
                'accountnumber': account_number,
                'currencycode':currency_code,
                'currencyid': currency_id,
                'currencyflag':currencyflag,
                'bankdetails':bank_details
            }
            data_list.append(data)

        context={
            'status':True,
            'data':data_list,
            'message':'successfully'
        }
        return Response(context)

class InwardRemittanceSuccessAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer=InwardRemittanceSerializer(data=request.data)
        if serializer.is_valid():
            bank_id = request.data.get('bank_id')
            account_id = request.data.get('account_id')
            sender_name = request.data.get('sender_name')
            sender_acc_number = request.data.get('sender_acc_number')
            sender_bank_name = request.data.get('sender_bank_name')
            sender_country = request.data.get('sender_country')
            swift_code = request.data.get('swift_code')
            amount = request.data.get('amount')
            reference = request.data.get('reference')
            invoice_doc = request.FILES.get('invoice_doc')

            def validate(request):
                if not amount:
                    return {
                        'status': False,
                        'message': 'Please enter the amount'
                    }
                elif float(amount) <= 0:
                    return {
                        'status':False,
                        'message':'Amount must be greater than 0'
                    }
                try:
                    bank_details = Bankdetail.objects.get(id=bank_id, isdeleted=False)
                except Exception as e:
                    logger.info(e)
                    return {
                        'status': False,
                        'message': 'selected bank is not available'
                    }
                try:
                    receive_money = Receivemoney.objects.create(
                        receiveraccount=Accounts.objects.get(id=account_id),
                        senderaccountno=sender_acc_number,
                        sendername=sender_name,
                        swiftcode=swift_code,
                        amount=amount,
                        reference=reference,
                        payment_proof=invoice_doc,
                        sendercountry=sender_country,
                        senderbankname=sender_bank_name,
                        bank=Bankdetail.objects.get(id=bank_id),
                        createdby=request.user
                    )
                    add_log_action(request, receive_money,
                                   status=f"created inward remittance of {receive_money.amount} {receive_money.receiveraccount.currency.code}",
                                   status_id=1)
                except Exception as e:
                    logger.info(e)
                    return {
                        'status': False,
                        'message': 'Error Occured'
                    }
                return {
                    'status': True
                }

            data = validate(request)
            if data.get('status') == True:
                context = {
                    'status': True,
                    'message': 'Your request has been successfully submitted.'
                }
                return Response(context)
            else:
                context = {
                    'status': False,
                    'message': data.get('message')
                }
                return Response(context)
        else:
            context={
                'status':False,
                'error':serializer.errors,
                'message':'Validation error occurred'
            }
            return Response(context)
class InwardRemittanceShowAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self,request):

        serializer=InwardAccountSerializer(data=request.data)
        if serializer.is_valid():
            account_id = request.data.get('account_id')
            accounts=Accounts.objects.filter(id=account_id)
            if not accounts:
                context={
                    'status':False,
                    'message':'account does not exist!'
                }
                return Response(context)

            try:
                account = Accounts.objects.get(id=account_id,isdeleted=False)
            except Exception as e:
                context = {
                    'status': False,
                    'message': 'account is not available in this position'
                }
                return Response(context)
            bank_details = Bankdetail.objects.filter(currency__code=account.currency.code, isdeleted=False)
            serializer=BankdetailSerializer(bank_details,many=True)
            context = {
                'status': True,
                'bank_details': serializer.data,
                'message': 'successfully'
            }
            return Response(context)
        else:
            context={
                'status':False,
                'errors':serializer.errors,
                'message':'Validation error'
            }
            return Response(context)

class UpdateCurrencyStatusAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        context = {}
        user_details = Useraccounts.active.get(customer__user=request.user)
        accounts = Accounts.active.filter(user_account__customer__user=request.user, isdeleted=False).order_by("-createdon").values()
        if user_details.added_by:
            accounts = acc_list(user_details).values()
        pr_accounts = accounts.filter(isprimary=1)
        sc_accounts = accounts.filter(isprimary=2)
        context['status']=True
        context['account_length'] = len(accounts)
        accounts = accounts.filter(isprimary=3)
        context['accounts'] = accounts
        context['pr_accounts'] = pr_accounts
        context['sc_accounts'] = sc_accounts
        context['currencies'] = Currencies.active.all().order_by("code").values()
        context['message']='successfully'
        return Response(context)

    def post(self, request):
        serializer=UpdateCurrencyStatusSerializer(data=request.data)
        if serializer.is_valid():
            acc_id = request.data.get("acc_id")
            acc_status = int(request.data.get("acc_status")) if request.data.get("acc_status") else 0
            loggeduser = request.user
            user_details = Useraccounts.objects.get(customer__user=request.user)
            if user_details.added_by:
                loggeduser = user_details.added_by.user
            try:
                acc_obj = Accounts.objects.get(id=acc_id)
                if acc_status == 1:
                    try:
                        acc_obj_pr = Accounts.objects.get(user_account__customer__user=loggeduser, isprimary=1,
                                                          isdeleted=False)
                        acc_obj_pr.isprimary = acc_obj.isprimary
                        acc_obj_pr.save()
                    except Exception as e:
                        logger.info(e)
                        pass
                    acc_obj.isprimary = 1
                elif acc_status == 2:
                    try:
                        acc_obj_sec = Accounts.objects.get(user_account__customer__user=loggeduser, isprimary=2,
                                                           isdeleted=False)
                        acc_obj_sec.isprimary = acc_obj.isprimary
                        acc_obj_sec.save()
                    except Exception as e:
                        logger.info(e)
                        pass
                    acc_obj.isprimary = 2
                acc_obj.save()
                context = {
                    'status': True,
                    'message': 'Updated successfully'
                }
                return Response(context)
            except Exception as e:
                logger.info(e)
                context = {
                    'status': False,
                    'message': 'Account does not exit'
                }
                return Response(context)
        else:
            context={
                'status':False,
                'errors':serializer.errors,
                'message':'Validation error'
            }
            return Response(context)

class IndustryTypeAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self, request):
        industry_types = Industrytypes.active.all()
        serializer = IndustrytypesSerializer(industry_types, many=True)
        content = {"status": 1, "data": serializer.data, "message": "success"}
        return Response(content, status=status.HTTP_200_OK)

class CompanyPermissionsAPIView(APIView,APIV1UtilMixins):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self,request):
        businessdetails = Businessdetails.objects.get(customer__user=request.user)
        ubo_account_id = Useraccounts.objects.get(customer__user=request.user).id
        matching_business_details = Businessdetails.objects.filter(companyname=businessdetails.companyname,emailaddress=businessdetails.emailaddress)
        data_details=[] 
        for matching_business_detail in matching_business_details:
            user_details=Useraccounts.objects.get(customer = matching_business_detail.customer)
            user_details_id=Useraccounts.objects.get(customer = matching_business_detail.customer).id
            user_account_status = Useraccounts.objects.get(customer__user=matching_business_detail.customer.user).activestatus
            user_account_trans_status = Useraccounts.objects.get(customer__user=matching_business_detail.customer.user).account_tran_status
            transaction_authoritytypes=Businesstransactionauthorities.objects.filter(useraccount=user_details)
            for transaction_authoritytype in transaction_authoritytypes:
                data_details.append({
                    "Full_Name":user_details.fullname,
                    "User_Type":transaction_authoritytype.transactionauthoritytype.name,
                    "Email_Address":user_details.customer.user.email,
                    "Permissions":user_details.ultimate_ben_user,
                    "account_id":user_details_id,
                    "transaction":user_account_trans_status,
                    "activestatus":user_account_status})
            

        context = {
            'status':1,
            'Message':'Success!',
            'ubo_account_id':ubo_account_id,
            'data':data_details,
            
        }
        return Response (context)
    def post(self,request):
            if request.data.get('type')=='addmore_user':
                seriliazer = CompanyPermissionSerializer(data=request.data)
                if seriliazer.is_valid():              
                    firstname=request.POST.get('firstname')
                    middlename=request.POST.get('middlename')
                    lastname=request.POST.get('lastname')
                    user_email = request.POST.get('emailaddress')
                    password = User.objects.make_random_password()
                    authority_types = Transactionauthoritytypes.objects.filter(isdeleted=False)
                    userType= request.POST.get('userType') if 'userType' in request.POST.dict() else None
                    if User.objects.filter(email=user_email).exists():
                        context={
                            "status":0,
                            "errors": {
                                "emailaddress": [
                                    "Email already exists."]
                            },
                            "message": "Validation error"
                            }
                        return Response(context)
                    else:  
                        if userType is not None:
                            usr_name = randomword(13)
                            while True:
                                if User.objects.filter(username=usr_name).exists():
                                    usr_name = randomword(13)
                                else:
                                    break
                            user = User.objects.create_user(username=usr_name,email=user_email,password=password)
                            customer,status = Customers.objects.get_or_create(user=user,customertype=2,agreetermsandconditions=True,
                                createdby=request.user,isactive=True,

                                ubo_customer = True if request.POST.get('mainBusinessownernew') == '1' else False,
                             )

                            current_user_added_by = Useraccounts.objects.get(customer__user=request.user).added_by
                            useraccount_each,status = Useraccounts.objects.get_or_create(customer=customer,firstname=request.data.get('firstname'),
                                    middlename=request.data.get('middlename'),
                                    lastname=request.data.get('lastname'),
                                    added_by=Useraccounts.objects.get(customer__user=request.user).added_by,
                                    ultimate_ben_user = True if request.data.get('mainBusinessownernew') == '1' else False,
                                    )
                            if useraccount_each.referred_by:
                                useraccount_each.customer.outgoingtansactionfee = current_user_added_by.outgoingtansactionfee
                                useraccount_each.customer.save()
                            business_transaction_authority_each = Businesstransactionauthorities.objects.get_or_create(
                                    useraccount=useraccount_each,transactionauthoritytype=Transactionauthoritytypes.objects.get(name=request.data.get('userType'))
                                    )
                            ubo_user = Useraccounts.objects.get(customer__user = request.user)
                            business_details = Businessdetails.objects.get(customer__user = request.user)
                            account_id= Useraccounts.objects.get(customer=useraccount_each.customer).id
                            business_details_new_user = Businessdetails.objects.get_or_create(
                                customer=customer,companyname=business_details.companyname,
                                industrytype=business_details.industrytype,
                                url=business_details.url,
                                createdby=business_details.createdby,
                                emailaddress=business_details.emailaddress,
                                phonenumber=business_details.phonenumber,
                                country_code=business_details.country_code,
                                address=business_details.address,company_country=business_details.company_country,
                                city = business_details.city, state = business_details.state
                            )
                            if request.data.get('middlename'):
                                full_name = f"{firstname} {middlename} {lastname}"
                                
                            else:
                                full_name = f"{firstname} {lastname}"
                            
                            password = User.objects.make_random_password()
                            ConfirmYourMail().send_confirm_mail(full_name, user_email,createdby=user,transaction_type=1, dev_type=1)
            
                            
                            try:
                                customer_doc_current = Customerdocuments.objects.filter(customer__user=request.user,verificationtype__verificationtype=3).first()
                                customer_doc_details_current1 = Customerdocumentdetails.objects.filter(customerdocument=customer_doc_current,
                                            field = Documentfields.objects.get(fieldtype='2',documenttype__description="Company registration document")).first()

                                customer_doc_details_current2 = Customerdocumentdetails.objects.filter(customerdocument=customer_doc_current,
                                                field = Documentfields.objects.get(fieldtype='5',documenttype__description="Company registration document")).first()

                                customer_doc_file_current = Customerdocumentfiles.objects.filter(customerdocument=customer_doc_current, document_type="Document").first()
                                
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
                                customer_files = Customerdocumentfiles.objects.create(customerdocument=customer_doc, filelocation=customer_doc_file_current.filelocation,
                                    document_type="Document")

                                additional_document1 = Customerdocumentfiles.objects.filter(
                                    customerdocument=customer_doc_current, document_type="AdditionalDocument1").first()
                                additional_document2 = Customerdocumentfiles.objects.filter(
                                    customerdocument=customer_doc_current, document_type="AdditionalDocument2").first()
                                additional_document3 = Customerdocumentfiles.objects.filter(
                                    customerdocument=customer_doc_current, document_type="AdditionalDocument3").first()
                                if additional_document1:
                                    Customerdocumentfiles.objects.create(
                                        customerdocument=customer_doc, filelocation=additional_document1.filelocation,
                                        document_type="AdditionalDocument1"
                                    )
                                if additional_document2:
                                    Customerdocumentfiles.objects.create(
                                        customerdocument=customer_doc, filelocation=additional_document2.filelocation,
                                        document_type="AdditionalDocument2"
                                    )
                                if additional_document3:
                                    Customerdocumentfiles.objects.create(
                                        customerdocument=customer_doc, filelocation=additional_document3.filelocation,
                                        document_type="AdditionalDocument3"
                                    )

                            except Exception as e:
                                logger.info(e)
                            
                           
                            context={
                                'status':1,
                                'message':"Updated successfully ",
                                'data':{
                                    'FullName':full_name,
                                    'Email':user_email,
                                    "User_Type":userType,
                                    'authority_types':Transactionauthoritytypes.objects.get(name= request.data['userType']).id,
                                    "account_id":account_id,
                                }
                            }
                            return Response(context)
                    

                        else:
                            context={
                            "status":0,
                            "errors": {
                                "userType": [
                                    "This field is required."
                                ]
                            },
                            "message": "Validation error"
                                }
                            return Response(context)


                else:
                    context={
                    'status':0,
                    'errors':seriliazer.errors,
                    'message':'Validation error'
                }
                return Response(context)

            elif request.data.get('type')=='deactivate':
                seriliazer = CompanyPermissionSerializer(data=request.data)
                account_id = request.POST.get('account_id')
                user_account = Useraccounts.objects.filter(id=account_id).update(
                activestatus="Deactivated by UBO")
                context={
                    'status':1,
                    'message':"Account successfully deactivated",
                    'user_account':user_account
                }
                return Response(context)
          
            elif request.POST.get('type')=='allow_transactions':
                ubo_account = Useraccounts.objects.get(id=request.data.get('ubo_acc_id'))
                user_account = Useraccounts.objects.get(id=request.data.get('account_id'))
                user_account.account_tran_status = True
                user_account.save()
                context={
                    'status':1,
                    'message':'Allow transactions',
                }
                return Response(context)
            elif request.POST.get('type')=='restrict_transactions':
                ubo_account = Useraccounts.objects.get(id=request.POST.get('ubo_acc_id'))
                user_account = Useraccounts.objects.get(id=request.POST.get('account_id'))
                user_account.account_tran_status = False
                user_account.save()
                context={
                    'status':1,
                    'message':'Restrict transactions',
                }
                return Response(context)

            elif request.POST.get('type')=='send-permission-req-mail':
                current_user_email = request.user.email
                user_account = Useraccounts.objects.get(customer__user=request.user)
                company = Businessdetails.objects.get(customer__user=request.user)
                all_companies = list(Businessdetails.objects.filter(companyname=company.companyname,url=company.url))
                to_email_list=[]
                for company in all_companies:
                    user_account = Useraccounts.objects.get(customer=company.customer)
                    if user_account.ultimate_ben_user:
                            to_email_list.append(user_account.customer.user.email)
                          
                PermissionEmail().send_email_permission(to_email_list,current_user_email)
                context={
                    'status':1,
                    'message' : 'Mail successfully sent to Ultimate Beneficial Owner.',
                    
                }
                return Response(context)

class ImageUploadView(APIView):
    serializer_class = ImageUploadSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        seriliazer = ImageUploadSerializer(data=request.data)
        if seriliazer.is_valid():
            user = request.user
            baseuser = Useraccounts.objects.get(customer__user= user)
            baseuser.image = seriliazer.validated_data["image"]
            baseuser.save()
            image = Useraccounts.objects.get(customer__user=user).image
            context = {
                "status": 1,
                "mesage": "Profile picture updated successfully !",
                "data": {
                    "image": settings.AWS_S3_BUCKET_URL + settings.AWS_S3_MEDIA_URL + str(image)
                },
            }
            return Response(context)
        else:
            try:
                err_msg = seriliazer.errors['image']['message'] 
                context = {
                    "status": 0,
                    "mesage":err_msg,
                }
            except:
                context = {
                    "status": 0,
                    "mesage":  "Incorrect image format",
                }
                
            return Response(context)

        


                             
class Personal_DetailsAPIView(APIView,OTP,APIV1UtilMixins):
    authentication_classes = [APIAccessTokenPermissions]
    permission_classes = [IsAuthenticated]
    def get(self, request):
        personal_details = Useraccounts.objects.get(customer__user=request.user)
        user_personaldetail = Personal_DetailSerializer(personal_details)
        context = {"status":True,"data":{'personal_details':user_personaldetail.data} }
        context["data"]['personal_details']['email'] = request.user.email 
        return Response(context)
    

class AccountAPIview(generics.ListAPIView):
    """
    This view should return a single  Accounts
    """       
    serializer_class = GetaccountSerializer
    authentication_classes = [APIAccessTokenPermissions]
    permission_classes = [IsAuthenticated]       
    def get(self,request,pk):
        accounts = Accounts.objects.filter(user_account__customer__user=request.user, isdeleted=False)
        try:
            account_number = Accounts.objects.get(accountno=pk)
            if account_number in accounts:        
                context={
                    'status' :True,
                    'data':{
                        'account_details': {
                        'account_number' : account_number.accountno,
                        'balance' : str(round(account_number.balance,2)),
                        'currency' : account_number.currency.code,
                    }
                } 
                    }
                    
            return Response(context,status=status.HTTP_200_OK)
        except:
            context = {
                "status":False,
                "error":{
                    "account_number":["Account does not exists"]},
                "message":"Invalid account number"
            } 
         
        return Response(context,status=status.HTTP_404_NOT_FOUND)
        
            
class International_Wire_TransferAPIview(APIView):  
    """
    This view should return transaction_no for the international wire transfer
    """       
    serializer_class = International_WireTransfer_Serializer
    authentication_classes = [APIAccessTokenPermissions]
    permission_classes = [AccountVerifiedPermission,AccountlockedPermissionforextapi,AccountTransactionPermission]
    def post(self,request):
        data = request.data  
        if data :
            # Temporary code
            _mutable = data._mutable
            # set to mutable
            data._mutable = True
            data['ownaccount']='False'
            data._mutable = _mutable
            ####
            def validate_invoice_doc(data):
                invoice_doc = data
                if invoice_doc:
                    ext = os.path.splitext(invoice_doc.name)[1]
                    filesize = invoice_doc.size
                    if not ext in settings.ALLOWED_FORMATS:
                        return {
                            "status": False,
                            "error": {
                                "invoice_doc": [
                                    "Incorrect file format."
                                ]
                                    },
                            "message": "validation error",
                        }
                    elif filesize > settings.MAX_FILE_SIZE:
                        return {
                            "status": False,
                            "error": {
                                "invoice_doc": [
                                "Maximum file size allowed is 10 MB"
                                ]
                                    },
                            "message": "validation error",
                        }
                    elif not all(ord(c) < 128 for c in invoice_doc.name):
                        return {
                            "status":False,
                            "error": {
                                "invoice_doc": [
                                "Special characters should not be in file name"
                                ]
                                    },
                            "message": "validation error",
                        }
                    else:
                        return {
                    "status":True,
                    "data":{}
                    }                 
                return invoice_doc
        if data.get('invoice_doc'):
            outcome= validate_invoice_doc(data.get('invoice_doc'))
            if not outcome.get("status"):
                return Response(outcome,status=status.HTTP_404_NOT_FOUND)
        if data.get('has_invoice'):
            if data['has_invoice']!='0' and data['has_invoice']!='1':
                    context={
                        'status': False,
                        'error':{
                            'has_invoice':"value must be '0' or '1'"
                        },
                        'message':"Invalid data"
                    }
                    return Response(context,status=status.HTTP_404_NOT_FOUND)
            if data.get('purpose'):
                p_urpose =Transactionpurposetype.objects.filter(transactionpurpose=request.data['purpose'], isdeleted=False).first()
                if not p_urpose :
                    context ={
                            'status':False,
                            'error':{
                                'purpose':["choose correct purpose"]
                            },
                            'message':"Invalid data"                                              
                        }          
                    return Response(context,status.HTTP_404_NOT_FOUND)
        seriliazer = International_WireTransfer_Serializer(data=data, context={'InternationalWireTransfer':True}) 
        is_ext_ben = Externalbeneficiaries.objects.filter(Q(accountnumber=request.data.get('beneficiary_account')) | Q(name=request.POST.get('beneficiary_name')), isdeleted=False,createdby=request.user).exists()
        accounts = Accounts.objects.filter(user_account__customer__user=request.user, isdeleted=False)   
        if seriliazer.is_valid():
            amount = round(Decimal(request.data.get('debit_amount')),2)
            from_amount = amount  
            try:
                from_account = Accounts.objects.get(accountno=request.data.get('debit_account'),createdby=request.user, isdeleted=False)
            except Exception as e:
                context={
                    'status':False,
                    'error':{
                        "debit_account":[
                            'Account does not exists']},
                    'message':"Invalid data"
                }
                return Response(context,status.HTTP_404_NOT_FOUND)
            from_account_balance = Decimal(from_account.balance)
            def conversion_charges(amount):
                if amount < 1000:
                    self.wire_transfer_fee = Decimal(10.00) 
                    self.cable_charge = Decimal(49.00)
                elif amount >= 1000 and amount <6900 :
                    self.total_tr_charge = Decimal(69.00)
                    self.wire_transfer_fee = round(amount * Decimal((1/100)),2)
                    self.cable_charge = round(self.total_tr_charge - self.wire_transfer_fee,2)
                    
                elif amount >=6900:
                    self.wire_transfer_fee = round(amount * Decimal((1/100)),2)
                    self.cable_charge = Decimal(0.00) 
                
            def conversion_rates(amount, from_currency_code,conversion_fee, wire_transfer_fee, cable_charge):
        
                to_dollar = Currencyconversionratescombined.objects.get(fromcurrency__code='USD', tocurrency__code=from_currency_code, isdeleted=False)
                currency_conversion = Currencyconversionratescombined.objects.get(fromcurrency__code=from_currency_code, tocurrency__code=request.POST.get('currency_code'), isdeleted=False)
                conversionrate = round(currency_conversion.conversionrate,4)
                try:
                    currency_margin = Currencyconversionmargins.objects.get(fromcurrency__code=from_currency_code, tocurrency__code=request.POST.get('currency_code'), isdeleted=False)
                    margin_rate = currency_margin.marginpercent
                    conversionrate = conversionrate - (conversionrate* Decimal(float(margin_rate)/100))
                except Exception as e:
                    logger.info(e)
                
                self.min_tr_amount = Decimal(100) * to_dollar.conversionrate
                self.conversion_fee = conversion_fee
                self.wire_transfer_fee = round(wire_transfer_fee * to_dollar.conversionrate,2)
                self.cable_charge = round(cable_charge * to_dollar.conversionrate,2)
                self.credit_amount = round(from_amount * conversionrate,2)

            from_currency_code = from_account.currency.code
            if request.POST.get('currency_code') not in Currencies.objects.values_list('code', flat=True):
                context = {
                    'status':False,
                    "error":{
                      'currency_code':["invalid currency code format!"]  
                    },
                    "message": "Invalid format"
                }
                return Response(context,status.HTTP_404_NOT_FOUND)
            
            if request.POST.get('currency_code') == from_currency_code:
                if from_currency_code == 'USD':
                    amount = Decimal(amount)
                else:
                    to_dollar = Currencyconversionratescombined.objects.get(fromcurrency__code='USD', tocurrency__code=from_currency_code, isdeleted=False)
                    amount = Decimal(amount) / to_dollar.conversionrate
                conversion_fee = Decimal(0.00)
                conversion_charges(amount)
            else:
                if from_currency_code == 'USD':
                    amount = Decimal(amount)
                else:
                    to_dollar = Currencyconversionratescombined.objects.get(fromcurrency__code='USD', tocurrency__code=from_currency_code, isdeleted=False)
                    amount =Decimal(amount) / to_dollar.conversionrate
                conversion_fee = round(from_amount * Decimal(0.5/100),2)
                conversion_charges(amount)
            conversion_rates(amount, from_currency_code, conversion_fee, self.wire_transfer_fee, self.cable_charge)
            debit_amount = self.wire_transfer_fee + self.cable_charge + self.conversion_fee + from_amount
            if from_account_balance < debit_amount:
                context = {
                    'status':False,
                    'error':{
                        'debit_amount':["You don't have enough funds to make this transaction"]
                    },
                    'message':"Invalid data"
                    
                }
                return Response(context,status.HTTP_404_NOT_FOUND)
            elif from_amount < self.min_tr_amount:
                context = {
                    'status':False,
                    'error':{
                        "debit_amount":[f'Minimum amount required for the transaction is {format(self.min_tr_amount, ".2f")} {from_currency_code}']
                    },
                    'message': "Invalid data"
                }
                return Response(context,status.HTTP_404_NOT_FOUND)
            try:
                customer_type = Customers.objects.get(user=request.user, isdeleted=False).customertype
                if customer_type == 1:
                    user = Useraccounts.objects.get(customer__user=request.user, isdeleted=False)
                    sender_name = f'{user.firstname} {user.lastname}'
                else:
                    sender_name = Businessdetails.objects.get(customer__user=request.user, isdeleted=False).companyname
            except Exception as e:
                logger.info(e)
                context = {
                    'status':False,
                    'error':{
                        'message' : 'Your Transaction has been declined due to invalid Customer or Business details'
                    }   
                }
                return Response(context,status.HTTP_404_NOT_FOUND)
            try:
                last_transactionno = Transactions.objects.latest('transactionno').transactionno
            
            except Exception as e:
                logger.info(e)
                last_transactionno = 10000000
            def transaction_fn(last_transactionno, from_amount,charge, parent_tr=None, toamount=None, inl_tr=None, commission_charges=None, cable_charge=None, last_transaction=None):
                try:
                    try:
                        account = Accounts.objects.get(accountno=request.data.get('debit_account'), isdeleted=False)
                    except Exception as e:
                        logger.info(e)
                        context= {
                            'status':False,
                            'error':{
                                'message':'Your Transaction has been declined due to invalid source account'
                            }
                            }
                        return context
                    if account.balance < Decimal(from_amount):
                        raise Exception()
                    account_balance = account.balance - Decimal(from_amount)
                    account.balance = account_balance
                    account.save()
                except Exception as e:
                    logger.info(e)
                    context = {
                        'status':False,
                        'error':{
                            'account_balance':'Your Transaction has been declined due to insufficient fund'
                        },
                        'message' :"Invalid data"
                    }
                    return context
                if cable_charge:
                    cablecharge_obj = Cablecharges.objects.create(
                                parenttransaction=parent_transaction,
                                chargeamount=Decimal(from_amount),
                                currency=Currencies.objects.get(code=request.data.get('currency_code'), isdeleted=False),
                                createdby=request.user,
                                transaction=last_transaction
                            )
                    add_log_action(request, cablecharge_obj, status=f'cable charge created for transaction {parent_transaction.transactionno}', status_id=1)
                    return {
                        'status':True,
                    }
                else:
                    if commission_charges:
                        try:
                            toaccount = Accounts.objects.get(user_account__ismaster_account=True, currency__code=from_currency_code, isdeleted=False)
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
                        self.transaction = Transactions.objects.create(
                                                    transactionno=int(last_transactionno)+1,
                                                    fromaccount=Accounts.objects.get(accountno=request.data.get('debit_account'), isdeleted=False),
                                                    toaccount=None,
                                                    fromamount=from_amount,
                                                    toamount=toamount,
                                                    initiatedby=request.user,
                                                    transactiontype=Transactiontypes.objects.get(name='Third Party Transfer'),
                                                    createdby=request.user,
                                                    note=request.data.get('note') if request.data.get('note') else '',
                                                    recipientname=request.data.get('beneficiary_name'),
                                                    fromaccountbalance=account_balance,
                                                    toaccountbalance=to_account_balance,
                                                    parenttransaction=parent_tr,
                                                    amount_type = charge_type,
                                                    affiliate_fee_percentage = Customers.objects.get(isdeleted=False, user=request.user).outgoingtansactionfee if Customers.objects.get(isdeleted=False,user=request.user).outgoingtansactionfee else 0
                                                    )
                        add_log_action(request, self.transaction, status=f"transaction(International Wire transfer : amount type {self.transaction.amount_type}) created for account {str(self.transaction.fromaccount.accountno)}", status_id=1)
                        if inl_tr:
                            try:
                                invoice_doc = InvoiceDocument.objects.create(invoice_doc=request.data.get('invoice_doc'))
                                invoice_doc.transaction = self.transaction
                                invoice_doc.save()
                            except Exception as e:
                                logger.info(e)
                            
                            inl_tr = Internationaltransactions.objects.create(
                                            transaction=self.transaction,
                                                bankname=request.data['bank_name'],
                                                swiftcode=request.data['bankswift_code'],
                                                accountnumber=request.data['beneficiary_account'],
                                                accountholdername=request.data['beneficiary_name'],
                                                currency=Currencies.objects.get(code=request.data['currency_code'], isdeleted=False),
                                                createdby=request.user,
                                                city=request.data['bank_city'],
                                                country=Countries.objects.get(name=request.data['bank_country']),
                                                email=request.data['beneficiary_email'] if request.data.get('beneficiary_email') else None,
                                                purpose=Transactionpurposetype.objects.get(transactionpurpose=request.data['purpose'], isdeleted=False),
                                                other_purpose_note=request.data['purpose_note'] if request.data.get('purpose_note') else None,
                                                user_box_no=request.data['user_box_no'] if request.data.get('user_box_no') else None,
                                                user_street=request.data['user_street'] if request.data.get('user_street') else None,
                                                user_city=request.data['user_city'] if request.data.get('user_city') else None,
                                                user_state=request.data['user_state'] if request.data.get('user_state') else None,
                                                user_country=Countries.objects.get(name=request.data['user_country']) if request.data.get('user_country') else None,
                                                user_phone=request.data['user_phone'] if request.data.get('user_phone') else None
                            )
                            add_log_action(request, inl_tr, status=f'international transaction created for account {str(self.transaction.fromaccount.accountno)}', status_id=1)
                    except Exception as e:
                        logger.info(e)
                        
                        context= {
                            'status':False,
                            'error':{
                                'message':'Your Transaction has been declined due to some error'
                            }
                        }
                        return context                      
            response = transaction_fn(last_transactionno, request.data['debit_amount'], toamount= self.credit_amount, charge=1, inl_tr= True)
            if response and not response.get('status'):
                return Response(response,status.HTTP_404_NOT_FOUND)
            parent_transaction =  self.transaction
            charge = 3
            response = transaction_fn(last_transactionno, self.wire_transfer_fee, charge, parent_transaction, toamount=self.wire_transfer_fee, commission_charges=True)
            if response and not response.get('status'):
                return Response(response,status=status.HTTP_200_OK)
            charge = 2
            response = transaction_fn(last_transactionno, self.conversion_fee, charge, parent_transaction, toamount=self.conversion_fee, commission_charges=True)
            if response and not response.get('status'):
                return Response(response,status=status.HTTP_200_OK)
            last_transaction =  self.transaction
            response = transaction_fn(last_transactionno, self.cable_charge,parent_transaction, cable_charge=True, last_transaction=last_transaction)
            if response and not response.get('status'):
                return Response(response,status=status.HTTP_200_OK)
            from_currency_code = from_account.currency.code
            if data['has_invoice'] == '0' and data['ownaccount'] == 'False':
                    if data['purpose'] == 'Other Remittance':
                            if 'purpose_note' in data:
                                if data['purpose_note'] != '':
                                    context = {
                                        'status':True,
                                        'data': {
                                            'transaction_no':parent_transaction.transactionno,
                                        'debit_account_details':{
                                            'debit_account':request.data['debit_account'],
                                            'sender_name':sender_name,
                                            'from_currency_code':from_currency_code,  
                                            'amount':format(float(request.data['debit_amount']), ".2f"),  
                                        },
                                        'credit_account_details':{
                                            'beneficiary_account':request.data['beneficiary_account'],
                                            'beneficiary_name':request.data['beneficiary_name'],
                                            'bank_name':request.data['bank_name'],
                                            'bankswift_code':request.data['bankswift_code'],
                                            'bank_city':request.data['bank_city'],
                                            'bank_country':request.data['bank_country'],
                                            'currency_code':request.data['currency_code'],
                                            'purpose':request.data['purpose'],
                                            'purpose_note':request.data['purpose_note'],
                                            'note':request.data['note'] if request.data.get('note') else None,
                                            'beneficiary_email':request.data['beneficiary_email'] if request.data.get('beneficiary_email') else None,
                                            'user_box_no':request.data['user_box_no'] if request.data.get('user_box_no') else None,
                                            'user_street':request.data['user_street'] if request.data.get('user_street') else None,
                                            'user_city':request.data['user_city'] if request.data.get('user_city') else None,
                                            'user_state':request.data['user_state'] if request.data.get('user_state') else None,
                                            'user_country':request.data['user_country'] if request.data.get('user_country') else None,
                                            'user_phone':request.data['user_phone'] if request.data.get('user_phone') else None,             
                                        },
                                        'conversion_fee' : format(conversion_fee, ".2f"),
                                        'wire_transfer_fee' : format(self.wire_transfer_fee,".2f"),
                                        'cable_charge' : format(self.cable_charge, ".2f"),
                                        'debit_amount' : format(debit_amount, ".2f"),
                                        'credit_amount' : format(self.credit_amount, ".2f"),
                                        'has_invoice':int(request.data.get('has_invoice')),
                                        'invoice':None,
                                            }
                                        }                                      
                                    if context['data'].get("domain"):
                                        del context['data']['domain']
                                    return Response(context,status=status.HTTP_200_OK)                                    
                    elif data['purpose'] != 'Other Remittance':
                        if 'purpose_note' not in data:
                            context = {
                                'status':True,
                                'data': {
                                        'transaction_no':parent_transaction.transactionno,
                                    'debit_account_details':{
                                        'debit_account':request.data['debit_account'],
                                        'sender_name':sender_name,
                                        'from_currency_code':from_currency_code,
                                        'amount':format(float(request.data['debit_amount']), ".2f"),     
                                    },
                                    'credit_account_details':{
                                        'beneficiary_account':request.data['beneficiary_account'],
                                        'beneficiary_name':request.data['beneficiary_name'],
                                        'bank_name':request.data['bank_name'],
                                        'bankswift_code':request.data['bankswift_code'],
                                        'bank_city':request.data['bank_city'],
                                        'bank_country':request.data['bank_country'],
                                        'currency_code':request.data['currency_code'],
                                        'purpose':request.data['purpose'],
                                        'note':request.data['note']  if request.data.get('note') else None,
                                        'beneficiary_email':request.data['beneficiary_email']  if request.data.get('beneficiary_email') else None,
                                        'user_box_no':request.data['user_box_no'] if request.data.get('user_box_no') else None,
                                        'user_street':request.data['user_street'] if request.data.get('user_street') else None,
                                        'user_city':request.data['user_city'] if request.data.get('user_city') else None,
                                        'user_state':request.data['user_state'] if request.data.get('user_state') else None,
                                        'user_country':request.data['user_country'] if request.data.get('user_country') else None,
                                        'user_phone':request.data['user_phone'] if request.data.get('user_phone') else None,
                                        },
                                    'conversion_fee' : format(conversion_fee, ".2f"),
                                    'wire_transfer_fee' : format(self.wire_transfer_fee,".2f"),
                                    'cable_charge' : format(self.cable_charge, ".2f"),
                                    'debit_amount' : format(debit_amount, ".2f"),
                                    'credit_amount' : format(self.credit_amount, ".2f"),
                                    'has_invoice':int(request.data.get('has_invoice')),
                                    'invoice':None,
                                    }
                                }                               
                            if context['data'].get("domain"):
                                del context['data']['domain']
                            return Response(context,status=status.HTTP_200_OK) 

            elif request.data['has_invoice'] == '0' and request.data['ownaccount'] =='True':
                
                if 'invoice_doc' not in request.data:
                    if data['purpose'] =='Other Remittance':
                        if 'purpose_note' in data:
                            if data['purpose_note'] != '':
                                context = {
                                    'status':True,
                                    'data': {
                                        'transactionno':parent_transaction.transactionno,
                                        'transaction_id':parent_transaction.id,
                                        'debit_account_details':{
                                            'debit_account':request.data['debit_account'],
                                            'sender_name':sender_name,
                                            'from_currency_code':from_currency_code,
                                            'amount':format(float(request.data['debit_amount']), ".2f"),
                                            },
                                        'credit_account_details':{
                                            'beneficiary_account':request.data['beneficiary_account'],
                                            'beneficiary_name':request.data['beneficiary_name'],
                                            'amount':format(float(request.data['debit_amount']), ".2f"),
                                            'bank_name':request.data['bank_name'],
                                            'bankswift_code':request.data['bankswift_code'],
                                            'bank_city':request.data['bank_city'],
                                            'bank_country':request.data['bank_country'],
                                            'currency_code':request.data['currency_code'],
                                            'purpose':request.data['purpose'],
                                            'purpose_note':request.data['purpose_note'],
                                            'note':request.data['note'] if request.data.get('note') else None,
                                            'beneficiary_email':request.data['beneficiary_email'] if request.data.get('beneficiary_email') else None,
                                            'user_phone':request.data['user_phone'] if request.data.get('user_phone') else None,
                                        },
                                        'conversion_fee' : format(conversion_fee, ".2f"),
                                        'wire_transfer_fee' : format(self.wire_transfer_fee,".2f"),
                                        'cable_charge' : format(self.cable_charge, ".2f"),
                                        'debit_amount' : format(debit_amount, ".2f"),
                                        'credit_amount' : format(self.credit_amount, ".2f"),
                                        'has_invoice':int(request.data.get('has_invoice')),
                                        'invoice':None,
                                        }
                                    }
                                if context['data'].get("domain"):
                                    del context['data']['domain']
                                return Response(context,status=status.HTTP_200_OK)                            

                    elif request.data['purpose'] != 'Other Remittance':
                        if 'purpose_note' not in data:
                            context = {
                                'status':True,
                                'data': {
                                    'transactionno':parent_transaction.transactionno,
                                'debit_account_details':{
                                    'debit_account':request.data['debit_account'],
                                    'sender_name':sender_name,
                                    'from_currency_code':from_currency_code,
                                    'amount':format(float(request.data['debit_amount']), ".2f"),
                                },
                                'credit_amount_details':{
                                    'beneficiary_account':request.data['beneficiary_account'],
                                    'beneficiary_name':request.data['beneficiary_name'],
                                    'bank_name':request.data['bank_name'],
                                    'bankswift_code':request.data['bankswift_code'],
                                    'bank_city':request.data['bank_city'],
                                    'bank_country':request.data['bank_country'],
                                    'currency_code':request.data['currency_code'],
                                    'purpose':request.data['purpose'],
                                    'note':request.data['note'] if request.data.get('note') else None,
                                    'beneficiary_email':request.data['beneficiary_email'] if request.data.get('beneficiary_email') else None ,
                                    'user_phone':request.data['user_phone'] if request.data.get('user_phone') else None,
                                    },                                   
                                'conversion_fee' : format(conversion_fee, ".2f"),
                                'wire_transfer_fee' : format(self.wire_transfer_fee,".2f"),
                                'cable_charge' : format(self.cable_charge, ".2f"),
                                'debit_amount' : format(debit_amount, ".2f"),
                                'credit_amount' : format(self.credit_amount, ".2f"),
                                'has_invoice':int(request.data.get('has_invoice')),
                                'invoice':None,
                                    }
                                }                               
                            if context['data'].get("domain"):
                                del context['data']['domain']
                            return Response(context,status=status.HTTP_200_OK)
            elif data['has_invoice'] == '1' and data['ownaccount'] == 'False':
                if 'invoice_doc' in data:
                    if data['purpose'] == 'Other Remittance':
                        if 'purpose_note' in data:
                            if data['purpose_note'] != '':
                                context = {
                                        'status':True,
                                        'data': {
                                            'transaction_no':parent_transaction.transactionno,
                                        'debit_account_details':{
                                            'debit_account':request.data['debit_account'],
                                            'sender_name':sender_name,
                                            'from_currency_code':from_currency_code,
                                            'amount':format(float(request.data['debit_amount']), ".2f"),                                           
                                        },
                                        'credit_account_details':{
                                            'beneficiary_account':request.data['beneficiary_account'],
                                            'beneficiary_name':request.data['beneficiary_name'],
                                            'bank_name':request.data['bank_name'],
                                            'bankswift_code':request.data['bankswift_code'],
                                            'bank_city':request.data['bank_city'],
                                            'bank_country':request.data['bank_country'],
                                            'currency_code':request.data['currency_code'],
                                            'purpose':request.data['purpose'],
                                            'purpose_note':request.data['purpose_note'],
                                            'note':request.data['note'] if request.data.get('note') else None ,
                                            'beneficiary_email':request.data['beneficiary_email'] if request.data.get('beneficiary_email') else None,
                                            'user_box_no':request.data['user_box_no'] if request.data.get('user_box_no') else None,
                                            'user_street':request.data['user_street'] if request.data.get('user_street') else None,
                                            'user_city':request.data['user_city'] if request.data.get('user_city') else None,
                                            'user_state':request.data['user_state'] if request.data.get('user_state') else None,
                                            'user_country':request.data['user_country'] if request.data.get('user_country') else None,
                                            'user_phone':request.data['user_phone'] if request.data.get('user_phone') else None,
                                            },                                           
                                        'conversion_fee' : format(conversion_fee, ".2f"),
                                        'wire_transfer_fee' : format(self.wire_transfer_fee,".2f"),
                                        'cable_charge' : format(self.cable_charge, ".2f"),
                                        'debit_amount' : format(debit_amount, ".2f"),
                                        'credit_amount' : format(self.credit_amount, ".2f"),
                                        'has_invoice':int(request.data.get('has_invoice')),
                                        'invoice_doc' : request.FILES['invoice_doc'].name,
                                            }
                                        }                                    
                                if context['data'].get("domain"):
                                    del context['data']['domain']
                                return Response(context,status=status.HTTP_200_OK)                                       

                    elif data['purpose'] != 'Other Remittance':
                        if 'purpose_note' not in data: 
                            context = {
                                'status':True,
                                'data': {
                                    'transaction_no':parent_transaction.transactionno,
                                'debit_account_details':{
                                    'debit_account':request.data['debit_account'],
                                    'sender_name':sender_name,
                                    'from_currency_code':from_currency_code,
                                    'amount':format(float(request.data['debit_amount']), ".2f"),
                                },
                                'credit_account_details':{          
                                    'beneficiary_account':request.data['beneficiary_account'],
                                    'beneficiary_name':request.data['beneficiary_name'],
                                    'bank_name':request.data['bank_name'],
                                    'bankswift_code':request.data['bankswift_code'],
                                    'bank_city':request.data['bank_city'],
                                    'bank_country':request.data['bank_country'],
                                    'currency_code':request.data['currency_code'],
                                    'purpose':request.data['purpose'],
                                    'note':request.data['note'] if request.data.get('note') else None ,
                                    'beneficiary_email':request.data['beneficiary_email'] if request.data.get('beneficiary_email') else None ,
                                    'user_box_no':request.data['user_box_no'] if request.data.get('user_box_no') else None,
                                    'user_street':request.data['user_street'] if request.data.get('user_street') else None,
                                    'user_city':request.data['user_city'] if request.data.get('user_city') else None,
                                    'user_state':request.data['user_state'] if request.data.get('user_state') else None,
                                    'user_country':request.data['user_country'] if request.data.get('user_country') else None,
                                    'user_phone':request.data['user_phone'] if request.data.get('user_phone') else None,                                            
                                },
                                'conversion_fee' : format(conversion_fee, ".2f"),
                                'wire_transfer_fee' : format(self.wire_transfer_fee,".2f"),
                                'cable_charge' : format(self.cable_charge, ".2f"),
                                'debit_amount' : format(debit_amount, ".2f"),
                                'credit_amount' : format(self.credit_amount, ".2f"),
                                'has_invoice':int(request.data.get('has_invoice')),
                                'invoice_doc' : request.FILES['invoice_doc'].name,
                                    }
                                }
                            if context['data'].get("domain"):
                                del context['data']['domain']
                            return Response(context,status=status.HTTP_200_OK)               

            elif data['has_invoice'] == '1' and data['ownaccount'] == 'True':
                if 'invoice_doc' in data:
                    if data['purpose'] == 'Other Remittance':
                        if 'purpose_note' in data:
                            if data['purpose_note'] != '':
                                context = {
                                    'status':True,
                                    'data': {
                                        'transaction_no':parent_transaction.transactionno,
                                    'debit_account_details':{
                                        'debit_account':request.data['debit_account'],   
                                        'sender_name':sender_name,
                                        'from_currency_code':from_currency_code, 'amount':format(float(request.data['debit_amount']), ".2f"), 
                                    },
                                    'credit_account_details':{
                                        'beneficiary_account':request.data['beneficiary_account'],
                                        'beneficiary_name':request.data['beneficiary_name'],
                                        'bank_name':request.data['bank_name'],
                                        'bankswift_code':request.data['bankswift_code'],
                                        'bank_city':request.data['bank_city'],
                                        'bank_country':request.data['bank_country'],
                                        'currency_code':request.data['currency_code'],
                                        'purpose':request.data['purpose'],
                                        'purpose_note':request.data['purpose_note'],
                                        'note':request.data['note'] if request.data.get('note') else None,
                                        'beneficiary_email':request.data['beneficiary_email'] if request.data.get('beneficiary_email') else None,
                                        'user_phone':request.data['user_phone'] if request.data.get('user_phone') else None,
                                        },                                        
                                        'conversion_fee' : format(conversion_fee, ".2f"),
                                        'wire_transfer_fee' : format(self.wire_transfer_fee,".2f"),
                                        'cable_charge' : format(self.cable_charge, ".2f"),
                                        'debit_amount' : format(debit_amount, ".2f"),
                                        'credit_amount' : format(self.credit_amount, ".2f"),
                                        'has_invoice':int(request.data.get('has_invoice')),
                                        'invoice_doc' : request.FILES['invoice_doc'].name,
                                        }
                                    }
                            if context['data'].get("domain"):
                                del context['data']['domain']
                            return Response(context,status=status.HTTP_200_OK)                               
                    elif data['purpose'] != 'Other Remittance':
                        if 'purpose_note' not in data: 
                            context = {
                                'status':True,
                                'data':{
                                    'transaction_no':parent_transaction.transactionno,
                                'debit_account_details':{
                                    'debit_account':request.data['debit_account'],
                                    'sender_name':sender_name,
                                    'from_currency_code':from_currency_code,
                                    'amount':format(float(request.data['debit_amount']), ".2f"),
                                },
                                'credit_account_details':{
                                    'beneficiary_account':request.data['beneficiary_account'],
                                    'beneficiary_name':request.data['beneficiary_name'],
                                    'bank_name':request.data['bank_name'],
                                    'bankswift_code':request.data['bankswift_code'],
                                    'city':request.data['bank_city'],
                                    'bank_city':request.data['bank_country'],
                                    'currency_code':request.data['currency_code'],
                                    'purpose':request.data['purpose'],
                                    'note':request.data['note'] if request.data.get('note') else None,
                                    'beneficiary_email':request.data['beneficiary_email'] if request.data.get('beneficiary_email') else None,
                                    'user_phone':request.data['user_phone'] if request.data.get('user_phone') else None,    
                                },                                    
                                'conversion_fee' : format(conversion_fee, ".2f"),
                                'wire_transfer_fee' : format(self.wire_transfer_fee,".2f"),
                                'cable_charge' : format(self.cable_charge, ".2f"),
                                'debit_amount' : format(debit_amount, ".2f"),
                                'credit_amount' : format(self.credit_amount, ".2f"),
                                'has_invoice':int(request.data.get('has_invoice')),
                                'invoice_doc' : request.FILES['invoice_doc'].name,                   
                                    }
                                }
                        if context['data'].get("domain"):
                            del context['data']['domain']
                            return Response(context,status=status.HTTP_200_OK) 

            else:
                context = {
                    'status':False,
                    'error':{
                        'message' : 'Your Transaction has been declined due to Security reason' 
                        }
                }
                return Response(context,status=status.HTTP_404_NOT_FOUND)       
        else:
            context = {
                "status": False,
                "errors": seriliazer.errors,
                "message" : "validation error",
                }
            return Response(context,status=status.HTTP_404_NOT_FOUND)
    
class Currency_Conversion_APIView(APIView,APIV1UtilMixins,FindAccount):
    serializer_class = Currency_ConversionSerializer
    authentication_classes = [APIAccessTokenPermissions]
    permission_classes = [AccountVerifiedPermission,AccountlockedPermissionforextapi,AccountTransactionPermission]
    def post(self,request):
        seriliazer = Currency_ConversionSerializer(data=request.data, context = {'currencyconversion': True})
        if seriliazer.is_valid():
            try:
                try:
                    debit_account = Accounts.objects.get(accountno=request.POST.get("debit_account"),createdby=request.user)
                except Exception as e:
                    context={
                        'status':False,
                        'error':{
                            "debit_account": [
                            "Account does not exists"
                            ]
                        },
                        "message":"validation error"
                    }
                    return Response(context,status=status.HTTP_404_NOT_FOUND)
                debit_acc_no = debit_account.accountno
                debit_acc_curr_code = debit_account.currency.code
                try:
                    credit_account = Accounts.objects.get(accountno=request.POST.get("credit_account"),createdby=request.user)
                except Exception as e:
                    context={
                        'status':False,
                        'error':{
                            "credit_account": [
                            "Account does not exists"
                            ]
                        },
                        "message":"validation error"
                    }
                    return Response(context,status=status.HTTP_404_NOT_FOUND)
                credit_acc_no = credit_account.accountno
                credit_acc_curr_code = credit_account.currency.code
                net_amount = round(Decimal(request.POST.get("net_amount")),2)
                note = request.POST.get("note") 
                conversion_fee = round(net_amount * Decimal(0.5 / 100),2)
                debit_amount = net_amount + conversion_fee
                debit_acc_balance = debit_account.balance
            except Exception as e:
                logger.info(e)
                debit_acc_balance = None
            context = json.loads(json.dumps(request.data))
        
            currency_conversion = Currencyconversionratescombined.objects.get(fromcurrency__code=debit_acc_curr_code,
                                                                            tocurrency__code=credit_acc_curr_code,
                                                                        isdeleted=False)
            conversionrate = round(currency_conversion.conversionrate,4)
            
            try:
                currency_margin = Currencyconversionmargins.objects.get(fromcurrency__code=debit_acc_curr_code, tocurrency__code=credit_acc_curr_code, isdeleted=False)
                margin_rate = currency_margin.marginpercent
                conversionrate = conversionrate - (conversionrate* Decimal(float(margin_rate)/100))
            except Exception as e:
                logger.info(e)
            credit_amount = round(net_amount * conversionrate,2)                    
            debit_account = Accounts.objects.get(accountno=request.POST.get("debit_account"))
            credit_account = Accounts.objects.get(accountno=request.POST.get("credit_account"))
            net_amount = round(Decimal(request.POST.get("net_amount")),2)
            debit_acc_no = debit_account.accountno
            note = request.data.get("note") if request.data.get("note") else ""
            conversion_fee = round(net_amount * Decimal(0.5 / 100),2)
            debit_amount = net_amount + conversion_fee
            debit_acc_curr_code = debit_account.currency.code
            credit_acc_no = credit_account.accountno
            credit_acc_curr_code = credit_account.currency.code
            currency_conversion = Currencyconversionratescombined.objects.get(
                fromcurrency__code=debit_acc_curr_code, tocurrency__code=credit_acc_curr_code, isdeleted=False)
            conversionrate = round(currency_conversion.conversionrate,4)
            currency_margin = Currencyconversionmargins.objects.get(fromcurrency__code=debit_acc_curr_code, tocurrency__code=credit_acc_curr_code, isdeleted=False)
            margin_rate = currency_margin.marginpercent
            conversionrate = conversionrate - (conversionrate* Decimal(float(margin_rate)/100))     
            try:
                account_number_prev = Transactions.objects.latest('transactionno').transactionno
            except Exception as e:
                logger.info(e)
                account_number_prev = 10000000
            try:
                transactionno = int(account_number_prev) + 1
                debit_accountno = debit_account.accountno
                credit_accountno = credit_acc_no
                fromamount = net_amount
                toamount = round(net_amount * conversionrate,2)
                conversion_fee = conversion_fee
                debit_account = Accounts.objects.get(accountno=debit_accountno)
                credit_account = Accounts.objects.get(accountno=credit_accountno)
                debit_account.balance = float(debit_account.balance) - float(fromamount)
                credit_account.balance = float(credit_account.balance) + float(toamount)
                debit_account.save()
                credit_account.save()
                Transactiontypes.objects.get_or_create(name='Currency Conversion') #TODO: to be removed in production
                def create_transaction(transactionno, debit_account, credit_account, fromamount, toamount, debit_balance, credit_balance, amount_type):
                    tr_obj = Transactions.objects.create(
                        transactionno=transactionno,
                        fromaccount=debit_account,
                        toaccount=credit_account,
                        fromamount=fromamount,
                        toamount=toamount,
                        transactiontype=Transactiontypes.objects.get(name='Currency Conversion'),
                        createdby=request.user,
                        note=request.data.get('note'),
                        fromaccountbalance=debit_balance,
                        toaccountbalance=credit_balance,
                        amount_type=amount_type,
                    )
                    add_log_action(request, tr_obj, status=f"transaction(Currency Conversion : amount type {tr_obj.amount_type}) created for account {str(tr_obj.fromaccount.accountno)}", status_id=1)
                    return tr_obj
                debit_balance = debit_account.balance
                credit_balance = credit_account.balance

                tr_deb_amount = create_transaction(transactionno, debit_account,credit_account, fromamount, toamount, debit_balance,
                                credit_balance, amount_type="Net Amount")

                # Add conversion fee to corresponding currency of master account
        
                try:
                    credit_account,converted_conversion_fee = self.find_master_account_convert_amount(debit_account, conversion_fee,debit_account.user_account.test_account)
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
                    context ={
                        'status':True,
                        'data': {
                                'transaction_number': transactionno,
                            'debit_account_details': {
                                'debit_account':debit_acc_no,
                                'balance':str(round(debit_account.balance,2)),
                                'debit_account_currency_code':debit_acc_curr_code,
                            },
                            'credit_account_details': {
                                'credit_account':credit_acc_no,
                                'credit_account_currency_code':credit_acc_curr_code,  
                            },
                            'note':note,
                            'conversion_rate':str(round(conversionrate,4)),
                            'net_amount':str(net_amount),
                            'conversion_fee':str(conversion_fee),
                            'debit_amount':str(debit_amount),
                            'credit_amount':str(toamount),
                            'request':request,                                                                               
                            }
                        }
                    if context['data']['request']:
                        del context['data']['request']                            
                    if context['data'].get("domain"):
                        del context['data']['domain']
                    return Response(context,status=status.HTTP_200_OK)
                except Exception as e:
                    logger.info(e)                        
            except Exception as e:
                logger.info(e)            
        else: 
            context = {
                'status':False,
                'errors':seriliazer.errors,
                'message':'validation error'
            }
            return Response(context,status=status.HTTP_404_NOT_FOUND)
   


                        
class AccountsListAPIview(generics.ListAPIView,APIV1UtilMixins):
    """
    This view should return a list of all Accounts
    """       
    serializer_class = GetaccountSerializer
    authentication_classes = [APIAccessTokenPermissions]
    permission_classes = [IsAuthenticated]       
    def get(self,request):
        accounts = Accounts.objects.filter(user_account__customer__user=request.user, isdeleted=False)   
        data_list = {}
        data_list["status"] = 1
        data_list['accounts'] = []
        context={
            'status':True,
            'data':{'accounts':data_list['accounts']}
        }
        for account in accounts:
            new_data_list = {}
            new_data_list['account_number'] = account.accountno
            new_data_list['currency'] = account.currency.code
            new_data_list['balance'] = str(round(account.balance,2))
            data_list['accounts'].append(new_data_list)
        return Response(context,status=status.HTTP_200_OK)
        


class StripeSessionAPIView(APIView,APIV1UtilMixins):
    serializer_class = CheckoutSerializer
    queryset = Stripe_Customer.objects.all()
    authentication_classes = [APIAccessTokenPermissions]
    def post(self,request):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        serialiazer = CheckoutSerializer(data=request.data)
        if serialiazer.is_valid():
            serialiazer_data  = serialiazer.data
            try:
                try:
                    customer_stripe, strip = Stripe_Customer.objects.update_or_create(
                        email=request.data.get('email'), 
                        line1 =request.data.get('line1'),
                        line2 = request.data.get('line2'),  
                        postal_code = request.data.get('postal_code'),
                        city= request.data.get('city'),
                        state= request.data.get('state'),
                        country= request.data.get('country'),)
                    customer_stripe.card_holder_name =request.data.get('card_holder_name')
                    customer_stripe.description =request.data.get('description')
                    customer_stripe.save()
                    
                    if strip:
                        customer = stripe.Customer.create(
                            email =request.data.get('email'),
                            name=request.data.get('card_holder_name'),
                            address={
                                "line1":request.data.get('line1'),
                                "line2": request.data.get('line2'),
                                "city":request.data.get('city'),
                                "country":request.data.get('country'),
                                "postal_code":request.data.get('postal_code'),
                                "state":request.data.get('state')
                                },
                        )
                        customer_stripe.customer_id = customer['id']
                        customer_stripe.card_holder_name =request.data.get('card_holder_name')
                        customer_stripe.save()
                    else:
                        if customer_stripe.card_holder_name is not request.data.get('card_holder_name'):
                            name_customer =stripe.Customer.modify(customer_stripe.customer_id)
                            name_customer.card_holder_name = request.data.get('card_holder_name')
                            name_customer.description = request.data.get('description')
                            name_customer.address = {
                                "line1":request.data.get('line1'),
                                "line2": request.data.get('line2'),
                                "city":request.data.get('city'),
                                "country":request.data.get('country'),
                                "postal_code":request.data.get('postal_code'),
                                "state":request.data.get('state')
                                }
                            name_customer.save()
                        try:
                            customer = stripe.Customer.retrieve(customer_stripe.customer_id)
                        except stripe.error.InvalidRequestError as e:
                            logger.info(e)
                            customer = stripe.Customer.create(
                                email =request.data.get('email'),
                                name=request.data.get('card_holder_name'),
                                address={
                                "line1":request.data.get('line1'),
                                "line2": request.data.get('line2'),   
                                "city":request.data.get('city'),
                                "country":request.data.get('country'),
                                "postal_code":request.data.get('postal_code'),
                                "state":request.data.get('state')
                                }
                            )
                            customer_stripe.customer_id = customer['id']
                            customer_stripe.save()
                            logger.info("Updated customer {}-{} with newly created stripe customer ID {}".format(customer_stripe.id,customer_stripe.email,customer['id']))
                            
                    card_number =serialiazer_data['card_number']
                    exp_month = serialiazer_data['exp_month']
                    exp_year = serialiazer_data['exp_year']
                    cvc = serialiazer_data['cvc']
                    card_details=stripe.Token.create(
                        card={
                            "number": card_number,
                            "exp_month": exp_month,
                            "exp_year": exp_year,
                            "cvc": cvc,
                                }
                        )
                    customer_stripe.token_id = card_details["id"]
                    customer_stripe.save()
                    
                    # create payment method
                    paymentmethod = stripe.PaymentMethod.create(
                        type="card",
                        card={
                            "number": card_number,
                            "exp_month": exp_month,
                            "exp_year": exp_year,
                            "cvc": cvc,
                                }
                    )
                    
                    amount = int(float(serialiazer_data['amount']) * 100 )# to least value in currency. eg: if $50 provided, will convert to 5000 cents. 
                    currency =serialiazer_data['currency']   
                    description = request.data['description']
                    
                    payment  = stripe.PaymentIntent.create(
                            amount=amount,
                            currency=currency,
                            payment_method_types=['card'],
                            capture_method= 'automatic',
                            confirm=True,
                            payment_method=paymentmethod["id"],
                            customer=customer['id'],
                            off_session=True,
                            description=description,
                            shipping={
                                "name": request.data.get('card_holder_name'),
                                "address": {
                                "line1":request.data.get('line1'),
                                "line2": request.data.get('line2'),
                                "city":request.data.get('city'),
                                "country":request.data.get('country'),
                                "postal_code":request.data.get('postal_code'),
                                "state":request.data.get('state')
                                },
                            },
                            )      

                    Stripe_Transaction.objects.get_or_create(amount=serialiazer_data['amount'],currency=serialiazer_data['currency'], transaction_id=payment['id'],customer= Stripe_Customer.objects.filter(email= request.data.get('email')).first())
                
                    
                    context = {
                    "status":True,
                    'data':{
                        'customer':{
                        'card_holder_name':request.data.get('card_holder_name'),
                        'email':customer.get("email"),
                        'customer_id' : customer.get('id'),
                            },
                        'card':{
                            'id':card_details.get('id'),
                            'card_number':card_number,
                            'exp_month':exp_month,
                            'exp_year' : exp_year,
                            'cvc' : cvc       
                            },
                        'Payment_details':{
                            'transaction_id':payment['id'],
                            "payment_method_types":payment['payment_method_types'],
                            'amount' :str(round(Decimal((amount)/100),2)),
                            'currency':currency,
                            'description':description,
                                'shipping':{
                                "address": {
                                "line1":request.data.get('line1'),
                                "line2": request.data.get('line2'),
                                "city":request.data.get('city'),
                                "country":request.data.get('country'),
                                "postal_code":request.data.get('postal_code'),
                                "state":request.data.get('state')
                                },
                            }
                            }
                    }
                    }
                    return Response(context,status=status.HTTP_200_OK)
                except stripe.error.CardError as e:
                    logger.info(e)
                    context = {
                        'status':False,
                        'error':{
                            'code':e.code,
                            'message':e.user_message
                        }                       
                    }
                    return Response(context,status=status.HTTP_404_NOT_FOUND)
                except stripe.error.RateLimitError as e:
                    logger.info(e)
                    context = {
                        'status':False,
                        'error':{
                            'code':e.code,
                            'message':e.user_message
                        }
                    }
                    return Response(context,status=status.HTTP_404_NOT_FOUND)
                except stripe.error.InvalidRequestError as e:
                    logger.info(e)
                    context = {
                        'status':False,
                        'error':{
                            'code':e.code,
                            'message':e.user_message
                        }
                    }
                    return Response(context,status=status.HTTP_404_NOT_FOUND)
               
                except stripe.error.AuthenticationError as e:
                    logger.info(e)
                    context = {
                        'status':False,
                        'error':{
                            'code':e.code,
                            'message':e.user_message
                        }
                    }
                    return Response(context,status=status.HTTP_404_NOT_FOUND)
                except stripe.error.APIConnectionError as e:
                    logger.info(e)
                    context = {
                        'status':False,
                        'error':{
                            'code':e.code,
                            'message':e.user_message
                        }
                    }
                    return Response(context,status=status.HTTP_404_NOT_FOUND)
                except stripe.error.StripeError as e:
                    logger.info(e)
                    context = {
                            'status':False,
                            'error':{
                            'code':e.code,
                            'message':e.user_message
                        }
                        }
                    return Response(context,status=status.HTTP_404_NOT_FOUND)
                except Exception as e:
                    logger.info(e)
                    return Response({})
            except Exception as e:
                logger.info(e)  
        else:
            context={
                'status':False,
                'errors':serialiazer.errors,
                'message':'Validation error'
            }
            return Response(context,status=status.HTTP_404_NOT_FOUND)

