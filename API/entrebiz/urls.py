"""entrebiz URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts import views as acc_views
from UserDetails import views as usr_views
from Transactions import views as tr_views
from Transactions.accounttoaccount import views as ta_views
from Transactions.Idverification import views as id_views
from Transactions.companyVerification import views as cpny_views
from Transactions.addressVerification import views as av_views
from accounts.businessaccount import views as bsacc_views
from Transactions.ReportMissingPayment import views as rp_views
from Transactions.inwardRemittance import views as ir_views
from utils import views as u_views
from EntrebizAdmin import views as admin_views
from EntrebizAdmin.currencyManagement import views as cr_views
from EntrebizAdmin.inwardRemittanceApproval import views as ira_views
from entrebiz import settings

urlpatterns = [
                  path('admin/', admin.site.urls),
                  # Accounts
                  path('', acc_views.DashboardView.as_view()),
                  path('login', acc_views.LoginView.as_view()),
                  path('logout', acc_views.user_logout),
                  path('beneficiary/', acc_views.ManageBeneficiaryView.as_view()),
                  path('beneficiary/list/', acc_views.BeneficiaryListView.as_view()),
                  path('beneficiary/edit/', acc_views.UpdateBeneficiaryView.as_view()),
                  path('dashboard', acc_views.AccountListView.as_view()),
                  path('settings/deleteCurrency', acc_views.RemoveCurrencyView.as_view()),
                  path('twoStepVerification', acc_views.TwoStepVerificationView.as_view()),
                  # Transactions

                  path('verification/addressList', av_views.AddressVerification.as_view(), name='address-list'),
                  path('documentVerification/addressEdit', av_views.AddressEdit.as_view(), name='address-edit'),
                  path('international-wire-transfer/', tr_views.InternationalWireTransfer.as_view(),
                       name='international-wire-transfer'),
                  path('wire-transfer-confirm/<str:token>', tr_views.WireTransferConfirm.as_view(),
                       name='wire-transfer-confirm'),
                  path('cutomer-account-balance', tr_views.cutomer_account_balance),
                  path('getbeneficiarylist', tr_views.getbeneficiarylist),
                  path('cancel-wire-transfer', tr_views.CancelWireTransfer.as_view(), name='cancel-wire-transfer'),
                  path('international-wire-transfer/wireOtp/<str:token>', tr_views.WireTransferOtp.as_view(),
                       name='international-wire-transfer-wireOtp'),
                  path('international-wire-transfer/success/<str:token>', tr_views.WireTransferSuccess.as_view(),
                       name='international-wire-transfer-success'),
                  path('wire-tr-invoice-mail/<str:token>', tr_views.WireTransactionInvoiceMail.as_view(),
                       name='wire-tr-invoice-mail'),
                  path('show-user-details', tr_views.ShowUserDetails.as_view()),
                  # Transactions : Account to account

                  # path('download_pdf/<id>', ta_views.GeneratePdf.as_view(), name="download_pdf"),
                  #   path('check-amount', ta_views.getamount),
                  path('interbeneficiarylist', ta_views.getInternalbeneficiarylist),
                  path('getaccountbalance', ta_views.accountbalance),
                  path('transaction/acc/', ta_views.AccountToAccountTransferView.as_view(), name="accTransaction"),
                  path('transaction/acc/Confirmation/?token=<str:token>',
                       ta_views.AccountToAccountDetailsView.as_view(), name="accConfirmation"),
                  path('transactionCancel', ta_views.AccountToAccountCancelView.as_view(), name="accCancel"),
                  path('transaction/accOtp/?accessToken=<str:token>', ta_views.AccountToAccountOTP.as_view(),
                       name="accOtp"),
                  path('transaction/accTransactionSuccess/?accessToken=<str:token>',
                       ta_views.AccountToAccountOTPSuccess.as_view(), name="accSuccess"),

                  # Transaction : Currency conversion
                  path('conversion', tr_views.CurrencyConversionView.as_view(),
                       name='conversion'),
                  path('conversionConfirm', tr_views.CurrencyConversionConfirmView.as_view(),
                       name='conversion_confirm'),
                  path('conversionSuccess', tr_views.ConversionSuccessView.as_view(),
                       name='conversion_confirm'),
                  path('cancelConversion', tr_views.ConversionCancelView.as_view(),
                       name='cancel_conversion'),

                  # Transaction : E Statements
                  path('statements', tr_views.EStatementsView.as_view(), name='statements'),
                  path('statements/transaction', tr_views.GetTransactionDetailsView.as_view(),
                       name='statements_transaction'),

                  # Userdetails

                  path('settings/personal', usr_views.PersonalDetailsView.as_view()),
                  path('verifyOTP', usr_views.OTPVerifyView.as_view()),
                  path('sendVerificationOTP', usr_views.VerificationOTPSendView.as_view()),
                  path('settings/personal/edit/', usr_views.EditPersonalDetailsView.as_view()),
                  path('settings/personal/confirm/', usr_views.ConfirmEditDetailsView.as_view()),
                  path('settings/twoFactor', usr_views.EditTwoFactorAuthenticationView.as_view()),
                  path('settings/otpMethod', usr_views.EditOTPMethodView.as_view()),
                  path('settings/changePassword', usr_views.ChangePassword.as_view()),
                  path('settings/cancelpasswordchange', usr_views.CancelPasswordChange.as_view()),

                  # path('getdocumentfeilds',id_views.getdocumentfeilds),
                  path('verification/idList', id_views.IdVerificationView.as_view(), name="idList"),
                  path('documentVerification/idEdit', id_views.IdEditView.as_view(), name="IdEdit"),

                  #  registration
                  path('register/personal', acc_views.PersonalSignUp.as_view()),
                  path('register/personalSignUpConfirm', acc_views.PersonalSignUpConfirm.as_view()),
                  path('setPassword/', acc_views.SetPassword.as_view()),
                  path('pageStatus/', acc_views.PageStatus.as_view()),
                  path('show-document-fields/', acc_views.ShowDocumentFields.as_view()),

                  # companyVerification
                  path('document-fields/', cpny_views.DocumentFields.as_view(), name='document-fields'),
                  path('documentVerification/companyList', cpny_views.CompanyVerificationView.as_view(),
                       name='CompanyList'),
                  path('documentVerification/companyEdit', cpny_views.CompanyEdit.as_view(), name='CompanyEdit'),

                  # businessaccount registration
                  path('register/account', bsacc_views.AccountRegistrationView.as_view(), name='registration'),
                  path('register/business/', bsacc_views.BusinessAccountRegistrationView.as_view(),
                       name='business-account-registration'),
                  path('register/businessSignUpConfirm', bsacc_views.BusinessAccountConfirmView.as_view(),
                       name="business-account-confirm"),
                  path('settings/updateCompanydetails', bsacc_views.CompanyDetailsView.as_view(),
                       name="company-details"),
                  path('settings/companydetails/edit/', bsacc_views.EditCompanyDetailsView.as_view(),
                       name="company-details-edit"),
                  path('settings/companydetails/confirm/', bsacc_views.ConfirmCompanyDetailsView.as_view(),
                       name="company-details-edit-confirm"),
                  path('settings/users',bsacc_views.ViewUsers.as_view(),name="view-users"),
                  path('settings/viewUserDetails',bsacc_views.ViewUserDetails.as_view(),name="view-user"),
                  path('settings/addNewUser',bsacc_views.AddMoreUser.as_view(),name="add-user"),
                  path('deactivate-account',bsacc_views.Dactivateaccount.as_view()),
                  path('send-permission-request',bsacc_views.PermissionEmail.as_view()),

                  # report a missing payment
                  path('tracePayment/list', rp_views.MissingPaymentList.as_view()),
                  path('tracePayment/addTracePayment', rp_views.AddTracePayment.as_view()),

                  # inward remittance details
                  path('receiveMoney', ir_views.InwardRemittance.as_view()),
                  path('receiveMoneySuccess', ir_views.InwardRemittanceSuccess.as_view()),
                  path('fetch-bank-details', ir_views.BankDetails.as_view()),

                  #company info
                  path('aboutUs', u_views.AboutUs.as_view()),
                  path('services', u_views.Services.as_view()),
                  path('termsAndCondition', u_views.TermsAndCondition.as_view()),
                  path('privacyPolicy', u_views.PrivacyPolicy.as_view()),

               #    forgot password
                  path('forgotPassword', usr_views.ForgotPassword.as_view()),
                  path('forgotPasswordSuccess', usr_views.ForgotPasswordSuccess.as_view()),

                  # entrebiz admin
               #    path('ebzadmin/login', admin_views.AdminLogin.as_view()),
               #    path('ebzadmin/dashboard', admin_views.AdminDashboardView.as_view()),
               #    path('volume', admin_views.Volume.as_view()),
               #    path('adminUserManagement', admin_views.AdminUserManagement.as_view()),
               #    path('addAdminUsers', admin_views.AddAdminUser.as_view()),
               #    path('editAdminUser/', admin_views.EditAdminUser.as_view()),
               #    path('filter-admin', admin_views.FilterAdmin.as_view()),

                  # entrebiz admin :  International wire tranfer requests
               #    path('transactions', admin_views.ManageWireTransferRequestsView.as_view()),
               #    path('getransactionDetails', admin_views.WireTransferRequestsDetailView.as_view()),

                  # bank management
               #    path('bankManagement', admin_views.BankManagement.as_view()),
               #    path('viewBank', admin_views.ViewBank.as_view()),
               #    path('editBank', admin_views.EditBank.as_view()),
               #    path('filter-bank', admin_views.FilterBank.as_view()),
               #    path('addBank', admin_views.AddBank.as_view()),

                  # customer management
               #    path('customerManagement', admin_views.CustomerManagement.as_view()),
               #    path('getCustomerDetails', admin_views.GetCustomerDetails.as_view()),
               #    path('viewImageDetails', admin_views.ViewImageDetails.as_view()),
               #    path('sendMail', admin_views.SendMail.as_view()),
               #    path('filter-customers', admin_views.FilterCustomers.as_view()),
               #    path('getStatements', admin_views.GetStatements.as_view()),
               #    path('addReferral', admin_views.AddReferral.as_view()),
               #    path('deleteReferral', admin_views.DeleteReferral.as_view()),

                  # entrebiz admin : inward remittance requests
               #    path('receiveMoneyRequest', admin_views.AdminInwardRemittanceRequestsListView.as_view()),
               #    path('viewReceiveRequest', admin_views.AdminInwardRemittanceRequestsDetailView.as_view()),

                  # entrebiz admin : inward remittance manage
               #    path('inwardRemittance', admin_views.AdminInwardRemittanceManageView.as_view()),

                  #currency management
               #    path('currencyManagement',cr_views.CurrencyManagement.as_view()),

                  #inward remittance approval
               #    path('inwardRemittanceStatus',ira_views.InwardRemittanceStatus.as_view()),
               #    path('inwardRemittancePending',ira_views.InwardRemittancePending.as_view()),

                # API - V1
               path('api-auth/', include('rest_framework.urls')),
               path('api/v1/', include('api.v1.urls')),

              ] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
              

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    handler404 = "Transactions.accounttoaccount.views.page_not_found_view"
    handler500 = "Transactions.accounttoaccount.views.server_error"
    handler503 = "Transactions.accounttoaccount.views.server_unavailable"

# from django.views.csrf import csrf_failure