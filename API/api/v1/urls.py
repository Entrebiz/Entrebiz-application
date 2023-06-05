from django.urls import path

from api.v1.externalapiaccounttoaccount.views import ExternalAccountToAccountAPIView
from api.v1.externalapiauthentication.views import ExternalAuthenticationAPIView
from api.v1.externalapibeneficiary.views import BeneficiaryAPIView, BeneficiaryCreateAPIView, UpdateBeneficiaryAPIView, \
    DeleteBeneficiaryAPIView
from api.v1.externalapitransactions.views import ExternalTransactionAPIView
from api.v1.views import AuthenticateView, DashboardAccountsListView, CurrenciesListView, \
    CountriesListView, TranscationPurposeTypes, Logout, RemoveCurrencyView, TwoFactorAuthenticationAPIView, \
    TwoStepVerificationAPIView, EditOTPMethodAPIView, ChangePasswordAPIView, VerificationOTPSendAPIView, \
    OTPVerifyAPIView, PersonalDetailsAPIView, OTPVerifyPersonalDetailAPIView, \
    ConfirmEditDetailsAPIView, ForgotPasswordAPIView, CurrencyConversionAPIView, AccountToAccountTransferViewAPIView, \
    AccountToAccountOTPSendAPIView, AccountToAccountOTPValidateAPIView, AccountToAccountSuccessEmailAPIView, \
    InwardRemittanceAPIView, InwardRemittanceSuccessAPIView, InternationalWireTransferAPIView,ImageUploadView, \
    CompanyPermissionsAPIView,InwardRemittanceShowAPIView, UpdateCurrencyStatusAPIView, ReportMissingPaymet, IndustryTypeAPIView, ReferFriendView, ReferalApiView, NormalUserCreateView, BusinessAccountCreation,\
        Personal_DetailsAPIView,AccountsListAPIview,AccountAPIview,International_Wire_TransferAPIview,StripeSessionAPIView,Currency_Conversion_APIView



from api.v1.beneficiary.views import BeneficiaryListAPIView, UpdateORDeleteBeneficiaryAPIView, CreateBeneficiaryAPIView
from api.v1.companyaccount.views import CompanyDetailsAPIView
from api.v1.documentVerification.views import AddressVerificationAPIView, DocumentsTypesAPIView, \
   IdVerificationListAPIView, CompanyVerificationListAPIView
from api.v1.estatements.views import EStatementsAPIView, GetTransactionDetailsView

urlpatterns = [
    path('login/', AuthenticateView.as_view(), name='login'),
    path('accounts', DashboardAccountsListView.as_view(), name='accounts'),
    path('currencies', CurrenciesListView.as_view(), name='currencies'),
    path('countries', CountriesListView.as_view(), name='countries'),
    path('transactionpurposetypes', TranscationPurposeTypes.as_view(),name = 'transactionpurposetypes'),
  
    #beneficiary endpoint
    path('beneficiary/', CreateBeneficiaryAPIView.as_view()),
    path("beneficiary/list/", BeneficiaryListAPIView.as_view()),
    path('beneficiary/edit/<str:slug>',UpdateORDeleteBeneficiaryAPIView.as_view()),

    path('settings/deleteCurrency', RemoveCurrencyView.as_view(), name='removecurrency'),
    path('settings/twoFactor',TwoFactorAuthenticationAPIView.as_view(),name='twofactorauthentication'),
    path('twoStepVerification',TwoStepVerificationAPIView.as_view(),name='twostepverification'),
    path('otpMethod',EditOTPMethodAPIView.as_view(),name='otpMethod'),
    path('changePassword',ChangePasswordAPIView.as_view(),name='changepassword'),
    path('mobileverification',VerificationOTPSendAPIView.as_view(),name='mobileverification'),
    path('verifyOTP', OTPVerifyAPIView.as_view(),name='verifyotp'),
    path('settings/personal',PersonalDetailsAPIView.as_view(),name='personaldetail'),
    path('settings/personal/verifyotp', OTPVerifyPersonalDetailAPIView.as_view(), name='verifyotppersonaldetail'),
    path('settings/personal/confirm/',ConfirmEditDetailsAPIView.as_view(),name='personalconfirm'),
    path('conversion/',CurrencyConversionAPIView.as_view(),name='conversion'),
    path('forgotPassword', ForgotPasswordAPIView.as_view()),
    path('transaction/account/',AccountToAccountTransferViewAPIView.as_view(), name="accountTransaction"),
    path('transaction/account/otpsend/',AccountToAccountOTPSendAPIView.as_view(), name="accountTransactionotpsend"),
    path('transaction/account/otpvalidate/', AccountToAccountOTPValidateAPIView.as_view(), name="accountTransactionotpvalidate"),
    path('transaction/account/emailsend/',AccountToAccountSuccessEmailAPIView.as_view(),name="accounttoaccountemailsend"),
    path('receiveMoney/',InwardRemittanceAPIView.as_view(),name="inwardremittance"),
    path('receiveMoney/show/',InwardRemittanceShowAPIView.as_view(),name="inwardremittanceshow"),
    path('receiveMoney/success',InwardRemittanceSuccessAPIView.as_view(),name="inwardremittancesuccess"),
    path('updatecurrencystatus/',UpdateCurrencyStatusAPIView.as_view(),name="updatecurrencystatus"),
    path('logout/', Logout.as_view(), name='logout'),
    path('international-wire-transfer/',InternationalWireTransferAPIView.as_view(),name='wire-transfer'),
    path('company-permissions/',CompanyPermissionsAPIView.as_view(),name='company-permissions'),
    
    #document verification endpoints
    path('listdocumenttype', DocumentsTypesAPIView.as_view()),
    path('verification/addressList', AddressVerificationAPIView.as_view()),
    path('verification/idList', IdVerificationListAPIView.as_view()),
    path('verification/companyList', CompanyVerificationListAPIView.as_view()),

    path('usercreate/', NormalUserCreateView.as_view(),name= 'usercreate'),
    path('business-user-create/', BusinessAccountCreation.as_view(), name= 'businescreate' ),

    path('referals/',ReferalApiView.as_view(), name='referal'),
    path('refer-friend/', ReferFriendView.as_view(), name='referfrnd'),
    path('reportmisssingpayment/', ReportMissingPaymet.as_view(),name='report'),
    path('reportmisssingpayment/<int:pk>/', ReportMissingPaymet.as_view(), name= 'reportdelete'),
    
    #company details endpoints
    path('settings/updateCompanydetails',CompanyDetailsAPIView.as_view(),name='company_details'),
    
    path('conversion/',CurrencyConversionAPIView.as_view(),name='conversion'),
    path('industrytype',IndustryTypeAPIView.as_view()),
    
    #e-statement endpoints
    path('statements', EStatementsAPIView.as_view()),
    path('statements/transaction', GetTransactionDetailsView.as_view()),
    
    #image upload 
    path('image/',ImageUploadView.as_view()),



    # Personal Details
    path('accounts/user-details/', Personal_DetailsAPIView.as_view()),
    #External_api_authentication
    path('authenticate', ExternalAuthenticationAPIView.as_view()),
    path('transaction/account-to-account',ExternalAccountToAccountAPIView.as_view()),
    path('transactions/list',ExternalTransactionAPIView.as_view()),
    path('beneficiary/list',BeneficiaryAPIView.as_view()),
    path('beneficiary/create',BeneficiaryCreateAPIView.as_view()),
    path('beneficiary/update/<str:slug>',UpdateBeneficiaryAPIView.as_view()),
    path('beneficiary/delete/<str:slug>',DeleteBeneficiaryAPIView.as_view()),
   

    #Retrive a single account
    path('accounts/<pk>',AccountAPIview.as_view(),name='retrieve-account'),

    
    #Currency conversion
    path('transaction/currency-conversion/', Currency_Conversion_APIView.as_view(),name='currency_conversion'), 

    #Get accounts list
    path('accounts/',AccountsListAPIview.as_view(),name="account-list"),
    
    #stripe checkout 
    path('transaction/checkout/', StripeSessionAPIView.as_view()),
  
    #International wire transfer
    path('transaction/wire-transfer/', International_Wire_TransferAPIview.as_view(),name='international-wiretransfer'),   

]
