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

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from accounts import views as acc_views
from entrebiz import settings
from EntrebizAdmin import views as admin_views
from EntrebizAdmin.country_management import views as cn_views
from EntrebizAdmin.currencyManagement import views as cr_views
from EntrebizAdmin.inwardRemittanceApproval import views as ira_views
from Transactions import views as tr_views
from Transactions.accounttoaccount import views as ta_views
from EntrebizAdmin.views import CrosscurrencyReportView

urlpatterns = [
    path("admin/", admin.site.urls),
    # Transaction : E Statements
    path("statements", tr_views.EStatementsView.as_view(), name="statements"),
    path("statements/transaction", tr_views.GetTransactionDetailsView.as_view(), name="statements_transaction"),
    # entrebiz admin
    path("", admin_views.AdminDashboardView.as_view()),
    path("login", admin_views.AdminLogin.as_view()),
    path("logout", acc_views.user_logout),
    path("dashboard", admin_views.AdminDashboardView.as_view()),
    path("volume", admin_views.Volume.as_view()),
    path("adminUserManagement", admin_views.AdminUserManagement.as_view()),
    path("addAdminUsers", admin_views.AddAdminUser.as_view()),
    path("editAdminUser/", admin_views.EditAdminUser.as_view()),
    path("filter-admin", admin_views.FilterAdmin.as_view()),
    # entrebiz admin :  International wire tranfer requests
    path("transactions", admin_views.ManageWireTransferRequestsView.as_view()),
    path("getransactionDetails", admin_views.WireTransferRequestsDetailView.as_view()),
    # bank management
    path("bankManagement", admin_views.BankManagement.as_view()),
    path("viewBank", admin_views.ViewBank.as_view()),
    path("editBank", admin_views.EditBank.as_view()),
    path("filter-bank", admin_views.FilterBank.as_view()),
    path("addBank", admin_views.AddBank.as_view()),
    # customer management
    path("customerManagement", admin_views.CustomerManagement.as_view()),
    path("getCustomerDetails", admin_views.GetCustomerDetails.as_view()),
    path("viewImageDetails", admin_views.ViewImageDetails.as_view()),
    path("sendMail", admin_views.SendMail.as_view()),
    path("filter-customers", admin_views.FilterCustomers.as_view()),
    path("getStatements", admin_views.GetStatements.as_view()),
    path("addReferral", admin_views.AddReferral.as_view()),
    path("editReferral", admin_views.EditReferral.as_view()),
    path("deleteReferral", admin_views.DeleteReferral.as_view()),
    path("password-reset-mail", admin_views.PasswordResetMail.as_view()),  # temporary
    # entrebiz admin : inward remittance requests
    path("receiveMoneyRequest", admin_views.AdminInwardRemittanceRequestsListView.as_view()),
    path("viewReceiveRequest", admin_views.AdminInwardRemittanceRequestsDetailView.as_view()),
    # entrebiz admin : inward remittance manage
    path("inwardRemittance", admin_views.AdminInwardRemittanceManageView.as_view()),
    # currency management
    path("currencyManagement", cr_views.CurrencyManagement.as_view()),
        # Crosscurrency Report
    path("crosscurrency-report", CrosscurrencyReportView.as_view()),
    
    # inward remittance approval
    path("inwardRemittanceStatus", ira_views.InwardRemittanceStatus.as_view()),
    path("inwardRemittancePending", ira_views.InwardRemittancePending.as_view()),
    path("404", ta_views.page_not_found_view),
    path("500", ta_views.server_error),
    # wallet withdrawel
    path("wallet-transactions", admin_views.ManageWalletWithdrawalTransferRequestsView.as_view()),
    path("get-wallet-transaction-details", admin_views.WalletWithdrawalTransferRequestsDetailView.as_view()),
    # coutry management
    path("country-management", cn_views.CountryManagementView.as_view()),
    path("edit-country", cn_views.ViewCountry.as_view()),
    path("add-country", cn_views.AddCountryView.as_view()),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    handler404 = "Transactions.accounttoaccount.views.page_not_found_view"
    handler500 = "Transactions.accounttoaccount.views.server_error"
    handler503 = "Transactions.accounttoaccount.views.server_unavailable"
