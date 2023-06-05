from django.contrib import admin

# Register your models here.

from utils.models import (Accounts, Customers, TemporaryCred, Useraccounts, Internalbeneficiaries, Currencies,
                          Externalbeneficiaries, Countries, Transactiontypes, Transactions, Activationlinks,
                          Activitylog, Admins, Apiaccesskeygenerate, Bankdetail, Industrytypes, Businessdetails,
                          Cablecharges, Conversioncharges, Conversionfeecharges, Currencyconversionmargins,
                          Referralfeetransactiondetails,
                          Currencyconversionrates, Currencyconversionratescombined, Documenttypes, Documentfields,
                          Documenttypesforverification, Customerdocuments, Customerdocumentfiles, Comments,
                          Referrerdetails,
                          Customerdocumentdetails, Internationaltransactions, Otps, Receivemoney, AdminAccount,
                          Incomingtracepayment, CurrencyConversionAPI,
                          Supportqueries, Transactionauthoritytypes, Transactionpurposetype, Userapikey,
                          InvoiceDocument, Businesstransactionauthorities, RefundRequests, Inwardremittancetransactions,
                          APIaccessToken,Stripe_Customer,Stripe_Transaction)
from django.contrib.admin.models import LogEntry

admin.site.register(Accounts)
admin.site.register(TemporaryCred)
admin.site.register(Useraccounts)
admin.site.register(Referralfeetransactiondetails)
admin.site.register(Referrerdetails)
admin.site.register(Comments)
admin.site.register(AdminAccount)
admin.site.register(Incomingtracepayment)
admin.site.register(Customers)
admin.site.register(Internalbeneficiaries)
admin.site.register(Externalbeneficiaries)
admin.site.register(Currencies)
admin.site.register(Transactiontypes)
admin.site.register(Transactions)
admin.site.register(Activationlinks)
admin.site.register(Activitylog)
admin.site.register(Admins)
admin.site.register(Apiaccesskeygenerate)
admin.site.register(Bankdetail)
admin.site.register(Industrytypes)
admin.site.register(Businessdetails)
admin.site.register(Cablecharges)
admin.site.register(Conversioncharges)
admin.site.register(Conversionfeecharges)
admin.site.register(Currencyconversionmargins)
admin.site.register(Currencyconversionrates)
admin.site.register(Currencyconversionratescombined)
admin.site.register(Documenttypes)
admin.site.register(Documentfields)
admin.site.register(Documenttypesforverification)
admin.site.register(Customerdocuments)
admin.site.register(Customerdocumentfiles)
admin.site.register(Customerdocumentdetails)
admin.site.register(Internationaltransactions)
admin.site.register(Otps)
admin.site.register(Receivemoney)
admin.site.register(Supportqueries)
admin.site.register(Transactionauthoritytypes)
admin.site.register(Transactionpurposetype)
admin.site.register(Userapikey)
admin.site.register(InvoiceDocument)
admin.site.register(Countries)
admin.site.register(Businesstransactionauthorities)
admin.site.register(RefundRequests)
admin.site.register(Inwardremittancetransactions)
admin.site.register(CurrencyConversionAPI)
admin.site.register(LogEntry)
admin.site.register(APIaccessToken)
admin.site.register(Stripe_Customer)
admin.site.register(Stripe_Transaction)
