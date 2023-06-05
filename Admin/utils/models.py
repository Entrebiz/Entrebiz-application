from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from entrebiz import settings


class GetActiveManager(models.Manager):
    def get_queryset(self):
        return super(GetActiveManager, self).get_queryset().filter(isdeleted=False)

class Customers(models.Model):
    user = models.ForeignKey(User, related_name='customer_details', on_delete=models.CASCADE)
    customertype = models.SmallIntegerField()  # Field name made lowercase.
    address = models.CharField(max_length=2000, blank=True, null=True)  # Field name made lowercase.
    country = models.CharField(max_length=250, blank=True, null=True)  # Field name made lowercase.
    nationality = models.CharField(max_length=100, blank=True, null=True)  # Field name made lowercase.
    zipcode = models.CharField(max_length=100, blank=True, null=True)  # Field name made lowercase.
    agreetermsandconditions = models.BooleanField(default=False)  # Field name made lowercase.
    createdby = models.ForeignKey(User, related_name='customer_created_by', on_delete=models.SET_NULL, blank=True,
                                  null=True)  # Field name made lowercase.
    createdon = models.DateTimeField(auto_now_add=True)  # Field name made lowercase.
    modifiedby = models.ForeignKey(User, related_name='customer_modified_by', on_delete=models.SET_NULL, blank=True,
                                   null=True)  # Field name made lowercase.
    modifiedon = models.DateTimeField(auto_now=True)  # Field name made lowercase.
    isdeleted = models.BooleanField(default=False)  # Field name made lowercase.
    isactive = models.BooleanField(blank=True, null=True)  # Field name made lowercase.
    approvallevel = models.SmallIntegerField(blank=True, null=True)  # Field name made lowercase.
    verifieddoccount = models.SmallIntegerField(blank=True, null=True)  # Field name made lowercase.
    totaldoccount = models.SmallIntegerField(blank=True, null=True)  # Field name made lowercase.
    verifiedusers = models.SmallIntegerField(blank=True, null=True)  # Field name made lowercase.
    incomingreferralfee = models.DecimalField(max_digits=9, decimal_places=5,blank=True, null=True)  # Field name made lowercase.
    incomingcompanyfee = models.DecimalField(max_digits=9, decimal_places=5,blank=True, null=True)  # Field name made lowercase.
    outgoingreferralfee = models.DecimalField(max_digits=9, decimal_places=5,blank=True, null=True)  # Field name made lowercase.
    outgoingtansactionfee = models.DecimalField(max_digits=9, decimal_places=2,default=0)  # Field name made lowercase.
    ubo_customer = models.BooleanField(default=False,blank=True, null=True)
    objects = models.Manager()
    active = GetActiveManager()


    def __str__(self):
        return f'user email-{self.user.email}'

class Useraccounts(models.Model):
    STATUS = (
    ("Not Verified", "Not Verified"),
    ("Deactivated by UBO", "Deactivated by UBO"),
    ("Verified", "Verified"),
    ("Rejected", "Rejected"),
    ("Suspended", "Suspended"),
    )
    RISK_STATUS =(
        ("Low","Low"),
        ("Medium Low","Medium Low"),
        ("Medium High","Medium High"),
        ("High ","High "),
    )
    slug = models.SlugField(unique=True)
    customer = models.ForeignKey(Customers, related_name='useracc_customer',
                                 on_delete=models.CASCADE)  # Field name made lowercase.
    firstname = models.CharField(max_length=250)  # Field name made lowercase.
    middlename = models.CharField(max_length=250, blank=True, null=True)  # Field name made lowercase.
    lastname = models.CharField(max_length=250)  # Field name made lowercase.
    fullname = models.CharField(max_length=1000, blank=True, null=True)
    dateofbirth = models.DateField(blank=True, null=True)  # Field name made lowercase.
    phonenumber = models.CharField(max_length=50, blank=True, null=True)  # Field name made lowercase.
    countrycode = models.CharField(max_length=50, blank=True, null=True)  # Field name made lowercase.
    emailverified = models.BooleanField(default=False)  # Field name made lowercase.
    phoneverified = models.BooleanField(default=False)  # Field name made lowercase.
    idverified = models.BooleanField(default=False)  # Field name made lowercase.
    addressverified = models.BooleanField(default=False)  # Field name made lowercase.
    createdby = models.ForeignKey(Customers, related_name='useracc_created_by', on_delete=models.SET_NULL, blank=True,
                                  null=True)  # Field name made lowercase.
    createdon = models.DateTimeField(auto_now_add=True)  # Field name made lowercase.
    modifiedby = models.ForeignKey(Customers, related_name='useracc_modified_by', on_delete=models.SET_NULL, blank=True,
                                   null=True)  # Field name made lowercase.
    modifiedon = models.DateTimeField(auto_now=True)  # Field name made lowercase.
    isdeleted = models.BooleanField(default=False)  # Field name made lowercase.
    street_address = models.CharField(max_length=1000, blank=True, null=True)  # Field name made lowercase.
    city = models.CharField(max_length=200, blank=True, null=True)  # Field name made lowercase.
    region = models.CharField(max_length=100, blank=True, null=True)  # Field name made lowercase.
    country = models.ForeignKey('Countries',related_name='usr_accnt_country',on_delete=models.SET_NULL, blank=True,null=True)  # Field name made lowercase.
    nationality = models.ForeignKey('Countries',related_name='usr_accnt_nationality',on_delete=models.SET_NULL, blank=True,null=True)  # Field name made lowercase.
    zipcode = models.CharField(max_length=100, blank=True, null=True)  # Field name made lowercase.
    otptype = models.SmallIntegerField(blank=True, null=True)  # Field name made lowercase.
    twofactorauth = models.BooleanField(default=False)  # Field name made lowercase.
    islocked = models.BooleanField(default=False)  # Field name made lowercase.
    logintrycount = models.SmallIntegerField(blank=True, null=True)  # Field name made lowercase.
    # activestatus = models.BooleanField(blank=True, null=True)  # Field name made lowercase.
    activestatus = models.CharField(max_length=35, choices=STATUS, default='Not Verified')
    risk_management = models.CharField(max_length=35, choices=RISK_STATUS, null=True,blank=True)
    admincomments = models.ManyToManyField('Comments',related_name='usr_admincomments', blank=True, null=True)  # Field name made lowercase.
    apistatus = models.IntegerField(blank=True, null=True)  # Field name made lowercase.
    referencecount = models.IntegerField(blank=True, null=True, default=0)  # Field name made lowercase.
    referencecode = models.CharField(max_length=20, blank=True, null=True)  # Field name made lowercase.
    ismaster_account = models.BooleanField(default=False)
    added_by  = models.ForeignKey(Customers, related_name='useracc_added_by', on_delete=models.SET_NULL, blank=True,
                                   null=True)
    ultimate_ben_user = models.BooleanField(default=False,blank=True, null=True)
    account_tran_status = models.BooleanField(default=False,blank=True, null=True)
    referred_by = models.ForeignKey('self',related_name='user_referred_by',on_delete=models.SET_NULL,null=True,blank=True)
    show_referee = models.BooleanField(default=False)
    is_prevuser = models.BooleanField(default=False)
    allow_wallet_withdrawal = models.BooleanField(default=False)
    test_account = models.BooleanField(default=False)
    upi_payment = models.BooleanField(default=False)
    objects = models.Manager()
    active = GetActiveManager()

    # isadmin = models.BooleanField(default=False)
    # approval_level = models.CharField(max_length=35, choices=APPROVAL_LEVEL, blank=True, null=True)
    # admin_level = models.CharField(max_length=35, choices=ADMIN_LEVEL, blank=True, null=True)

    def __str__(self):
        return f'customer-{self.customer.user.email}'

    def save(self, *args, **kwargs):
        import random, string
        slug = ''.join(
            random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
        if not self.slug:
            self.slug = slug
        super(Useraccounts, self).save(*args, **kwargs)

# class Comments(models.Model):
#     STATUS = (
#     ("Not Verified", "Not Verified"),
#     ("Deactivated by UBO", "Deactivated by UBO"),
#     ("Verified", "Verified"),
#     ("Rejected", "Rejected"),
#     ("Suspended", "Suspended"),
#     )
#     content = models.CharField(max_length=4000, blank=True, null=True)
#     createdby = models.ForeignKey('AdminAccount', related_name='comments_createdby', on_delete=models.SET_NULL, blank=True,null=True)
#     comment_to = models.ForeignKey(Useraccounts, related_name='comments_commentto', on_delete=models.CASCADE, blank=True,null=True)
#     status = models.CharField(max_length=35, choices=STATUS, blank=True, null=True)
#     createdon = models.DateTimeField(auto_now_add=True)
#     isdeleted = models.BooleanField(default=False)

class Currencies(models.Model):
    code = models.CharField(max_length=10)  # Field name made lowercase.
    name = models.CharField(max_length=200)  # Field name made lowercase.
    symbol = models.CharField(max_length=50, blank=True, null=True)  # Field name made lowercase.
    createdby = models.ForeignKey(User, related_name='crncy_created_by', on_delete=models.SET_NULL, blank=True,
                                  null=True)  # Field name made lowercase.
    createdon = models.DateTimeField(auto_now_add=True)  # Field name made lowercase.
    modifiedby = models.ForeignKey(User, related_name='crncy_modified_by', on_delete=models.SET_NULL, blank=True,
                                   null=True)  # Field name made lowercase.
    modifiedon = models.DateTimeField(auto_now=True)  # Field name made lowercase.
    isdeleted = models.BooleanField(default=False)  # Field name made lowercase.
    flag = models.FileField(upload_to='uploads/currency/flags/', blank=True, null=True) # Field name made lowercase.
    marginpercent = models.CharField(max_length=20)  # Field name made lowercase.
    objects = models.Manager()
    active = GetActiveManager()


    def __str__(self):
        return self.code

class Countries(models.Model):
    name = models.CharField(max_length=200)
    shortform = models.CharField(max_length=10, blank=True, null=True)
    phonecode = models.CharField(max_length=17, blank=True, null=True)
    flag = models.FileField(upload_to='uploads/country/flags/', blank=True, null=True)
    isdeleted = models.BooleanField(default=False)
    objects = models.Manager()
    active = GetActiveManager()

    def __str__(self):
        return f'{self.name}-{self.shortform}--{self.phonecode}'


class Accounts(models.Model):
    slug = models.SlugField(unique=True)
    user_account = models.ForeignKey(Useraccounts, related_name='accnt_usr_accnt',
                                     on_delete=models.CASCADE)  # Field name made lowercase.
    accountno = models.CharField(max_length=50, blank=True, null=True)  # Field name made lowercase.
    currency = models.ForeignKey(Currencies, related_name='accnt_crncy', on_delete=models.SET_NULL, blank=True,
                                 null=True)  # Field name made lowercase.
    accounttype = models.SmallIntegerField()  # Field name made lowercase.
    balance = models.DecimalField(max_digits=18, decimal_places=4,default=0)  # Field name made lowercase.
    isprimary = models.SmallIntegerField(default=3,blank=True,
                                  null=True)  # Field name made lowercase.
    createdby = models.ForeignKey(User, related_name='accnt_created_by', on_delete=models.SET_NULL, blank=True,
                                  null=True)  # Field name made lowercase.
    createdon = models.DateTimeField(auto_now_add=True)  # Field name made lowercase.
    modifiedby = models.ForeignKey(User, related_name='accnt_modified_by', on_delete=models.SET_NULL, blank=True,
                                   null=True)  # Field name made lowercase.
    modifiedon = models.DateTimeField(auto_now=True)  # Field name made lowercase.
    isdeleted = models.BooleanField(default=False)  # Field name made lowercase.
    objects = models.Manager()
    active = GetActiveManager()

    def save(self, *args, **kwargs):
        import random, string
        slug = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
        if not self.slug:
            self.slug = slug
        self.accounttype = 1  # temporary
        super(Accounts, self).save(*args, **kwargs)

    def __str__(self):
        return "{} - {} >>> {}".format(self.accountno,self.currency.code if self.currency else " --- ",self.createdby.email if self.createdby else "")


class Transactiontypes(models.Model):
    name = models.CharField(max_length=200)  # Field name made lowercase.

    def __str__(self):
        return self.name


class Transactions(models.Model):
    AMOUNT_TYPE = (
    ("Net Amount", "Net Amount"),
    ("Conversion Fee", "Conversion Fee"),
    ("Wire Transfer Fee", "Wire Transfer Fee"),
    ("Wallet Withdrawal Fee", "Wallet Withdrawal Fee"),
    ("Admin Fee", "Admin Fee"),
    )
    transactionno = models.CharField(max_length=20)  # Field name made lowercase.
    fromaccount = models.ForeignKey(Accounts, related_name='tr_frm_accnt', on_delete=models.SET_NULL, blank=True,
                                    null=True)  # Field name made lowercase.
    toaccount = models.ForeignKey(Accounts, related_name='tr_to_accnt', on_delete=models.SET_NULL, blank=True,
                                  null=True)  # Field name made lowercase.
    fromamount = models.DecimalField(max_digits=18, decimal_places=4)  # Field name made lowercase.
    toamount = models.DecimalField(max_digits=18, decimal_places=4,blank=True, null=True)  # Field name made lowercase.
    initiatedby = models.ForeignKey(User, related_name='tr_initiated', on_delete=models.SET_NULL, blank=True,
                                    null=True)  # Field name made lowercase.
    transactiontype = models.ForeignKey(Transactiontypes, related_name='tr_type', on_delete=models.SET_NULL, blank=True,
                                        null=True)  # Field name made lowercase.
    createdby = models.ForeignKey(User, related_name='tr_created_by', on_delete=models.SET_NULL, blank=True,
                                  null=True)  # Field name made lowercase.
    createdon = models.DateTimeField(auto_now_add=True)  # Field name made lowercase.
    modifiedby = models.ForeignKey(User, related_name='tr_modified_by', on_delete=models.SET_NULL, blank=True,
                                   null=True)  # Field name made lowercase.
    modifiedon = models.DateTimeField(auto_now=True)  # Field name made lowercase.
    isdeleted = models.BooleanField(default=False)  # Field name made lowercase.
    note = models.CharField(max_length=1000, blank=True, null=True)  # Field name made lowercase.
    recipientname = models.CharField(max_length=50, blank=True, null=True)  # Field name made lowercase.
    # parentid = models.BigIntegerField(db_column='ParentId', blank=True, null=True)  # Field name made lowercase.
    parenttransaction = models.ForeignKey('self', related_name='parent_transaction', on_delete=models.CASCADE, blank=True, null=True)
    fromaccountbalance = models.DecimalField(max_digits=18, decimal_places=4, blank=True,
                                             null=True)  # Field name made lowercase.
    toaccountbalance = models.DecimalField(max_digits=18, decimal_places=4, blank=True,
                                           null=True)  # Field name made lowercase.
    amount_type = models.CharField(max_length=35, choices=AMOUNT_TYPE, blank=True, null=True)
    affiliate_fee_percentage = models.DecimalField(max_digits=9, decimal_places=2,default=0)
    conversionrate = models.DecimalField(max_digits=15, decimal_places=5, null=True)
    objects = models.Manager()
    active = GetActiveManager()


    def __str__(self):
        return f'transactionno-{self.transactionno} - {self.transactiontype.name if self.transactiontype else ""}'


class Activationlinks(models.Model):
    link = models.CharField(max_length=2000)  # Field name made lowercase.
    validtill = models.DateField(blank=True, null=True)
    # transactiontype = models.ForeignKey(Transactiontypes, related_name='ac_link_tr_type', on_delete=models.SET_NULL,
    #                                     blank=True, null=True)  # Field name made lowercase.
    # transaction = models.ForeignKey(Transactions, related_name='ac_link_tr', on_delete=models.SET_NULL, blank=True,
                                    # null=True)  # Field name made lowercase.
    transactiontype = models.CharField(max_length=100, blank=True, null=True) 
    validated = models.BooleanField(default=False)  # Field name made lowercase.
    createdby = models.ForeignKey(User, related_name='ac_link_created_by', on_delete=models.SET_NULL, blank=True,
                                  null=True)  # Field name made lowercase.
    createdon = models.DateTimeField(auto_now_add=True)  # Field name made lowercase.
    modifiedby = models.ForeignKey(User, related_name='ac_link_modified_by', on_delete=models.SET_NULL, blank=True,
                                   null=True)  # Field name made lowercase.
    modifiedon = models.DateTimeField(auto_now=True)  # Field name made lowercase.
    isdeleted = models.BooleanField(default=False)  # Field name made lowercase.
    activationcode = models.CharField(max_length=50, blank=True, null=True)  # Field name made lowercase.
    objects = models.Manager()
    active = GetActiveManager()


    def __str__(self):
        return self.activationcode

class Activitylog(models.Model):
    activity = models.CharField(max_length=500, blank=True, null=True) 
    user = models.ForeignKey(User,related_name='acvty_log_user', on_delete=models.CASCADE) 
    activitytime = models.DateTimeField(auto_now_add=True)


class Admins(models.Model):
    name = models.CharField(max_length=30, blank=True, null=True)
    email = models.CharField(max_length=100, blank=True, null=True)
    phoneno = models.CharField(max_length=20, blank=True, null=True)



class Apiaccesskeygenerate(models.Model):
    createddate = models.DateTimeField(blank=True, null=True)
    user = models.ForeignKey(User,related_name='apiaccess_keygen_user', on_delete=models.SET_NULL, blank=True, null=True)
    apiacesscount = models.IntegerField(blank=True, null=True)
    expiretime = models.DateTimeField(blank=True, null=True)
    apikey = models.CharField(max_length=900)



class Bankdetail(models.Model):
    slug = models.SlugField(unique=True)
    currency = models.ForeignKey(Currencies,related_name='bankdtl_crncy', on_delete=models.SET_NULL, blank=True, null=True)
    bankname = models.CharField(max_length=200)
    acnumber = models.CharField(max_length=50)
    address = models.CharField(max_length=500)
    reference = models.CharField(max_length=200, blank=True, null=True)
    swiftcode = models.CharField(max_length=40, blank=True, null=True)
    beneficiaryname = models.CharField(max_length=60, blank=True, null=True)
    beneficiaryaddress = models.CharField(max_length=4000, blank=True, null=True)
    city = models.CharField(max_length=400, blank=True, null=True)
    country = models.ForeignKey(Countries, related_name='bankdtl_cntry', on_delete=models.SET_NULL, blank=True, null=True)
    isdeleted = models.BooleanField(default=False)
    objects = models.Manager()
    active = GetActiveManager()


    def __str__(self):
        return self.bankname


    def save(self, *args, **kwargs):
        import random, string
        slug = ''.join(
            random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
        if not self.slug:
            self.slug = slug
        super(Bankdetail, self).save(*args, **kwargs)


class Industrytypes(models.Model):
    name = models.CharField(max_length=250)
    description = models.CharField(max_length=500, blank=True, null=True)
    createdby = models.ForeignKey(User,related_name='indstry_type_crtdby',on_delete=models.SET_NULL, blank=True, null=True)
    createdon = models.DateTimeField(auto_now_add=True)
    modifiedby = models.ForeignKey(User,related_name='indstry_type_mdfdby',on_delete=models.SET_NULL, blank=True, null=True)
    modifiedon = models.DateTimeField(auto_now=True)
    isdeleted = models.BooleanField(default=False)
    objects = models.Manager()
    active = GetActiveManager()

    def __str__(self):
        return self.name


class Businessdetails(models.Model):
    customer = models.ForeignKey(Customers, related_name='bsnssdtls_cstmr', on_delete=models.CASCADE)
    companyname = models.CharField(max_length=250)
    industrytype = models.ForeignKey(Industrytypes, related_name='bsnssdtls_indstrytype', on_delete=models.SET_NULL, blank=True, null=True)
    emailaddress = models.CharField(max_length=200, blank=True, null=True)
    dateofincorporation = models.DateTimeField(blank=True, null=True)
    phonenumber = models.CharField(max_length=50, blank=True, null=True)
    countrycode = models.CharField(max_length=50, blank=True, null=True)
    createdby = models.ForeignKey(User,related_name='bsnssdtls_createdby',on_delete=models.SET_NULL, blank=True, null=True)
    createdon = models.DateTimeField(auto_now_add=True)
    modifiedby = models.ForeignKey(User,related_name='bsnssdtls_modifiedby',on_delete=models.SET_NULL, blank=True, null=True)
    modifiedon = models.DateTimeField(auto_now=True)
    isdeleted = models.BooleanField(default=False)
    address = models.CharField(max_length=2000, blank=True, null=True)
    country = models.CharField(max_length=250, blank=True, null=True)
    zipcode = models.CharField(max_length=100, blank=True, null=True)
    url = models.URLField(max_length=300, blank=True, null=True)
    city = models.CharField(max_length=250, blank=True, null=True)
    state = models.CharField(max_length=250, blank=True, null=True)
    country_code  = models.ForeignKey(Countries,related_name='bsnssdtls_country_code',on_delete=models.SET_NULL, blank=True, null=True)
    company_country  = models.ForeignKey(Countries,related_name='bsnssdtls_company_country',on_delete=models.SET_NULL, blank=True, null=True)
    objects = models.Manager()
    active = GetActiveManager()


    def __str__(self):
        return f'companyname-{self.companyname}'


class Cablecharges(models.Model):
    parenttransaction = models.ForeignKey(Transactions, related_name='cblcharge_parenttransaction', on_delete=models.CASCADE)
    chargeamount = models.DecimalField(max_digits=18, decimal_places=4)
    currency = models.ForeignKey(Currencies, related_name='cblcharge_currency', on_delete=models.CASCADE)
    createdby = models.ForeignKey(User, related_name='cblcharge_createdby', on_delete=models.SET_NULL, blank=True, null=True)
    createdon = models.DateTimeField(auto_now_add=True)
    modifiedby = models.ForeignKey(User, related_name='cblcharge_modifiedby', on_delete=models.SET_NULL, blank=True, null=True)
    modifiedon = models.DateTimeField(auto_now=True)
    isdeleted = models.BooleanField(default=False)
    transaction = models.ForeignKey(Transactions, related_name='cblcharge_transaction', on_delete=models.CASCADE)
    objects = models.Manager()
    active = GetActiveManager()

    def __str__(self):
        return f'{self.parenttransaction.id}-{self.transaction.id}({self.chargeamount})'


class Conversioncharges(models.Model):
    parenttransaction = models.BigIntegerField()
    chargeamount = models.DecimalField(max_digits=18, decimal_places=4)
    currency = models.ForeignKey(Currencies, related_name='cncharge_currency', on_delete=models.CASCADE)
    createdby = models.ForeignKey(User, related_name='cncharge_createdby', on_delete=models.SET_NULL, blank=True, null=True)
    createdon = models.DateTimeField(auto_now_add=True)
    modifiedby = models.ForeignKey(User, related_name='cncharge_modifiedby', on_delete=models.SET_NULL, blank=True, null=True)
    modifiedon = models.DateTimeField(auto_now=True)
    isdeleted = models.SmallIntegerField(default=True)
    transaction = models.ForeignKey(Transactions, related_name='cncharge_transaction', on_delete=models.CASCADE)
    chargetype = models.SmallIntegerField()
    objects = models.Manager()
    active = GetActiveManager()


class Conversionfeecharges(models.Model):
    currencycode = models.ForeignKey(Currencies, related_name='cnfeecharge_crcode', on_delete=models.SET_NULL, blank=True, null=True)
    rate = models.DecimalField(max_digits=6, decimal_places=4)
    ratetype = models.SmallIntegerField()
    referenceid = models.IntegerField(blank=True, null=True)
    isdeleted = models.BooleanField(default=False)
    createdon = models.DateTimeField(auto_now_add=True)
    createdby = models.ForeignKey(User, related_name='cnfeecharge_createdby', on_delete=models.SET_NULL, blank=True, null=True)
    tocurrencycode = models.ForeignKey(Currencies, related_name='cnfeecharge_tocurrencycode', on_delete=models.SET_NULL, blank=True, null=True)
    minimumamount = models.BigIntegerField(blank=True, null=True)
    maximumamount = models.BigIntegerField(blank=True, null=True)
    objects = models.Manager()
    active = GetActiveManager()



class Currencyconversionmargins(models.Model):
    fromcurrency = models.ForeignKey(Currencies, related_name='crcn_margin_fromcurrency', on_delete=models.CASCADE)
    tocurrency = models.ForeignKey(Currencies, related_name='crcn_margin_tocurrency', on_delete=models.CASCADE)
    marginpercent = models.CharField(max_length=20,blank=True, null=True)
    isdeleted = models.BooleanField(default=False)
    createdon = models.DateTimeField(auto_now_add=True)
    modifiedby = models.ForeignKey(User, related_name='crcn_margin_modifiedby', on_delete=models.SET_NULL, blank=True, null=True)
    modifiedon = models.DateTimeField(auto_now=True)
    objects = models.Manager()
    active = GetActiveManager()

    def __str__(self):
        return f"{self.fromcurrency.code} to {self.tocurrency.code} - {self.marginpercent}"


class Currencyconversionrates(models.Model):
    fromcurrency = models.ForeignKey(Currencies, related_name='currency_cnrate_fromcurrency', on_delete=models.CASCADE)
    tocurrency = models.ForeignKey(Currencies, related_name='currency_cnrate_tocurrency', on_delete=models.CASCADE)
    conversionrate = models.DecimalField(max_digits=15, decimal_places=5)
    isdeleted = models.BooleanField(default=False)
    submittime = models.DateTimeField(blank=True, null=True)
    createdon = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()
    active = GetActiveManager()


class Currencyconversionratescombined(models.Model):
    fromcurrency = models.ForeignKey(Currencies, related_name='cr_ratescombined_fromcurrency', on_delete=models.CASCADE)
    tocurrency = models.ForeignKey(Currencies, related_name='cr_ratescombined_tocurrency', on_delete=models.CASCADE)
    conversionrate = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True)
    isdeleted = models.BooleanField(default=False)
    submittime = models.DateTimeField(blank=True, null=True)
    createdon = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()
    active = GetActiveManager()


    def __str__(self):
        return f'{self.fromcurrency.code}-{self.tocurrency.code}-{self.conversionrate}'



class Documenttypes(models.Model):
    name = models.CharField(max_length=250)
    description = models.CharField(max_length=500)
    createdby = models.ForeignKey(User, related_name='documenttype_createdby', on_delete=models.SET_NULL, blank=True, null=True)
    createdon = models.DateTimeField(auto_now_add=True)
    modifiedby = models.ForeignKey(User, related_name='documenttype_modifiedby', on_delete=models.SET_NULL, blank=True, null=True)
    modifiedon = models.DateTimeField(auto_now=True)
    isdeleted = models.BooleanField(default=False)
    filesrequired = models.SmallIntegerField(blank=True, null=True)
    objects = models.Manager()
    active = GetActiveManager()


    def __str__(self):
        return f'{self.name}-{self.description}'

class Documentfields(models.Model):
    documenttype = models.ForeignKey(Documenttypes, related_name='documentfield_documenttype', on_delete=models.CASCADE)
    fieldname = models.CharField(max_length=250)
    fieldtype = models.SmallIntegerField()
    createdby = models.ForeignKey(User, related_name='documentfield_createdby', on_delete=models.SET_NULL, blank=True, null=True)
    createdon = models.DateTimeField(auto_now_add=True)
    modifiedby = models.ForeignKey(User, related_name='documentfield_modifiedby', on_delete=models.SET_NULL, blank=True, null=True)
    modifiedon = models.DateTimeField(auto_now=True)
    isdeleted = models.BooleanField(default=False)
    objects = models.Manager()
    active = GetActiveManager()


    def __str__(self):
        return f'{self.documenttype.name}-{self.fieldname}-{self.fieldtype}'


class Documenttypesforverification(models.Model):
    documenttype = models.ForeignKey(Documenttypes, related_name='dct_type_for_vrfcn_documenttype', on_delete=models.CASCADE)
    verificationtype = models.SmallIntegerField()

    def __str__(self):
        return f'{self.documenttype.name}-{str(self.verificationtype)}'

class Customerdocuments(models.Model):
    customer = models.ForeignKey(Customers, related_name='customerdocument_customer', on_delete=models.CASCADE)
    # verificationtype = models.SmallIntegerField()
    verificationtype = models.ForeignKey(Documenttypesforverification, related_name='customerdocument_vtype', on_delete=models.SET_NULL, blank=True, null=True)
    documenttype = models.ForeignKey(Documenttypes, related_name='customerdocument_type', on_delete=models.CASCADE, blank=True, null=True)
    createdby = models.ForeignKey(User, related_name='customerdocument_createdby', on_delete=models.SET_NULL, blank=True, null=True)
    createdon = models.DateTimeField(auto_now_add=True)
    modifiedby = models.ForeignKey(User, related_name='customerdocument_modifiedby', on_delete=models.SET_NULL, blank=True, null=True)
    modifiedon = models.DateTimeField(auto_now=True)
    isdeleted = models.BooleanField(default=False)
    useraccount = models.ForeignKey(Useraccounts, related_name='customerdocument_useraccount', on_delete=models.SET_NULL, blank=True, null=True)
    firstapprovalstatus = models.BooleanField(default=False) 
    firstapprovalcomments = models.CharField(max_length=4000, blank=True, null=True)
    secondapprovalstatus = models.BooleanField(default=False)
    secondapprovalcomments = models.CharField(max_length=4000, blank=True, null=True)
    added_by = models.ForeignKey(Businessdetails, related_name='business_details', on_delete=models.SET_NULL, blank=True, null=True)
    objects = models.Manager()
    active = GetActiveManager()

    def __str__(self):
        return f'{self.customer.user.email}-{self.documenttype.name}'

class Customerdocumentfiles(models.Model):
    slug = models.SlugField(unique=True)
    customerdocument = models.ForeignKey(Customerdocuments, related_name='customerdocumentfile_ctmrdcmt', on_delete=models.CASCADE)
    # filelocation = models.CharField(max_length=2000)
    filelocation = models.FileField(upload_to ='address_proof',  blank=True, null=True)
    document_type = models.CharField(max_length=400, blank=True, null=True)
    def __str__(self):
        return f'{self.customerdocument.verificationtype.verificationtype}-{self.customerdocument.customer.user.email}'

    def save(self, *args, **kwargs):
        import random, string
        slug = ''.join(
            random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
        self.slug = slug
        super(Customerdocumentfiles, self).save(*args, **kwargs)

class Customerdocumentdetails(models.Model):
    customerdocument = models.ForeignKey(Customerdocuments, related_name='customerdocumentdetail_ctmrdcmt', on_delete=models.CASCADE)
    # fieldid = models.IntegerField()
    field = models.ForeignKey(Documentfields, related_name='customerdocumentdetail_filed', on_delete=models.SET_NULL, blank=True, null=True)
    value = models.CharField(max_length=500)
    createdby = models.ForeignKey(User, related_name='customerdocumentdetail_createdby', on_delete=models.SET_NULL, blank=True, null=True)
    createdon = models.DateTimeField(auto_now_add=True)
    modifiedby = models.ForeignKey(User, related_name='customerdocumentdetail_modifiedby', on_delete=models.SET_NULL, blank=True, null=True)
    modifiedon = models.DateTimeField(auto_now=True)
    isdeleted = models.BooleanField(default=False)
    objects = models.Manager()
    active = GetActiveManager()


    def __str__(self):
        return f'{self.customerdocument.customer.user.email}-{self.field.fieldname}'


# class Emaillog(models.Model):
#     toaddress = models.CharField(db_column='ToAddress', max_length=250)  # Field name made lowercase.
#     fromaddress = models.CharField(db_column='FromAddress', max_length=100)  # Field name made lowercase.
#     subject = models.CharField(db_column='Subject', max_length=1000)  # Field name made lowercase.
#     htmlcontent = models.TextField(db_column='HtmlContent')  # Field name made lowercase.
#     textcontent = models.TextField(db_column='TextContent')  # Field name made lowercase.
#     transactiontype = models.SmallIntegerField(db_column='TransactionType')  # Field name made lowercase.
#     transactionid = models.BigIntegerField(db_column='TransactionId')  # Field name made lowercase.
#     status = models.SmallIntegerField(db_column='Status')  # Field name made lowercase.
#     createdby = models.IntegerField(db_column='CreatedBy', blank=True, null=True)  # Field name made lowercase.
#     createdon = models.DateTimeField(db_column='CreatedOn')  # Field name made lowercase.
#     modifiedon = models.DateTimeField(db_column='ModifiedOn')  # Field name made lowercase.
#
#     class Meta:
#         managed = False
#
#
class Externalbeneficiaries(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)  # Field name made lowercase.
    accountnumber = models.CharField(max_length=50)  # Field name made lowercase.
    currency = models.ForeignKey(Currencies, related_name='extrnl_ben_crncy', on_delete=models.SET_NULL, blank=True,
                                 null=True)  # Field name made lowercase.
    swiftcode = models.CharField(max_length=25)  # Field name made lowercase.
    country = models.ForeignKey(Countries,related_name='ext_ben_country',on_delete=models.SET_NULL, blank=True,null=True)  # Field name made lowercase.
    city = models.CharField(max_length=100)  # Field name made lowercase.
    bankname = models.CharField(max_length=200)  # Field name made lowercase.
    createdby = models.ForeignKey(User, related_name='extrnl_ben_created_by', on_delete=models.SET_NULL, blank=True,
                                  null=True)  # Field name made lowercase.
    createdon = models.DateTimeField(auto_now_add=True)  # Field name made lowercase.
    modifiedby = models.ForeignKey(User, related_name='extrnl_ben_modified_by', on_delete=models.SET_NULL, blank=True,
                                   null=True)  # Field name made lowercase.
    modifiedon = models.DateTimeField(auto_now=True)  # Field name made lowercase.
    isdeleted = models.BooleanField(default=False)  # Field name made lowercase.
    email = models.CharField(max_length=400, blank=True, null=True)  # Field name made lowercase.
    customer = models.ForeignKey(Customers, related_name='extrnl_ben_customer',
                                 on_delete=models.CASCADE)  # Field name made lowercase.
    objects = models.Manager()
    active = GetActiveManager()


    def save(self, *args, **kwargs):
        import random, string
        slug = ''.join(
            random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
        if not self.slug:
            self.slug = slug
        super(Externalbeneficiaries, self).save(*args, **kwargs)

class Incomingtracepayment(models.Model):
    STATUS = (
    ("Open", "Open"),
    ("Processing", "Processing"),
    ("Hold", "Hold"),
    ("Closed", "Closed"),
    )
    slug = models.SlugField(unique=True)
    account = models.ForeignKey(Accounts, related_name='incoming_payment_account', on_delete=models.CASCADE)
    sendername = models.CharField(max_length=800, blank=True, null=True)
    senderbank = models.CharField(max_length=800, blank=True, null=True)
    senderaccountno = models.CharField(max_length=40, blank=True, null=True)
    amount = models.DecimalField(max_digits=18, decimal_places=4)
    bookingdate = models.DateField(blank=True, null=True)
    paymentattachment = models.FileField(upload_to ='paymentattachment', blank=True, null=True)
    currency = models.ForeignKey(Currencies, related_name='incoming_payment_currency', on_delete=models.CASCADE)
    reference = models.CharField(max_length=1600, blank=True, null=True)
    createdby = models.ForeignKey(User, related_name='incoming_payment_createdby', on_delete=models.CASCADE)
    createdon = models.DateTimeField(auto_now_add=True)
    modifiedby = models.ForeignKey(User, related_name='incoming_payment_modifiedby', on_delete=models.CASCADE, blank=True, null=True)
    modifiedon = models.DateTimeField(auto_now=True)
    isdeleted = models.BooleanField(default=False)
    status = models.CharField(max_length=50, choices=STATUS, default='Open')
    admincomments = models.ManyToManyField('Comments',related_name='inc_tr_payment_admincomments', blank=True, null=True)  # Field name made lowercase.
    customerid = models.ForeignKey(Customers, related_name='incoming_payment_customer', on_delete=models.SET_NULL, blank=True, null=True)
    isadmindeleted = models.BooleanField(default=False)
    objects = models.Manager()
    active = GetActiveManager()

    def save(self, *args, **kwargs):
        import random, string
        slug = ''.join(
            random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
        if not self.slug:
            self.slug = slug
        super(Incomingtracepayment, self).save(*args, **kwargs)


class Internalbeneficiaries(models.Model):
    slug = models.SlugField(unique=True)
    receivername = models.CharField(max_length=100)  # Field name made lowercase.
    account = models.ForeignKey(Accounts, related_name='intrnl_ben_accnt',
                                on_delete=models.CASCADE)
    createdby = models.ForeignKey(User, related_name='intrnl_ben_created_by', on_delete=models.SET_NULL, blank=True,
                                  null=True)
    createdon = models.DateTimeField(auto_now_add=True) 
    modifiedby = models.ForeignKey(User, related_name='intrnl_ben_modified_by', on_delete=models.SET_NULL, blank=True,
                                   null=True)
    modifiedon = models.DateTimeField(auto_now=True) 
    isdeleted = models.BooleanField(default=False) 
    customer = models.ForeignKey(Customers, related_name='intrnl_ben_customer',
                                 on_delete=models.CASCADE)
    objects = models.Manager()
    active = GetActiveManager()


    def save(self, *args, **kwargs):
        import random, string
        slug = ''.join(
            random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
        if not self.slug:
            self.slug = slug
        super(Internalbeneficiaries, self).save(*args, **kwargs)


class Internationaltransactions(models.Model):
    VERIFICATION_STATUSES = (
        ("Executed","Executed"),
        ("Hold","Hold"),
        ("Approved","Approved"),
        ("Pending","Pending"),
        ("Refund Requested","Refund Requested"),
        ("Refund Rejected","Refund Rejected"),
        ("Refunded","Refunded"),
    )
    slug = models.SlugField(unique=True)
    transaction = models.ForeignKey(Transactions, related_name='inltransaction_tr', on_delete=models.CASCADE)
    bankname = models.CharField(max_length=200)
    swiftcode = models.CharField(max_length=25)
    accountnumber = models.CharField(max_length=50) 
    accountholdername = models.CharField(max_length=200) 
    currency = models.ForeignKey(Currencies, related_name='inltransaction_currency',on_delete=models.CASCADE)
    createdby = models.ForeignKey(User, related_name='inltransaction_createdby', on_delete=models.SET_NULL, blank=True, null=True)
    createdon = models.DateTimeField(auto_now_add=True)
    modifiedby = models.ForeignKey(User, related_name='inltransaction_modifiedby', on_delete=models.SET_NULL, blank=True, null=True)
    modifiedon = models.DateTimeField(auto_now=True)
    isdeleted = models.BooleanField(default=False)
    city = models.CharField(max_length=200, blank=True, null=True)
    country = models.ForeignKey(Countries, related_name='inltransaction_country', on_delete=models.SET_NULL, blank=True, null=True)
    user_box_no = models.CharField(max_length=30, blank=True, null=True)
    user_street = models.CharField(max_length=100, blank=True, null=True)
    user_city = models.CharField(max_length=100, blank=True, null=True)
    user_state = models.CharField(max_length=100, blank=True, null=True)
    user_country = models.ForeignKey(Countries, related_name='inltransaction_usercountry', on_delete=models.SET_NULL, blank=True, null=True)
    user_phone = models.CharField(max_length=50, blank=True, null=True)
    invoice_doc = models.FileField(upload_to ='uploads/% Y/% m/% d/', blank=True, null=True)
    verificationstatus = models.CharField(max_length=30,choices=VERIFICATION_STATUSES,default="Pending",blank=True, null=True)
    approvallevel = models.SmallIntegerField(blank=True, null=True)
    email = models.CharField(max_length=400, blank=True, null=True)
    purpose = models.ForeignKey('Transactionpurposetype', related_name='inltransaction_purpose', on_delete=models.SET_NULL, blank=True, null=True) 
    other_purpose_note = models.CharField(max_length=50, blank=True, null=True)
    admincomments = models.ManyToManyField('Comments')
    hideforadmin = models.BooleanField(default=False)
    affiliate_fee_deducted = models.BooleanField(default=False)
    master_fee_deducted = models.BooleanField(default=False)
    objects = models.Manager()
    active = GetActiveManager()

    def save(self, *args, **kwargs):
        import random, string
        slug = ''.join(
            random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
        if not self.slug:
            self.slug = slug
        super(Internationaltransactions, self).save(*args, **kwargs)

    def __str__(self):
        return self.transaction.transactionno



class Inwardremittancetransactions(models.Model):
    slug = models.SlugField(unique=True)
    amount = models.DecimalField(max_digits=18, decimal_places=4)
    account = models.ForeignKey(Accounts,related_name='inward_remittance_acc',on_delete=models.CASCADE,null=True,blank=True)
    currency = models.ForeignKey(Currencies,related_name='inward_remittance_curency',on_delete=models.SET_NULL,null=True,blank=True)
    transactiontype = models.ForeignKey(Transactiontypes,related_name='inwared_remittance_ttype',on_delete=models.SET_NULL,null=True,blank=True)
    transaction = models.ForeignKey(Transactions, related_name='inward_remittance_transaction',
                                    on_delete=models.SET_NULL, blank=True, null=True)
    comment = models.CharField(max_length=500, blank=True, null=True)
    createdby = models.ForeignKey(User, related_name='inward_remittance_createdby', on_delete=models.SET_NULL, blank=True, null=True)
    modifiedby = models.ForeignKey(User, related_name='inward_remittance_modifiedby', on_delete=models.SET_NULL, blank=True, null=True)
    createdon = models.DateTimeField(auto_now_add=True)
    modifiedon = models.DateTimeField(auto_now=True)
    approvallevel = models.IntegerField(default=0,blank=True, null=True)
    approvestatus = models.BooleanField(default=False)
    reasonforreject = models.CharField(max_length=500, blank=True, null=True)
    isdeleted = models.BooleanField(default=False)
    objects = models.Manager()
    active = GetActiveManager()

    def save(self, *args, **kwargs):
        import random, string
        slug = ''.join(
            random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
        if not self.slug:
            self.slug = slug
        super(Inwardremittancetransactions, self).save(*args, **kwargs)

class Otps(models.Model):
    code = models.CharField(max_length=10) 
    validtill = models.DateField(blank=True, null=True) 
    transactiontype = models.CharField(max_length=100, blank=True, null=True) 
    # transaction = models.ForeignKey(Transactions, related_name='otp_transaction', on_delete=models.SET_NULL, blank=True, null=True) 
    token = models.CharField(max_length=100, blank=True, null=True)
    validated = models.BooleanField(default=False) 
    createdby = models.ForeignKey(User, related_name='otp_createdby', on_delete=models.SET_NULL, blank=True, null=True)
    createdon = models.DateTimeField(auto_now_add=True) 
    modifiedby = models.ForeignKey(User, related_name='otp_modifiedby', on_delete=models.SET_NULL, blank=True, null=True) 
    modifiedon = models.DateTimeField(auto_now=True)
    isdeleted = models.BooleanField(default=False)
    objects = models.Manager()
    active = GetActiveManager()


    def __str__(self):
        return self.code


# class Outgoingtracepayment(models.Model):
#     accountid = models.IntegerField(db_column='AccountId')  # Field name made lowercase.
#     beneficiaryname = models.CharField(db_column='BeneficiaryName', max_length=400)  # Field name made lowercase.
#     beneficiarybank = models.CharField(db_column='BeneficiaryBank', max_length=400)  # Field name made lowercase.
#     beneficiaryaccountno = models.CharField(db_column='BeneficiaryAccountNo', max_length=20)  # Field name made lowercase.
#     amount = models.DecimalField(db_column='Amount', max_digits=18, decimal_places=2)  # Field name made lowercase.
#     bookingdate = models.DateTimeField(db_column='BookingDate')  # Field name made lowercase.
#     scotrantransactionid = models.CharField(db_column='ScotranTransactionId', max_length=20)  # Field name made lowercase.
#     currency = models.IntegerField(db_column='Currency')  # Field name made lowercase.
#     reference = models.CharField(db_column='Reference', max_length=800)  # Field name made lowercase.
#     createdby = models.IntegerField(db_column='CreatedBy')  # Field name made lowercase.
#     createdon = models.DateTimeField(db_column='CreatedOn')  # Field name made lowercase.
#     modifiedby = models.IntegerField(db_column='ModifiedBy')  # Field name made lowercase.
#     modifiedon = models.DateTimeField(db_column='ModifiedOn')  # Field name made lowercase.
#     isdeleted = models.SmallIntegerField(db_column='IsDeleted')  # Field name made lowercase.
#     status = models.CharField(db_column='Status', max_length=10, blank=True, null=True)  # Field name made lowercase.
#     admincomment = models.CharField(db_column='AdminComment', max_length=400, blank=True, null=True)  # Field name made lowercase.
#
#     class Meta:
#         managed = False
#
#
class Receivemoney(models.Model):
    # bankname = models.ForeignKey(Bankdetail,related_name='receivemoney_bankname',on_delete=models.SET_NULL, blank=True, null=True) 
    # bankaddress = models.ForeignKey(Bankdetail, related_name='receivemoney_bankaddress',on_delete=models.SET_NULL, blank=True, null=True) 
    slug = models.SlugField(unique=True)
    senderaccountno = models.CharField(max_length=20, blank=True, null=True)
    sendername = models.CharField(max_length=200, blank=True, null=True) 
    swiftcode = models.CharField(max_length=20, blank=True, null=True) 
    amount = models.DecimalField(max_digits=18, decimal_places=4) 
    receiveraccount = models.ForeignKey(Accounts,related_name='receivemoney_receiveraccount',on_delete=models.SET_NULL, blank=True, null=True) 
    # transaction = models.ForeignKey(Transactions,related_name='receivemoney_transaction',on_delete=models.SET_NULL, blank=True, null=True) 
    createdby = models.ForeignKey(User, related_name='receivemoney_createdby', on_delete=models.SET_NULL, blank=True, null=True) 
    createdon = models.DateTimeField(auto_now_add=True)  
    modifiedby = models.ForeignKey(User, related_name='receivemoney_modifiedby', on_delete=models.SET_NULL, blank=True, null=True) 
    modifiedon = models.DateTimeField(auto_now=True) 
    isdeleted = models.BooleanField(default=False)
    reference = models.CharField(max_length=500, blank=True, null=True) 
    verificationstatus = models.BooleanField(default=False) 
    approvallevel = models.SmallIntegerField(blank=True, null=True) 
    senderbankname = models.CharField(max_length=400, blank=True, null=True) 
    sendercountry = models.CharField(max_length=200, blank=True, null=True)
    payment_proof = models.FileField(upload_to ='payment_proof_uploads', blank=True, null=True)
    bank = models.ForeignKey(Bankdetail, related_name='receivemoney_bank', on_delete=models.SET_NULL, blank=True, null=True)
    objects = models.Manager()
    active = GetActiveManager()

    def save(self, *args, **kwargs):
        import random, string
        slug = ''.join(
            random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
        if not self.slug:
            self.slug = slug
        super(Receivemoney, self).save(*args, **kwargs)


class Referralfeetransactiondetails(models.Model):
    STATUS = (
    ("Pending", "Pending"),
    ("Completed", "Completed"),
    ("Hold", "Hold"),
    )
    referrer = models.ForeignKey(Useraccounts, related_name='referralfeetrdetails_referrer', on_delete=models.CASCADE)
    amount = models.CharField(max_length=20)
    currency = models.ForeignKey(Currencies, related_name='referralfeetrdetails_cr', on_delete=models.CASCADE)
    parenttransaction = models.ForeignKey(Transactions, related_name='referralfeetrdetails_parenttr', on_delete=models.CASCADE)
    transactionstatus = models.CharField(max_length=35, choices=STATUS, default='Pending')
    transactionwillcreateon = models.DateTimeField(auto_now_add=True)
    createdby = models.ForeignKey(Customers, related_name='referralfeetrdetails_createdby', on_delete=models.CASCADE)
    createdon = models.DateTimeField(auto_now_add=True)
    modifiedon = models.DateTimeField(auto_now=True)
    isdeleted = models.BooleanField(default=False)



class Referrerdetails(models.Model):
    referrer = models.ForeignKey(Useraccounts, related_name='referrerdetails_referrer', on_delete=models.CASCADE)
    referee = models.ForeignKey(Useraccounts, related_name='referrerdetails_referee', on_delete=models.CASCADE)
    isdeleted = models.BooleanField(default=False)


# class Referrerfeetransactiondetails(models.Model):
#     referrerid = models.IntegerField(db_column='ReferrerId') 
#     amount = models.CharField(db_column='Amount', max_length=20) 
#     fromdate = models.DateTimeField(db_column='FromDate')  
#     todate = models.DateTimeField(db_column='ToDate') 
#     createdon = models.DateTimeField(db_column='CreatedOn', blank=True, null=True) 



# class Smslog(models.Model):
#     tophone = models.CharField(db_column='ToPhone', max_length=20)
#     fromphone = models.CharField(db_column='FromPhone', max_length=20) 
#     content = models.CharField(db_column='Content', max_length=500)  
#     transactiontype = models.SmallIntegerField(db_column='TransactionType') 
#     transactionid = models.BigIntegerField(db_column='TransactionId') 
#     status = models.SmallIntegerField(db_column='Status')  
#     createdby = models.IntegerField(db_column='CreatedBy', blank=True, null=True) 
#     createdon = models.DateTimeField(db_column='CreatedOn') 
#     modifiedon = models.DateTimeField(db_column='ModifiedOn')  


class Supportqueries(models.Model):
    description = models.CharField(max_length=2000) 
    createdby = models.ForeignKey(User,related_name='sp_qs_createdby', on_delete=models.SET_NULL, blank=True, null=True) 
    createdon = models.DateTimeField(auto_now_add=True) 
    modifiedby = models.ForeignKey(User,related_name='sp_qs_modifiedby', on_delete=models.SET_NULL, blank=True, null=True) 
    modifiedon = models.DateTimeField(auto_now=True)
    isdeleted = models.BooleanField(default=False)
    subject = models.CharField(max_length=2000, blank=True, null=True)
    objects = models.Manager()
    active = GetActiveManager()


class Transactionauthoritytypes(models.Model):
    name = models.CharField(max_length=250)
    description = models.CharField(max_length=500)
    createdby = models.ForeignKey(User,related_name='tr_authtype_crtdby',on_delete=models.SET_NULL, blank=True, null=True) 
    createdon = models.DateTimeField(auto_now_add=True)
    modifiedby = models.ForeignKey(User,related_name='tr_authtype_mdfdby',on_delete=models.SET_NULL, blank=True, null=True) 
    modifiedon = models.DateTimeField(auto_now=True)
    isdeleted = models.BooleanField(default=False)
    objects = models.Manager()
    active = GetActiveManager()

class Businesstransactionauthorities(models.Model):
    useraccount = models.ForeignKey(Useraccounts,related_name='bsnsstrauth_usracc',on_delete=models.CASCADE)
    # transactionauthoritytype = models.SmallIntegerField(db_column='TransactionAuthorityType')
    transactionauthoritytype = models.ForeignKey(Transactionauthoritytypes,related_name='transaction_authority_type',on_delete=models.CASCADE)
    accesstype = models.SmallIntegerField(db_column='AccessType', blank=True, null=True)
    createdby = models.ForeignKey(User,related_name='business_trans_crtdby',on_delete=models.SET_NULL, blank=True, null=True)
    createdon = models.DateTimeField(db_column='CreatedOn', blank=True, null=True)
    modifiedby = models.IntegerField(db_column='ModifiedBy', blank=True, null=True)
    modifiedon = models.DateTimeField(db_column='ModifiedOn', blank=True, null=True)
    isdeleted = models.BooleanField(db_column='IsDeleted', blank=True, null=True)
    isowner = models.BooleanField(db_column='IsOwner', blank=True, null=True)
    userauthorised = models.BooleanField(db_column='UserAuthorised', blank=True, null=True)
    
class Transactionpurposetype(models.Model):
    transactionpurpose = models.CharField(max_length=400)
    isdeleted = models.BooleanField(default=False)
    objects = models.Manager()
    active = GetActiveManager()

    def __str__(self):
        return self.transactionpurpose



# class Transactionsupportqueries(models.Model):
#     comment = models.CharField(db_column='Comment', max_length=100)
#     transactiontype = models.IntegerField(db_column='Transactiontype')
#     transactionid = models.BigIntegerField(db_column='TransactionId')
#     createdby = models.IntegerField(db_column='CreatedBy')
#     customerid = models.IntegerField(db_column='CustomerId')
#     createdon = models.DateTimeField(db_column='CreatedOn')
#     modifiedby = models.IntegerField(db_column='ModifiedBy')
#     modifiedon = models.DateTimeField(db_column='ModifiedOn')
#     isdeleted = models.IntegerField(db_column='IsDeleted')



# class Useraccountsmpinregistration(models.Model):
#     userid = models.IntegerField(db_column='Userid')  
#     mpin = models.CharField(db_column='Mpin', max_length=200)  
#     deviceid = models.CharField(db_column='DeviceId', max_length=100) 
#     createdby = models.IntegerField(db_column='CreatedBy') 
#     createdon = models.DateTimeField(db_column='CreatedOn')  
#     modifiedby = models.IntegerField(db_column='Modifiedby') 
#     modifiedon = models.DateTimeField(db_column='ModifiedOn')  
#     isdeleted = models.BooleanField(db_column='IsDeleted') 


# class Biometriclogin(models.Model):
#     userid = models.IntegerField(db_column='userId', blank=True, null=True)  
#     deviceid = models.CharField(db_column='deviceId', max_length=255, blank=True, null=True) 
#     status = models.IntegerField(blank=True, null=True)
#     createdon = models.DateTimeField(db_column='CreatedOn', blank=True, null=True) 
#     isdeleted = models.IntegerField(db_column='IsDeleted', blank=True, null=True) 


# class Sysdiagrams(models.Model):
#     name = models.CharField(max_length=128)
#     principal_id = models.IntegerField()
#     diagram_id = models.AutoField(primary_key=True)
#     version = models.IntegerField(blank=True, null=True)
#     definition = models.BinaryField(blank=True, null=True)

class Userapikey(models.Model):
    token = models.TextField()
    user = models.ForeignKey(User, related_name='usrapikey_usr',on_delete=models.SET_NULL,blank=True, null=True)
    expirestime = models.IntegerField(blank=True, null=True)
    createdon = models.DateTimeField(auto_now_add=True)
    
class InvoiceDocument(models.Model):
    invoice_doc = models.FileField(upload_to ='invoice_uploads', blank=True, null=True)
    transaction = models.ForeignKey(Transactions, related_name='invoice_trancation', on_delete=models.CASCADE, blank=True, null=True)

class AdminAccount(models.Model):
    APPROVAL_LEVEL = (
    ("Inputter", "Inputter"),
    ("Approver", "Approver"),
    ("Inputter / Approver", "Inputter / Approver"),
    )
    ADMIN_LEVEL = (
    ("Admin", "Admin"),
    ("Super Admin", "Super Admin"),
    ("Sub Admin", "Sub Admin"),
    )
    slug = models.SlugField(unique=True)
    firstname = models.CharField(max_length=250)
    middlename = models.CharField(max_length=250, blank=True, null=True)
    lastname = models.CharField(max_length=250, blank=True, null=True)
    email = models.CharField(max_length=100)
    phonenumber = models.CharField(max_length=50, blank=True, null=True)
    dateofbirth = models.DateField(blank=True, null=True)
    createdby = models.OneToOneField(User, related_name='adminacc_created_by', on_delete=models.CASCADE)
    createdon = models.DateTimeField(auto_now_add=True)
    modifiedby = models.ForeignKey(User, related_name='adminacc_modified_by', on_delete=models.CASCADE, blank=True,null=True)
    modifiedon = models.DateTimeField(auto_now=True)
    isdeleted = models.BooleanField(default=False)
    status = models.BooleanField(default=True)
    approval_level = models.CharField(max_length=35, choices=APPROVAL_LEVEL, blank=True, null=True)
    admin_level = models.CharField(max_length=35, choices=ADMIN_LEVEL, blank=True, null=True)
    test_account = models.BooleanField(default=False)
    objects = models.Manager()
    active = GetActiveManager()

    def __str__(self):
        return self.firstname

    def save(self, *args, **kwargs):
        import random, string
        slug = ''.join(
            random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
        if not self.slug:
            self.slug = slug
        super(AdminAccount, self).save(*args, **kwargs)


class Comments(models.Model):
    content = models.CharField(max_length=4000, blank=True, null=True)
    createdby = models.ForeignKey('AdminAccount', related_name='comments_createdby', on_delete=models.SET_NULL, blank=True,null=True)
    status = models.CharField(max_length=50, blank=True, null=True)
    createdon = models.DateTimeField(auto_now_add=True)
    isdeleted = models.BooleanField(default=False)


    class Meta:
        ordering = ('-id', )

    def __str__(self):
        return self.content[0:30]


class RefundRequests(models.Model):
    amount = models.DecimalField(max_digits=18, decimal_places=4)
    requestedby = models.ForeignKey(AdminAccount, related_name='refund_requestedby', on_delete=models.SET_NULL, blank=True,null=True)
    isapproved = models.BooleanField(default=False)
    approvedby = models.ForeignKey(AdminAccount, related_name='refund_approvedby', on_delete=models.SET_NULL, blank=True,null=True)
    comment = models.CharField(max_length=4000, blank=True, null=True)
    wire_transaction = models.ForeignKey(Internationaltransactions,related_name='refund_transaction', on_delete=models.CASCADE)
    isdeleted = models.BooleanField(default=False)
    objects = models.Manager()
    active = GetActiveManager()

class CurrencyConversionAPI(models.Model):
    key = models.CharField(max_length=200)
    used = models.BooleanField(default=False)

class WalletWithdrawalTransactions(models.Model):
    VERIFICATION_STATUSES = (
        ("Executed","Executed"),
        ("Approved", "Approved"),
        ("Hold","Hold"),
        ("Pending","Pending"),
        ("Refund Requested","Refund Requested"),
        ("Refund Rejected","Refund Rejected"),
        ("Refunded","Refunded"),
    )
    slug = models.SlugField(unique=True)
    transaction = models.ForeignKey(Transactions, related_name='walletwithdrawal_tr', on_delete=models.CASCADE)
    wallet_name = models.CharField(max_length=200)
    accountholdername = models.CharField(max_length=200) #ben name
    currency = models.ForeignKey(Currencies, related_name='walletwithdrawal_currency',on_delete=models.CASCADE)
    createdby = models.ForeignKey(User, related_name='walletwithdrawal_createdby', on_delete=models.SET_NULL, blank=True, null=True)
    createdon = models.DateTimeField(auto_now_add=True)
    modifiedby = models.ForeignKey(User, related_name='walletwithdrawal_modifiedby', on_delete=models.SET_NULL, blank=True, null=True)
    modifiedon = models.DateTimeField(auto_now=True)
    isdeleted = models.BooleanField(default=False)
    verificationstatus = models.CharField(max_length=30,choices=VERIFICATION_STATUSES,default="Pending",blank=True, null=True)
    approvallevel = models.SmallIntegerField(blank=True, null=True)
    admincomments = models.ManyToManyField('Comments')
    hideforadmin = models.BooleanField(default=False)
    affiliate_fee_deducted = models.BooleanField(default=False)
    master_fee_deducted = models.BooleanField(default=False)
    objects = models.Manager()
    active = GetActiveManager()

    def save(self, *args, **kwargs):
        import random, string
        slug = ''.join(
            random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
        if not self.slug:
            self.slug = slug
        super(WalletWithdrawalTransactions, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.transaction.transactionno)
class Cryptobeneficiaries(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=200)
    wallet_name = models.CharField(max_length=200)
    currency = models.ForeignKey(Currencies, related_name='crypto_ben_crncy', on_delete=models.SET_NULL, blank=True, null=True)
    createdby = models.ForeignKey(User, related_name='crypto_ben_created_by', on_delete=models.SET_NULL, blank=True, null=True)
    createdon = models.DateTimeField(auto_now_add=True)
    modifiedby = models.ForeignKey(User, related_name='crypto_ben_modified_by', on_delete=models.SET_NULL, blank=True, null=True)
    modifiedon = models.DateTimeField(auto_now=True)
    isdeleted = models.BooleanField(default=False)
    customer = models.ForeignKey(Customers, related_name='crypto_ben_customer', on_delete=models.CASCADE)
    objects = models.Manager()
    active = GetActiveManager()

    def save(self, *args, **kwargs):
        import random, string
        slug = ''.join(
            random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
        if not self.slug:
            self.slug = slug
        super(Cryptobeneficiaries, self).save(*args, **kwargs)
        
class WalletWithdrawalRefundRequests(models.Model):
    amount = models.DecimalField(max_digits=18, decimal_places=4)
    requestedby = models.ForeignKey(AdminAccount, related_name='wallet_tr_refund_requestedby', on_delete=models.SET_NULL, blank=True,null=True)
    isapproved = models.BooleanField(default=False)
    approvedby = models.ForeignKey(AdminAccount, related_name='wallet_tr_refund_approvedby', on_delete=models.SET_NULL, blank=True,null=True)
    comment = models.CharField(max_length=4000, blank=True, null=True)
    wallet_withdrawal_transaction = models.ForeignKey(WalletWithdrawalTransactions,related_name='wallet_tr_refund_transaction', on_delete=models.CASCADE)
    isdeleted = models.BooleanField(default=False)
    objects = models.Manager()
    active = GetActiveManager()
    
    
class DomesticTransaction(models.Model):
    VERIFICATION_STATUSES = (
        ("Executed","Executed"),
        ("Hold","Hold"),
        ("Approved","Approved"),
        ("Pending","Pending"),
        ("Refund Requested","Refund Requested"),
        ("Refund Rejected","Refund Rejected"),
        ("Refunded","Refunded"),
    )
    slug = models.SlugField(unique=True)
    transaction = models.ForeignKey(Transactions, related_name='domtransaction_tr', on_delete=models.CASCADE)
    bankname = models.CharField(max_length=200)
    routing_number = models.CharField(max_length=50)
    accountnumber = models.CharField(max_length=50)
    accountholdername = models.CharField(max_length=200)
    currency = models.ForeignKey(Currencies, related_name='domtransaction_currency', on_delete=models.CASCADE)
    createdby = models.ForeignKey(User, related_name='domtransaction_createdby', on_delete=models.SET_NULL, blank=True,
                                  null=True)
    createdon = models.DateTimeField(auto_now_add=True)
    modifiedby = models.ForeignKey(User, related_name='domtransaction_modifiedby', on_delete=models.SET_NULL, blank=True, null=True)
    modifiedon = models.DateTimeField(auto_now=True)
    isdeleted = models.BooleanField(default=False)
    city = models.CharField(max_length=200, blank=True, null=True)
    country = models.ForeignKey(Countries, related_name='domtransaction_country', on_delete=models.SET_NULL, blank=True, null=True)
    user_box_no = models.CharField(max_length=30, blank=True, null=True)
    user_street = models.CharField(max_length=100, blank=True, null=True)
    user_city = models.CharField(max_length=100, blank=True, null=True)
    user_state = models.CharField(max_length=100, blank=True, null=True)
    user_country = models.ForeignKey(Countries, related_name='domtransaction_usercountry', on_delete=models.SET_NULL, blank=True, null=True)
    user_phone = models.CharField(max_length=50, blank=True, null=True)
    invoice_doc = models.FileField(upload_to ='uploads/% Y/% m/% d/', blank=True, null=True)
    verificationstatus = models.CharField(max_length=30,choices=VERIFICATION_STATUSES,default="Pending",blank=True, null=True)
    approvallevel = models.SmallIntegerField(blank=True, null=True)
    email = models.CharField(max_length=400, blank=True, null=True)
    purpose = models.ForeignKey('Transactionpurposetype', related_name='domtransaction_purpose', on_delete=models.SET_NULL, blank=True, null=True)
    note = models.CharField(max_length=1000, blank=True, null=True)
    other_purpose_note = models.CharField(max_length=50, blank=True, null=True)
    admincomments = models.ManyToManyField('Comments')
    hideforadmin = models.BooleanField(default=False)
    affiliate_fee_deducted = models.BooleanField(default=False)
    master_fee_deducted = models.BooleanField(default=False)
    objects = models.Manager()
    active = GetActiveManager()

    def save(self, *args, **kwargs):
        import random, string
        slug = ''.join(
            random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16))
        if not self.slug:
            self.slug = slug
        super(DomesticTransaction, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.transaction.transactionno)
    
    
class DomesticTransactionRefundRequests(models.Model):
    amount = models.DecimalField(max_digits=18, decimal_places=4)
    requestedby = models.ForeignKey(AdminAccount, related_name='domestic_transaction_refund_requestedby', on_delete=models.SET_NULL, blank=True,null=True)
    isapproved = models.BooleanField(default=False)
    approvedby = models.ForeignKey(AdminAccount, related_name='domestic_transaction_refund_approvedby', on_delete=models.SET_NULL, blank=True,null=True)
    comment = models.CharField(max_length=4000, blank=True, null=True)
    domestic_transaction = models.ForeignKey("DomesticTransaction",related_name='refund_transaction', on_delete=models.CASCADE)
    isdeleted = models.BooleanField(default=False)
    objects = models.Manager()
    active = GetActiveManager()
