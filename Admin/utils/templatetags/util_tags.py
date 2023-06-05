import datetime
from decimal import Decimal

from django import template
from django.conf import settings
from django.contrib.auth.models import User
# from django.template.defaultfilters import linesbr
from django.db.models import Sum

from utils.models import Accounts, Activitylog, Businessdetails, DomesticTransaction, Useraccounts, Customerdocumentdetails, Customerdocumentfiles, \
    Internationaltransactions, Cablecharges, InvoiceDocument, Transactions
import logging
logger = logging.getLogger('lessons')

register = template.Library()


@register.simple_tag
def get_last_login(user):
    try:
        if Activitylog.objects.filter(user=user,activity='login'):
            try:
                logintime = Activitylog.objects.filter(user=user,activity='login').order_by("-activitytime")[1].activitytime
            except Exception as e:
                logger.info(e)
                logintime = Activitylog.objects.filter(user=user, activity='login').order_by("-activitytime")[0].activitytime

            logintime = logintime.strftime("%d %b %Y, %H:%M") + " UTC"
            return logintime
        else:
            return "---"
    except Exception as e:
        logger.info(e)
        return "---"


@register.simple_tag
def hide_characters(string):
    string = str(string)
    if len(string) - 3 > 4:
        length = 3
    elif len(string) - 3 > 2:
        length = 2
    else:
        length = 1
    first = string[0:length if length>2 else length]
    last = string[-length:]
    return "{} xxxx {}".format(first,last)



@register.simple_tag
def generate_otp_type_string(request):
    user = request.user
    if not user.is_authenticated:
        user = User.objects.get(email=request.session.get("user_email"))
    try:
        if "/verifyOTP" not in request.path:
            if request.session.get("mob_verification_token"):
                del request.session['mob_verification_token'] # Temp code
        user_account = Useraccounts.objects.get(customer__user=user)
        if request.session.get("mob_verification_token"):
            return f'{user_account.countrycode}{user_account.phonenumber}'
        else:
            send_to = user.email

            if user_account.otptype == 2 and user_account.phoneverified:
                send_to = f'{send_to} <br /> & <br /> {user_account.countrycode}{user_account.phonenumber}'
            return send_to
    except Exception as e:
        logger.info(e)
        return user.email

@register.filter(name='docValue')
def docValue(input):
    try:
        value =Customerdocumentdetails.objects.get(customerdocument=input).value
    except Exception as e:
        logger.info(e)
        value = ''
    return value

@register.filter(name='docField')
def docField(input):
    try:
        field_id =Customerdocumentdetails.objects.get(customerdocument=input).field.id
    except Exception as e:
        logger.info(e)
        field_id = ''
    return field_id

@register.filter(name='docFieldName')
def docFieldName(input):
    try:
        field_name =Customerdocumentdetails.objects.get(customerdocument=input).field.fieldname
    except Exception as e:
        logger.info(e)
        field_name = ''
    return field_name

@register.filter(name='docType')
def docType(input):
    try:
        doc_type =Customerdocumentdetails.objects.get(customerdocument=input).customerdocument.documenttype.name
    except Exception as e:
        logger.info(e)
        doc_type = ''
    return doc_type

@register.filter(name='docFile')
def docFile(input):
    try:
        doc_file =Customerdocumentfiles.objects.get(customerdocument=input).filelocation
    except Exception as e:
        logger.info(e)
        doc_file =''
    return doc_file


@register.simple_tag
def check_current_menu(current_path):
    settings_paths = ['settings','documentVerification','verification']
    wire_transfer_paths = ['international-wire-transfer','wire-transfer-confirm']
    if any(path in current_path for path in settings_paths):
        return 'settings'
    elif any(path in current_path for path in wire_transfer_paths):
        return 'wire_transfer'

@register.filter(name='to_int')
def to_int(value):
    return int(value)


@register.simple_tag
def get_transaction_type(transaction):
    transaction_type = transaction.transactiontype.name
    if transaction_type == "Third Party Transfer":
        transaction_type = "International Transfer"
        if transaction.amount_type in ["Conversion Fee","Wire Transfer Fee"]:
            transaction_type += " Fee"
    elif transaction_type == "Wallet Withdrawal Transfer":
        transaction_type = "Wallet Withdrawal Transfer"
        if transaction.amount_type in ["Conversion Fee","Wallet Withdrawal Fee"]:
            transaction_type += " Fee"
    elif transaction_type == "Domestic Transfer":
        transaction_type = "Domestic Transfer"
        if transaction.amount_type in ["Conversion Fee","Domestic Transfer Fee"]:
            transaction_type += " Fee"
    else:
        if transaction.toaccount and transaction.toaccount.user_account.ismaster_account:
            if transaction_type == "International Transfer Fee to Master Account":
                transaction_type = "International Transfer"
            if transaction_type == "Wallet Withdrawal Transfer Fee to Master Account":
                transaction_type = "Wallet Withdrawal Transfer"
            if transaction_type == "Domestic Transfer Fee to Master Account":
                transaction_type = "Domestic Transfer"
            transaction_type += " Fee"
    return transaction_type


@register.simple_tag
def get_beneficiary(transaction):
    if transaction.transactiontype.name == "Third Party Transfer":
        data = {
            'name': transaction.inltransaction_tr.all()[0].accountholdername if transaction.inltransaction_tr.all() else "NA",
            'email': transaction.inltransaction_tr.all()[0].email if transaction.inltransaction_tr.all() else "NA"
        }
        return data
    if transaction.transactiontype.name == "Wallet Withdrawal Transfer":
        data = {
            'name': transaction.walletwithdrawal_tr.all()[0].accountholdername if transaction.walletwithdrawal_tr.all() else "NA",
            'email': 'NA'
        }
        return data
    if transaction.transactiontype.name == "Domestic Transfer":
        data = {
            'name': transaction.domtransaction_tr.all()[0].accountholdername if transaction.domtransaction_tr.all() else "NA",
            'email': transaction.domtransaction_tr.all()[0].email if transaction.domtransaction_tr.all() else "NA"
        }
        return data
    if transaction.toaccount.user_account.ismaster_account:
        data = {
        'name':'NA',
        'email':'NA',
        }
        return data
    if transaction.transactiontype.name not in settings.EXCLUDED_TRANSACTION_TYPES and transaction.toaccount:
        full_name = f'{transaction.toaccount.user_account.firstname if transaction.toaccount.user_account.firstname else ""} {transaction.toaccount.user_account.middlename if transaction.toaccount.user_account.middlename else ""} {transaction.toaccount.user_account.lastname if transaction.toaccount.user_account.lastname else ""}'
        email = f'{transaction.toaccount.user_account.customer.user.email if  transaction.toaccount.user_account and transaction.toaccount.user_account.customer and transaction.toaccount.user_account.customer.user else ""}'
    else:
        full_name = 'NA'
        email = 'NA'
    data = {
        'name':full_name,
        'email':email,
    }
    return data


@register.simple_tag
def get_debit_amount(transaction, tr_req='False',tr_det='False'):
    from utils.models import Transactions
    tr_req = eval(str(tr_req))
    transaction_type = transaction.transactiontype.name
    if transaction_type == "Third Party Transfer":
        if transaction.amount_type == "Wire Transfer Fee":
            debit_amount = Transactions.objects.filter(transactionno=transaction.transactionno, amount_type__in=['Wire Transfer Fee','Conversion Fee']).aggregate(
                Sum('fromamount')).get('fromamount__sum')
            cable_charge = get_transaction_amounts(transaction).get("cable_charge")
            debit_amount += cable_charge if cable_charge else 0
        elif tr_req:
            debit_amount = Transactions.objects.filter(transactionno=transaction.transactionno).aggregate(Sum('fromamount')).get(
                'fromamount__sum')
            cable_charge = get_transaction_amounts(transaction).get("cable_charge")
            debit_amount += cable_charge if cable_charge else 0
        else:
            debit_amount = Transactions.objects.filter(transactionno=transaction.transactionno,amount_type='Net Amount').aggregate(Sum('fromamount')).get('fromamount__sum')
    elif transaction_type == "Domestic Transfer":
        if transaction.amount_type == "Domestic Transfer Fee":
            debit_amount = Transactions.objects.filter(transactionno=transaction.transactionno, amount_type__in=['Domestic Transfer Fee','Conversion Fee']).aggregate(
                Sum('fromamount')).get('fromamount__sum')
            cable_charge = get_transaction_amounts(transaction).get("cable_charge")
            debit_amount += cable_charge if cable_charge else 0
        elif tr_req:
            debit_amount = Transactions.objects.filter(transactionno=transaction.transactionno).aggregate(Sum('fromamount')).get(
                'fromamount__sum')
            cable_charge = get_transaction_amounts(transaction).get("cable_charge")
            debit_amount += cable_charge if cable_charge else 0
        else:
            debit_amount = Transactions.objects.filter(transactionno=transaction.transactionno,amount_type='Net Amount').aggregate(Sum('fromamount')).get('fromamount__sum')
    elif transaction_type == "Wallet Withdrawal Transfer":
        if transaction.amount_type == "Wallet Withdrawal Fee":
            debit_amount = Transactions.objects.filter(transactionno=transaction.transactionno, amount_type__in=['Wallet Withdrawal Fee','Conversion Fee']).aggregate(
                Sum('fromamount')).get('fromamount__sum')
            cable_charge = get_transaction_amounts(transaction).get("cable_charge")
            debit_amount += cable_charge if cable_charge else 0
        elif tr_req:
            debit_amount = Transactions.objects.filter(transactionno=transaction.transactionno).aggregate(Sum('fromamount')).get(
                'fromamount__sum')
            cable_charge = get_transaction_amounts(transaction).get("cable_charge")
            debit_amount += cable_charge if cable_charge else 0
        else:
            debit_amount = Transactions.objects.filter(transactionno=transaction.transactionno,amount_type='Net Amount').aggregate(Sum('fromamount')).get('fromamount__sum')

    else:
        debit_amount = Transactions.objects.filter(transactionno=transaction.transactionno).aggregate(Sum('fromamount')).get('fromamount__sum')

    return format(debit_amount,".4f")


@register.simple_tag
def is_debit_or_credit(transaction, accountno):
    if transaction.transactiontype.name == "Third Party Transfer":
        to_account = transaction.inltransaction_tr.all()[0].accountnumber if transaction.inltransaction_tr.all() else None
    elif transaction.transactiontype.name == "Domestic Transfer":
        to_account = transaction.domtransaction_tr.all()[0].accountnumber if transaction.domtransaction_tr.all() else None
    elif transaction.transactiontype.name == "Wallet Withdrawal Transfer":
        to_account = transaction.walletwithdrawal_tr.all()[0].accountholdername if transaction.walletwithdrawal_tr.all() else None
    elif transaction.transactiontype.name == "Other Charges":
        to_account = transaction.toaccount.accountno
        if to_account and to_account == accountno:
            return 'debit'
    elif transaction.transactiontype.name in ["International Transfer Fee to Master Account", "Wallet Withdrawal Transfer Fee to Master Account", "Domestic Transfer Fee to Master Account"]:
        if transaction.toaccount.user_account.ismaster_account:
            return 'credit'
    else:
        to_account = transaction.toaccount.accountno if transaction.toaccount else None
    if transaction.fromaccount and transaction.fromaccount.accountno == accountno:
        return 'debit'
    elif to_account and to_account == accountno:
        return 'credit'
    else:
        return None


@register.simple_tag
def get_recipient_accountnumber(transaction):
    if transaction.transactiontype.name == "Third Party Transfer":
        return transaction.inltransaction_tr.all()[0].accountnumber if transaction.inltransaction_tr.all() else "NA"
    elif transaction.transactiontype.name == "Wallet Withdrawal Transfer":
        return transaction.walletwithdrawal_tr.all()[0].wallet_name if transaction.walletwithdrawal_tr.all() else "NA"
    elif transaction.transactiontype.name == "Domestic Transfer":
        return transaction.domtransaction_tr.all()[0].accountnumber if transaction.domtransaction_tr.all() else "NA"
    else:
        if transaction.toaccount.user_account.ismaster_account:
            return transaction.fromaccount.accountno if transaction.fromaccount else "NA"
        else:
            return transaction.toaccount.accountno if transaction.toaccount else "NA"


@register.simple_tag
def get_reference(transaction):
    transaction_type = transaction.transactiontype.name
    if transaction_type == "Third Party Transfer":
        if transaction.amount_type == "Wire Transfer Fee":
            return f"International Transfer Fee for Transaction No.{transaction.transactionno}"
        else:
            return f"AC - {get_recipient_accountnumber(transaction)}"
    elif transaction_type == "Wallet Withdrawal Transfer":
        if transaction.amount_type == "Wallet Withdrawal Fee":
            return f"Wallet Withdrawal Transfer Fee for Transaction No.{transaction.transactionno}"
        else:
            return f"Wallet Address - {get_recipient_accountnumber(transaction)}"
    elif transaction_type == "Domestic Transfer":
        if transaction.amount_type == "Domestic Transfer Fee":
            return f"Domestic Transfer Fee for Transaction No.{transaction.transactionno}"
        else:
            return f"AC - {get_recipient_accountnumber(transaction)}"
    elif transaction_type in ["Inward Remittance","Other Charges","International Transfer Fee to Master Account","Refund","Wallet Withdrawal Transfer Fee to Master Account", "Domestic Transfer Fee to Master Account"]:
        return transaction.note
    elif transaction.transactiontype.name == "Affiliate Fee":
        account_details = "NA"
        if transaction.note:
            account_details = transaction.note
        elif transaction.toaccount:
            account_details = f"AC - {transaction.toaccount.accountno}"
        return account_details
    else:
        return f"AC - {get_recipient_accountnumber(transaction)}"


@register.simple_tag
def get_transaction_amounts(transaction):
    from utils.models import Transactions # since app and model have same names
    transactions = Transactions.objects.filter(transactionno=transaction.transactionno)
    try:
        cable_charge = Cablecharges.objects.get(parenttransaction__transactionno=transaction.transactionno).chargeamount
    except Exception as e:
        logger.info(e)
        cable_charge = None
    return {
        'net_amount':transactions.filter(amount_type='Net Amount')[0].fromamount if transactions.filter(amount_type='Net Amount') else None,
        'wire_fee':transactions.filter(amount_type='Wire Transfer Fee')[0].fromamount if transactions.filter(amount_type='Wire Transfer Fee') else None,
        'conversion_fee':transactions.filter(amount_type='Conversion Fee')[0].fromamount if transactions.filter(amount_type='Conversion Fee') else None,
        'wallet_fee':transactions.filter(amount_type='Wallet Withdrawal Fee')[0].fromamount if transactions.filter(amount_type='Wallet Withdrawal Fee') else None,
        'domestic_fee':transactions.filter(amount_type='Domestic Transfer Fee')[0].fromamount if transactions.filter(amount_type='Domestic Transfer Fee') else None,
        'cable_charge':cable_charge,
    }


@register.simple_tag
def get_transaction_receipt(transaction):
    try:
        tr_receipt = InvoiceDocument.objects.get(transaction__transactionno=transaction.transactionno).invoice_doc
        tr_receipt = str(tr_receipt).replace("invoice_uploads/","")
    except Exception as e:
        logger.info(e)
        tr_receipt = None
    return tr_receipt


@register.simple_tag
def get_accounts(request):
    from utils.models import Accounts
    return Accounts.active.filter(user_account__customer__user=request.user).order_by('currency__code')

@register.filter(name='value_change')
def value_change(value):
    return value if value and value != "" else 'N/A'

@register.filter(name='business_details')
def business_details(value):
    company_detials = ''
    try:
        if value.customer.customertype == 2:
            company_detials = Businessdetails.objects.get(customer=value.customer)
            company_name=company_detials.companyname
            return f' ({company_name})'
        else:
            return f'{company_detials}'
    except Exception as e:
        logger.info(e)
        return f'{company_detials}'


@register.filter(name='doc_details')
def doc_details(value):
    customer_doc_details = Customerdocumentdetails.objects.filter(customerdocument=value,isdeleted=False)
    return customer_doc_details

@register.filter(name='customer_doc_files')
def customer_doc_files(value):
    file = Customerdocumentfiles.objects.filter(customerdocument=value)
    return file

@register.filter(name='doc_heading')
def doc_heading(value):
    doc = []
    heading = ''
    for i in value:
        if i.verificationtype.verificationtype == 1:
            doc.append('idDocuments')
        elif i.verificationtype.verificationtype == 2:
            doc.append('addressDocuments')
    if not 'idDocuments' in  doc or not 'addressDocuments' in  doc:
        if not 'idDocuments' in  doc and not 'addressDocuments' in  doc:
            heading = 'No Personal Documents Uploaded'
        if not 'idDocuments' in  doc and 'addressDocuments' in  doc:
            heading = 'No ID Documents Uploaded'
        if 'idDocuments' in  doc and  not 'addressDocuments' in  doc:
            heading = 'No Address Documents Uploaded'
    else:
        heading = 'Documents'

    return heading

@register.simple_tag
def get_affiliate_amount(int_transaction):
    from Transactions.mixins import FindAccount, get_class_name
    try:
        transaction = int_transaction.transaction
        if get_class_name(int_transaction) == "Internationaltransactions":
            wire_fee = Transactions.active.get(transactionno=transaction.transactionno,
                                            amount_type="Wire Transfer Fee").fromamount
        elif get_class_name(int_transaction) == "DomesticTransaction":
            wire_fee = Transactions.active.get(transactionno=transaction.transactionno,
                                            amount_type="Domestic Transfer Fee").fromamount
    except Exception as e:
        logger.info(e)
        return None
    if wire_fee > 0:
        if wire_fee and transaction.fromaccount.user_account.referred_by:
            affiliate_amount = Decimal(wire_fee) * round((transaction.affiliate_fee_percentage/100),2)
            referred_by_user = transaction.fromaccount.user_account.referred_by
            account_obj,affiliate_amount = FindAccount().find_affiliate_account_convert_amount(referred_by_user,transaction.fromaccount.currency,affiliate_amount)
            if account_obj and affiliate_amount:
                affiliate_amount = f"{affiliate_amount} {account_obj.currency.code}"
                return affiliate_amount
    return None

@register.simple_tag
def get_wallet_withdrawal_affiliate_amount(transaction):
    from Transactions.mixins import FindAccount
    try:
        wallet_fee = Transactions.active.get(transactionno=transaction.transactionno,
                                           amount_type="Wallet Withdrawal Fee").fromamount
    except Exception as e:
        logger.info(e)
        return None
    if wallet_fee > 0:
        if wallet_fee and transaction.fromaccount.user_account.referred_by:
            affiliate_amount = Decimal(wallet_fee) * round((transaction.affiliate_fee_percentage/100),2)
            referred_by_user = transaction.fromaccount.user_account.referred_by
            account_obj,affiliate_amount = FindAccount().find_affiliate_account_convert_amount(referred_by_user,transaction.fromaccount.currency,affiliate_amount)
            if account_obj and affiliate_amount:
                affiliate_amount = f"{affiliate_amount} {account_obj.currency.code}"
                return affiliate_amount
    return None

@register.filter(name='company_users_list')
def company_users_list(companyname):
    company_customers = ''
    if companyname:
        company_customers = Useraccounts.objects.filter(customer__bsnssdtls_cstmr__companyname=companyname).order_by('id')
    return company_customers

@register.filter(name='acc_list')
def acc_list(acc,user_acc):
    if acc:
        return acc
    else:
        customer = user_acc.added_by
        account_details =  Accounts.objects.filter(user_account__customer=customer, isdeleted=False).order_by('isprimary')
        return account_details
        
@register.simple_tag
def acc_bal(user_acc):
    customer = user_acc.added_by
    account_details =  Accounts.objects.filter(user_account__customer=customer, isdeleted=False).order_by('isprimary')
    account = account_details[0] if account_details else None
    return f'{account.balance} {account.currency.code}' if account else None

@register.filter(name='get_active')
def get_active(queryset):
    return queryset.filter(isdeleted=False)

@register.filter(name='company_name')
def company_name(queryset):
    business_details = Businessdetails.objects.filter(isdeleted=False,customer=queryset)[0]
    return business_details.companyname

@register.simple_tag
def get_balance_amount(transaction):
    transaction_type = get_transaction_type(transaction)
    if transaction_type in ["Inward Remittance", "Other Charges","Refund","Affiliate Fee","Other Charges Fee"]:
        balance_amount = transaction.toaccountbalance
    else:
        try:
            last_transaction = Transactions.active.filter(transactionno=transaction.transactionno).order_by('-id')[0]
            if transaction_type in ["International Transfer", "Wallet Withdrawal Transfer", "Domestic Transfer"]:
                last_transaction = Transactions.active.filter(transactionno=transaction.transactionno,amount_type="Net Amount")[0]
            balance_amount = last_transaction.fromaccountbalance
        except Exception as e:
            logger.info(e)
            balance_amount = transaction.fromaccountbalance
    if transaction_type in ["International Transfer Fee", "Wallet Withdrawal Transfer Fee", "Domestic Transfer Fee"]:
        cable_charge = get_transaction_amounts(transaction).get("cable_charge")
        balance_amount -= cable_charge if cable_charge else 0
    if balance_amount:
        balance_amount = format(float(balance_amount),".4f")
    return balance_amount



@register.simple_tag
def enable_view_action(transaction,request):
    transaction_type = get_transaction_type(transaction)
    flag = False
    if request.user.adminacc_created_by and transaction_type in ["International Transfer Fee", "Wallet Withdrawal Transfer Fee", "Domestic Transfer Fee"] and transaction.amount_type != "Admin Fee":
       return False
    if transaction_type in ["International Transfer", "Acccount To Account Transfer","Currency Conversion","Wallet Withdrawal Transfer", "Domestic Transfer"]:
        return True
    elif request.user.adminacc_created_by  and transaction_type in ["Acccount To Account Transfer Fee","Currency Conversion Fee","International Transfer Fee","Wallet Withdrawal Transfer Fee", "Domestic Transfer Fee"]:
        return True
    else:
        return False

@register.simple_tag
def get_tr_details_debit_amount(transaction):
    debit_amount = Transactions.objects.filter(transactionno=transaction.transactionno,
                                               amount_type__in=['Net Amount', 'Conversion Fee']).aggregate(
        Sum('fromamount')).get('fromamount__sum')
    return debit_amount

@register.filter(name='filter_by')
def filter_by(queryset,filter_type):
    if filter_type == "phonecode":
        return queryset.order_by('phonecode')
    if filter_type == "phonecode-dist":
        return queryset.distinct('phonecode').order_by('phonecode')
    return queryset

@register.filter(name='refund_show')
def refund_show(int_transaction):
    from entrebiz import settings
    current_date = datetime.datetime.now().date()
    days_difference = current_date - int_transaction.createdon.date()
    if days_difference.days <= settings.FEE_CALCULATE_MINIMUM_DURATION and int_transaction.verificationstatus in ["Executed","Pending","Refund Rejected"]:
        return True
    else:
        return False


@register.filter(name='show_last_chars')
def show_last_chars(string,length=4):
    if len(string)>length:
        last = string[-int(length):]
    else:
        last = string
    return f'XXXX XXXX {last}'

@register.filter(name='to_decimals')
def to_decimals(value,dec_points=4):
    if value:
        return format(value,f".{dec_points}f")
    return "-"

@register.filter(name='to_color')
def to_color(value):
    if Decimal(value) < 0:
        return 'red'
    else:
        return 'green'

@register.simple_tag
def show_transaction(transactions, request):
    if (transactions.verificationstatus == 'Pending' or transactions.verificationstatus == 'Hold' or transactions.verificationstatus == 'Refund Rejected' or transactions.verificationstatus == 'Refund Requested') and request.user.adminacc_created_by.approval_level == 'Inputter':
        return False
    else:
        return True

@register.simple_tag
def show_comment(transactions, request):
    if (transactions.verificationstatus == 'Executed' or transactions.verificationstatus == 'Refunded' or transactions.verificationstatus == 'Refund Requested'):
        return False
    else:
        return True
    
@register.filter(name='get_transaction_endpoint_by_obj')
def get_transaction_endpoint_by_obj(obj):
    if isinstance(obj, Internationaltransactions):
        return f"/getransactionDetails?TransactionId=INT_{obj.slug}"
    elif isinstance(obj, DomesticTransaction):
        return f"/getransactionDetails?TransactionId=DOM_{obj.slug}"
    else:
        return ""
    
@register.filter(name='get_class_name')
def get_class_name(obj):
    return type(obj).__name__

@register.filter(name='add_type_prefix')
def add_type_prefix(obj):
    if isinstance(obj, Internationaltransactions):
        return f"INT_{obj.id}"
    elif isinstance(obj, DomesticTransaction):
        return f"DOM_{obj.id}"
    else:
        return ""