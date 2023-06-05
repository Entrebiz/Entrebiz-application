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
                          Cryptobeneficiaries, WalletWithdrawalTransactions, APIaccessToken, DomesticBeneficiary,
                          DomesticTransaction)
from django.contrib.admin.models import LogEntry
class StateAdmin(admin.ModelAdmin):
    list_display = ('Customer','fullname','number','activestatus','phoneverified')
    search_fields = ("fullname",'customer__user__email','phonenumber')
    def number(self, obj):
        if obj.phonenumber and obj.countrycode:
            return "{} {}".format(obj.countrycode,obj.phonenumber)
        else:
            return 'N/A'
    def Customer(self, obj):
        return obj.customer.user.email
admin.site.register(Useraccounts,StateAdmin)

class StateToken(admin.ModelAdmin):
    list_display = ('key','user','createdon')
    search_fields = ('user__email',)
admin.site.register(APIaccessToken,StateToken)

class StateAPikey(admin.ModelAdmin):
    list_display = ('apikey', 'user', 'createddate')
    search_fields = ('user__email',)
admin.site.register(Apiaccesskeygenerate,StateAPikey)



class ActivationlinksAdmin(admin.ModelAdmin):

    search_fields = ['link','createdby__email']
    list_display = ['createdby','created_date','validtill', 'transactiontype', 'validated', 'activationcode']
    
    def created_date(self,obj):
        return obj.createdon.date()
    
    

class OtpsAdmin(admin.ModelAdmin):
    
    search_fields = ['code','createdby__email','transactiontype']
    list_display = ['createdby','code','created_date','validtill','validated','transactiontype']
    
    def created_date(self,obj):
        return obj.createdon.date()

   
class InternationaltransactionsAdmin(admin.ModelAdmin):
    
    search_fields = ['transaction__transactionno','accountnumber','transaction__fromaccount__accountno','createdby__email']
    list_display = ['transaction_no','from_accountnumber','to_accountnumber','currency','createdby','created_date','verificationstatus','isdeleted']
    
    def transaction_no(self,obj):
        if obj.transaction:
            return str(obj.transaction.transactionno)
    
    def to_accountnumber(self, obj):
        if obj.accountnumber:
            return obj.accountnumber
    
    def from_accountnumber(self, obj):
        if obj.transaction.fromaccount:
            return obj.transaction.fromaccount.accountno
    
    def created_date(self,obj):
        return obj.createdon.date()

    
class TransactionsAdmin(admin.ModelAdmin):
    
    search_fields = ['transactionno','fromaccount__accountno','toaccount__accountno','createdby__email']
    list_display = ['transactionno','from_account','to_account','fromamount','toamount','createdby','created_date','recipientname','fromaccountbalance','toaccountbalance'] 
    
    def from_account(self, obj):
        if obj.fromaccount:
            return obj.fromaccount.accountno
    
    def to_account(self, obj):
        if obj.toaccount:
            return obj.toaccount.accountno
        
    def created_date(self,obj):
        return obj.createdon.date()
   

admin.site.register(Accounts)
admin.site.register(TemporaryCred)
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
admin.site.register(Transactions,TransactionsAdmin)
admin.site.register(Activationlinks,ActivationlinksAdmin)
admin.site.register(Activitylog)
admin.site.register(Admins)
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
admin.site.register(Internationaltransactions,InternationaltransactionsAdmin)
admin.site.register(Otps,OtpsAdmin)
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
admin.site.register(Cryptobeneficiaries)
admin.site.register(WalletWithdrawalTransactions)
admin.site.register(LogEntry)
admin.site.register(DomesticBeneficiary)
admin.site.register(DomesticTransaction)
# admin.site.register(UpiPayments)
