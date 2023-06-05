from decimal import Decimal
import logging
import threading
import random
import string
import six
import math
from django.conf import settings
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Sum, Q
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.core.mail import EmailMessage
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.models import LogEntry
from random import randint
from utils.models import AdminAccount, Currencyconversionratescombined, Otps, Transactions, Transactiontypes, Useraccounts, Activationlinks, Accounts, Cablecharges, InvoiceDocument, \
    Internationaltransactions, Comments
import datetime
from twilio.rest import Client
logger = logging.getLogger('lessons')

class CustomMail:
    def send_custom_mail(self,subject,content,sendermail):
        year = datetime.date.today().year
        context = {
            'year' : year,
            'body' : content,
            'domain' : settings.CURRENT_DOMAIN
        }
        template = render_to_string('customer-management/custom-email-template.html',context)
        from_user = settings.EMAIL_HOST_USER
        to_user = [sendermail,]
        def thread_send_custom_mail(subject,template,from_user,to_user):
            email = EmailMessage(subject,template,from_user,to_user)
            email.content_subtype = 'html'
            email.fail_silently=False
            email.send()
        process_mail = threading.Thread(target=thread_send_custom_mail,args=(subject,template,from_user,to_user))
        process_mail.start()
    def send_refferal_mail(self,full_name,subject,content,sendermail):
        context = {
            'full_name' : full_name,
            'domain' : settings.CURRENT_DOMAIN,
            'content' : content
        }
        template = render_to_string('userdetails/refer-friend/refferal-mail.html',context)
        from_user = settings.EMAIL_HOST_USER
        to_user = [sendermail,]
        def thread_send_refferal_mail(subject,template,from_user,to_user):
            email = EmailMessage(subject,template,from_user,to_user)
            email.content_subtype = 'html'
            email.fail_silently=False
            email.send()
        process_mail = threading.Thread(target=thread_send_refferal_mail,args=(subject,template,from_user,to_user))
        process_mail.start()

class SendAddMoneySuccessMailtoUser:
    def send_mail(self,full_name,amount,curr_code,subject,sendermail):
        year = datetime.date.today().year
        context = {
            'year' : year,
            'full_name' : full_name,
            'amount' : amount,
            'curr_code' : curr_code,
            'domain' : settings.CURRENT_DOMAIN
        }
        template = render_to_string('inward-remittance-approval/Addmoneytoaccountsuccess.html',context)
        from_user = settings.EMAIL_HOST_USER
        to_user = [sendermail,]
        def thread_send_mail(subject,template,from_user,to_user):
            email = EmailMessage(subject,template,from_user,to_user)
            email.content_subtype = 'html'
            email.fail_silently=False
            email.send()
        process_mail = threading.Thread(target=thread_send_mail,args=(subject,template,from_user,to_user))
        process_mail.start()

class OTP:
    def send_email_otp(self,transaction_type, created_by, email,full_name,token,activation_code=None):
        try:
            valid_till = datetime.datetime.now() + datetime.timedelta(days=settings.OTP_EXP)
            valid_till = valid_till.date().strftime(settings.DATE_FORMAT)
            if not activation_code:
                activation_code = randint(settings.OTP_NUMBER_RANGE[0], settings.OTP_NUMBER_RANGE[1])
            from_user = settings.EMAIL_HOST_USER
            to_user = [email,]

            if transaction_type == 1:
                otp_type = "MobileNumber Verification"
                Purposevalue = "mobilenumber verification initiated through"
            else:
                otp_type = "Other Purposes"
                Purposevalue = "other purposes initiated through"

            otp,status = Otps.objects.get_or_create(
                    transactiontype=otp_type,
                    createdby=created_by,
                    token=token,
                    )
            otp.code = activation_code
            otp.validtill = valid_till
            otp.save()
            subject =  "OTP - "+ otp_type
            PlaceholderkeyUservalue = full_name.title()
            PlaceholderkeyYearvalue = str(datetime.date.today().year)
            PlaceholderkeyOtpvalue = str(activation_code)
            PlaceholderkeyPurposevalue = Purposevalue

            template = render_to_string('accounts/wire_transfer/otp-mail-template.html',{
            'PlaceholderkeyUservalue' : PlaceholderkeyUservalue,
            'PlaceholderkeyYearvalue' : PlaceholderkeyYearvalue,
            'PlaceholderkeyOtpvalue' : PlaceholderkeyOtpvalue,
            'PlaceholderkeyPurposevalue' : PlaceholderkeyPurposevalue,
            'domain' : settings.CURRENT_DOMAIN
            })

            def thread_send_notification(subject,template,from_user,to_user):
                send_mail(subject=subject,message=template,html_message=template,from_email=from_user,recipient_list=to_user,fail_silently=False)

            def send_sms(created_by=created_by,activation_code=activation_code):
                try:
                    user_account = Useraccounts.objects.get(customer__user=created_by)
                    if (user_account.otptype == 2 and user_account.phoneverified) or transaction_type == 1:
                        phone_number = f'{user_account.countrycode}{user_account.phonenumber}'
                        otp_string = "Your OTP is " + str(
                            activation_code) + " \nPlease do not share this OTP with anyone for security reasons."
                        send_twilio_sms(phone_number, otp_string)
                except Exception as e:
                    logger.info(f"Twilio error >> {e}")

            if not transaction_type == 1:
                process_mail = threading.Thread(target=thread_send_notification,args=(subject,template,from_user,to_user))
                process_mail.start()

            process_sms = threading.Thread(target=send_sms,
                                            args=(created_by, activation_code))
            process_sms.start()

            return True
        except Exception as e:
            logger.info(f"{e}")
            return False


class TransactionMail:
    def transaction_success_or_failure_mail(self, email,email_data, status,attach=None, transaction_type=None):
        try:
            Subject = "Transaction Invoice"
            if not status:
                Subject = "Transaction Failed"

            templatename = 'accounts/wire_transfer/transaction-success-mail.html'
            if transaction_type == 2:
                templatename = 'transactions/currency_conversion/email/transaction-success-mail.html'
            email_data['domain'] = settings.CURRENT_DOMAIN
            template= render_to_string(templatename,email_data)
            from_user = settings.EMAIL_HOST_USER
            to_user = [email,]
            def thread_send_transaction_mail(Subject,template,from_user,to_user,bcc=None):
                if bcc:
                    email = EmailMessage(Subject,template,from_user,to_user,bcc)
                else:
                    email = EmailMessage(Subject,template,from_user,to_user)
                email.content_subtype = 'html'
                if attach:
                    email.attach_file(attach)
                email.fail_silently=False
                email.send()
            if not email_data.get("test_user") and any(email_data.get(f"{transfer_type}_success") for transfer_type in ["wire_transfer", "domestic", "wallet_transfer"]):
                bcc = list(AdminAccount.objects.filter(isdeleted=False, admin_level="Super Admin", status=True).values_list("createdby__email", flat=True))
                process_mail = threading.Thread(target=thread_send_transaction_mail,args=(Subject,template,from_user,to_user,bcc))
            else:
                process_mail = threading.Thread(target=thread_send_transaction_mail,args=(Subject,template,from_user,to_user))
            process_mail.start()
            return True
        except Exception as e:
            logger.info(e)
            return False

    def mail_transfer_executed(self,recipient,context):
        templatename = "wire-transfer-request/email/fund-transfer-approved-mail.html"
        subject = "Your Fund Transfer Request Has Been Approved"
        sender = settings.EMAIL_HOST_USER
        context['domain'] = settings.CURRENT_DOMAIN
        template = render_to_string(templatename, context)
        def thread_transfer_executed_mail(subject, template, sender, recipient):
            email = EmailMessage(subject, template, sender, recipient)
            email.content_subtype = 'html'
            email.fail_silently = False
            email.send()

        process_mail = threading.Thread(target=thread_transfer_executed_mail,
                                        args=(subject, template, sender, [recipient]))
        process_mail.start()
        return True


def send_twilio_sms(recipient,body):
    account_sid = settings.TWILIO_ACCOUNT_SID
    auth_token = settings.TWILIO_AUTH_TOKEN
    client = Client(account_sid, auth_token)

    message = client.messages.create(
        body=body,
        from_=settings.TWILIO_NUMBER,
        to=recipient
    )
    return message


def randomword(length):
    str_letters = string.ascii_lowercase
    return ''.join(random.choice(str_letters) for i in range(length))


class ConfirmYourMail:
    def send_confirm_mail(self, full_name, email, createdby,transaction_type, dev_type=None):
        try:
            activation_code = randomword(30)
            if dev_type == '1':
                link = f"{settings.DOMAIN}?activationLink={activation_code}"
            else:
                link = f"{settings.DOMAIN}?activationLink={activation_code}"
            valid_till = datetime.datetime.now() + datetime.timedelta(days=settings.ACTIVATION_LINK_EXP)
            valid_till = valid_till.date().strftime(settings.DATE_FORMAT)
            if transaction_type == 1:
                link_type = "Confirm your email"
                reason = 'complete your signing up'
            else:
                link_type = "Forgot password"
                reason = 'reset your password'
            activation_link,status = Activationlinks.objects.get_or_create(createdby=createdby,transactiontype=link_type)
            activation_link.link=link
            activation_link.validated=False
            activation_link.validtill=valid_till
            activation_link.activationcode=activation_code
            activation_link.save()
            email_data = {
                'full_name' : full_name,
                'url' : link,
                'year' : str(datetime.date.today().year),
                'domain' : settings.CURRENT_DOMAIN,
                'reason' : reason
            }
            Subject = link_type
            template= render_to_string('accounts/openaccount/personal-signup/confirm-your-email.html',email_data)
            from_user = settings.EMAIL_HOST_USER
            to_user = [email,]
            def thread_send_confirm_mail(Subject,template,from_user,to_user):
                email = EmailMessage(Subject,template,from_user,to_user)
                email.content_subtype = 'html'
                email.fail_silently=False
                email.send()
            process_mail = threading.Thread(target=thread_send_confirm_mail,args=(Subject,template,from_user,to_user))
            process_mail.start()
            return True
        except Exception as e:
            logger.info(e)
            return False


class ModelQueries:
    def get_accounts(self,request,useracc=None):
        if useracc:
            return Accounts.active.filter(user_account__customer=request.customer).order_by('currency__code')
        else:
            return Accounts.active.filter(user_account__customer__user=request.user).order_by('currency__code')

    def get_transactions(self,request,order_by):
        return Transactions.objects.filter(createdby=request.user, isdeleted=False) \
                .order_by(f'{order_by}')

    def get_transactions_filtered(self,transactions,accountid=None,transaction_no=None,beneficiary_name=None,from_date=None,to_date=None,creditdebit=None):
        if transaction_no:
            transactions = transactions.filter(transactionno=transaction_no)
        if beneficiary_name:
            transactions_to_be_appended = transactions.filter(inltransaction_tr__accountholdername__icontains=beneficiary_name)
            transactions = transactions.filter(transactiontype__name='Acccount To Account Transfer',toaccount__user_account__fullname__icontains=beneficiary_name)
            transactions = transactions_to_be_appended | transactions
        if from_date:
            from_date_obj = datetime.datetime.strptime(from_date, settings.DATE_FORMAT)
            transactions = transactions.filter(createdon__gte=from_date_obj.date())
        if to_date:
            to_date_obj = datetime.datetime.strptime(to_date, settings.DATE_FORMAT)

        elif from_date and not to_date:
            to_date_obj = datetime.datetime.now()
        else:
            to_date_obj = None
        if to_date_obj:
            to_date_obj = to_date_obj + datetime.timedelta(days=1)
            transactions = transactions.filter(createdon__lt=to_date_obj.date())
        if creditdebit:
            if creditdebit == "1":
                transactions = transactions.filter(~Q(transactiontype__name='Other Charges',
                                                                                  toaccount__id=accountid),toaccount__id=accountid)
            elif creditdebit == "2":
                transactions = transactions.filter(Q(fromaccount__id=accountid)|Q(transactiontype__name='Other Charges',
                                                                                  toaccount__id=accountid))

        return transactions

    def paginate(self,queryset,page,per_page):
        paginator = Paginator(queryset, per_page)
        try:
            queryset = paginator.page(page)
        except PageNotAnInteger:
            queryset = paginator.page(1)
        except EmptyPage:
            queryset = paginator.page(paginator.num_pages)
        return queryset

    def get_transaction_type(self,transaction):
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
                elif transaction_type == "Wallet Withdrawal Transfer Fee to Master Account":
                    transaction_type = "Wallet Withdrawal Transfer"
                elif transaction_type == "Domestic Transfer Fee to Master Account":
                    transaction_type = "Domestic Transfer"
                transaction_type += " Fee"
        return transaction_type

    def get_beneficiary(self,transaction):
        if transaction.transactiontype.name == "Third Party Transfer":
            data = {
                'name': transaction.inltransaction_tr.all()[
                    0].accountholdername if transaction.inltransaction_tr.all() else "NA",
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
            email = f'{transaction.toaccount.user_account.customer.user.email if transaction.toaccount.user_account and transaction.toaccount.user_account.customer and transaction.toaccount.user_account.customer.user else ""}'
        else:
            full_name = 'NA'
            email = 'NA'
        data = {
            'name': full_name,
            'email': email,
        }
        return data

    def is_debit_or_credit(self,transaction, accountno):
        if transaction.transactiontype.name == "Third Party Transfer":
            to_account = transaction.inltransaction_tr.all()[
                0].accountnumber if transaction.inltransaction_tr.all() else None
        elif transaction.transactiontype.name == "Wallet Withdrawal Transfer":
            to_account = transaction.walletwithdrawal_tr.all()[0].accountholdername if transaction.walletwithdrawal_tr.all() else None
        elif transaction.transactiontype.name == "Domestic Transfer":
            to_account = transaction.domtransaction_tr.all()[0].accountnumber if transaction.domtransaction_tr.all() else None
        elif transaction.transactiontype.name == "Other Charges":
            to_account = transaction.toaccount.accountno
            if to_account and to_account == accountno:
                return 'debit'
        else:
            to_account = transaction.toaccount.accountno if transaction.toaccount else None
        if transaction.fromaccount and transaction.fromaccount.accountno == accountno:
            return 'debit'
        elif to_account and to_account == accountno:
            return 'credit'
        else:
            return None

    def get_transaction_amounts(self,transaction,from_amount=False):
        from utils.models import Transactions  # since app and model have same names
        transactions = Transactions.objects.filter(transactionno=transaction.transactionno)
        try:
            cable_charge = Cablecharges.objects.get(
                parenttransaction__transactionno=transaction.transactionno).chargeamount
        except Exception as e:
            logger.info(e)
            cable_charge = None
        data = {
            'net_amount': round(transactions.filter(amount_type='Net Amount')[0].toamount,2) if transactions.filter(
                amount_type='Net Amount') else None,
            'wire_fee': round(transactions.filter(amount_type='Wire Transfer Fee')[0].toamount,2) if transactions.filter(
                amount_type='Wire Transfer Fee') else None,
            'conversion_fee': round(transactions.filter(amount_type='Conversion Fee')[0].fromamount,2) if transactions.filter(
                amount_type='Conversion Fee') else None,
            'wallet_fee': round(transactions.filter(amount_type='Wallet Withdrawal Fee')[0].fromamount,2) if transactions.filter(amount_type='Wallet Withdrawal Fee') else None,
            'domestic_fee': round(transactions.filter(amount_type='Domestic Transfer Fee')[0].toamount,2) if transactions.filter(amount_type='Domestic Transfer Fee') else None,
            'cable_charge': round(cable_charge,2) if cable_charge else 0.00,
        }
        if from_amount:
            data['net_amount'] = round(transactions.filter(amount_type='Net Amount')[0].fromamount,2) if transactions.filter(
                amount_type='Net Amount') else None
        return data

    def get_debit_amount(self,transaction,tr_req=False):
        from utils.models import Transactions
        transaction_type = transaction.transactiontype.name
        if transaction_type == "Third Party Transfer":
            if transaction.amount_type == "Wire Transfer Fee":
                debit_amount = Transactions.objects.filter(transactionno=transaction.transactionno,
                                                           amount_type__in=['Wire Transfer Fee',
                                                                            'Conversion Fee']).aggregate(
                    Sum('fromamount')).get('fromamount__sum')
                cable_charge = self.get_transaction_amounts(transaction).get("cable_charge")
                debit_amount += cable_charge if cable_charge else 0
            elif tr_req:
                debit_amount = Transactions.objects.filter(transactionno=transaction.transactionno).aggregate(
                    Sum('fromamount')).get(
                    'fromamount__sum')
                cable_charge = self.get_transaction_amounts(transaction).get("cable_charge")
                debit_amount += cable_charge if cable_charge else 0
            else:
                debit_amount = Transactions.objects.filter(transactionno=transaction.transactionno,
                                                           amount_type='Net Amount').aggregate(Sum('fromamount')).get(
                    'fromamount__sum')
        elif transaction_type == "Wallet Withdrawal Transfer":
            if transaction.amount_type == "Wallet Withdrawal Fee":
                debit_amount = Transactions.objects.filter(transactionno=transaction.transactionno, amount_type__in=['Wallet Withdrawal Fee','Conversion Fee']).aggregate(
                    Sum('fromamount')).get('fromamount__sum')
                cable_charge = self.get_transaction_amounts(transaction).get("cable_charge")
                debit_amount += cable_charge if cable_charge else 0
            elif tr_req:
                debit_amount = Transactions.objects.filter(transactionno=transaction.transactionno).aggregate(Sum('fromamount')).get(
                    'fromamount__sum')
                cable_charge = self.get_transaction_amounts(transaction).get("cable_charge")
                debit_amount += cable_charge if cable_charge else 0
            else:
                debit_amount = Transactions.objects.filter(transactionno=transaction.transactionno,amount_type='Net Amount').aggregate(Sum('fromamount')).get('fromamount__sum')

        elif transaction_type == "Domestic Transfer":
            if transaction.amount_type == "Domestic Transfer Fee":
                debit_amount = Transactions.objects.filter(transactionno=transaction.transactionno, amount_type__in=['Domestic Transfer Fee','Conversion Fee']).aggregate(
                    Sum('fromamount')).get('fromamount__sum')
                cable_charge = self.get_transaction_amounts(transaction).get("cable_charge")
                debit_amount += cable_charge if cable_charge else 0
            elif tr_req:
                debit_amount = Transactions.objects.filter(transactionno=transaction.transactionno).aggregate(Sum('fromamount')).get(
                    'fromamount__sum')
                cable_charge = self.get_transaction_amounts(transaction).get("cable_charge")
                debit_amount += cable_charge if cable_charge else 0
            else:
                debit_amount = Transactions.objects.filter(transactionno=transaction.transactionno,amount_type='Net Amount').aggregate(Sum('fromamount')).get('fromamount__sum')
        else:
            debit_amount = Transactions.objects.filter(transactionno=transaction.transactionno).aggregate(
                Sum('fromamount')).get('fromamount__sum')

        return format(math.ceil(debit_amount*100)/100,".2f")

    def get_transaction_receipt(self,transaction):
        try:
            tr_receipt = InvoiceDocument.objects.get(transaction__transactionno=transaction.transactionno).invoice_doc
            tr_receipt = str(tr_receipt).replace("invoice_uploads/", "")
        except Exception as e:
            logger.info(e)
            tr_receipt = None
        return tr_receipt

    def get_international_transaction_filtered(self,name=None,email=None,accountno=None,from_date=None,to_date=None,
                                               currencyid=None,tr_status=None):
        int_transactions = Internationaltransactions.active.filter(hideforadmin=False)
        if name:
            int_transactions = int_transactions.filter(
                Q(transaction__createdby__customer_details__useracc_customer__firstname__icontains=name) |
                Q(transaction__createdby__customer_details__useracc_customer__middlename__icontains=name) |
                Q(transaction__createdby__customer_details__useracc_customer__lastname__icontains=name))
        if email:
            int_transactions = int_transactions.filter(
                transaction__createdby__email=email)
        if accountno:

            int_transactions = int_transactions.filter(
                transaction__fromaccount__accountno=int(accountno))
        if from_date:
            from_date_obj = datetime.datetime.strptime(from_date, settings.DATE_FORMAT)
            # from_date_obj = from_date_obj - datetime.timedelta(days=1)
            int_transactions = int_transactions.filter(createdon__gte=from_date_obj.date())
        if to_date:
            to_date_obj = datetime.datetime.strptime(to_date, settings.DATE_FORMAT)

        elif from_date and not to_date:
            to_date_obj = datetime.datetime.now()
        else:
            to_date_obj = None
        if to_date_obj:
            to_date_obj = to_date_obj + datetime.timedelta(days=1)
            int_transactions = int_transactions.filter(createdon__lte=to_date_obj.date())

        if currencyid:
            int_transactions = int_transactions.filter(currency__id=currencyid)

        if tr_status:
            int_transactions = int_transactions.filter(verificationstatus=tr_status)

        return int_transactions

    def create_comment(self,request,comment,tr_status,int_transaction):
        comment_obj = Comments.objects.create(content=comment, createdby=request.user.adminacc_created_by,
                                              status=tr_status)
        int_transaction.verificationstatus = tr_status
        int_transaction.save()
        int_transaction.admincomments.add(comment_obj)
        return comment_obj

    def get_recipient_accountnumber(self,transaction):
        if transaction.transactiontype.name == "Third Party Transfer":
            return transaction.inltransaction_tr.all()[0].accountnumber if transaction.inltransaction_tr.all() else "NA"
        elif transaction.transactiontype.name == "Wallet Withdrawal Transfer":
            return transaction.walletwithdrawal_tr.all()[0].wallet_name if transaction.walletwithdrawal_tr.all() else "NA"
        elif transaction.transactiontype.name == "Domestic Transfer":
            return transaction.domtransaction_tr.all()[0].accountnumber if transaction.domtransaction_tr.all() else "NA"
        else:
            if transaction.toaccount.user_account.ismaster_account and transaction.fromaccount:
                return transaction.fromaccount.accountno if transaction.fromaccount else "NA"
            else:
                return transaction.toaccount.accountno if transaction.toaccount else "NA"

    def get_reference(self,transaction):
        transaction_type = transaction.transactiontype.name
        if transaction_type == "Third Party Transfer":
            if transaction.amount_type == "Wire Transfer Fee":
                return f"International Transfer Fee for Transaction No.{transaction.transactionno}"
            else:
                return f"AC - {self.get_recipient_accountnumber(transaction)}"
        elif transaction_type == "Wallet Withdrawal Transfer":
            if transaction.amount_type == "Wallet Withdrawal Fee":
                return f"Wallet Withdrawal Transfer Fee for Transaction No.{transaction.transactionno}"
            else:
                return f"Wallet Name - {self.get_recipient_accountnumber(transaction)}"
        elif transaction_type == "Domestic Transfer":
            if transaction.amount_type == "Domestic Transfer Fee":
                return f"Domestic Transfer Fee for Transaction No.{transaction.transactionno}"
            else:
                return f"AC - {self.get_recipient_accountnumber(transaction)}"
        elif transaction_type in ["Inward Remittance", "Other Charges","International Transfer Fee to Master Account","Refund","Wallet Withdrawal Transfer Fee to Master Account"]:
            return transaction.note
        elif transaction.transactiontype.name == "Affiliate Fee":
            account_details = "NA"
            if transaction.note:
                account_details = transaction.note
            elif transaction.toaccount:
                account_details = f"AC - {transaction.toaccount.accountno}"
            return account_details
        else:
            return f"AC - {self.get_recipient_accountnumber(transaction)}"

    def filter_user_account(self,name=None,email=None,accountno=None):
        useraccounts = Useraccounts.active.all()
        if name:
            useraccounts = useraccounts.filter(
                    Q(firstname__icontains=name) |
                    Q(middlename__icontains=name) |
                    Q(lastname__icontains=name))
        if email:
            useraccounts = useraccounts.filter(customer__user__email=email)
        if accountno:
            useraccounts = useraccounts.filter(accnt_usr_accnt__accountno=accountno)
        accountlist = []
        for userac in useraccounts:
            accounts = []
            if userac.added_by:
                if userac.added_by.useracc_customer.all() and \
                        userac.added_by.useracc_customer.all()[0].accnt_usr_accnt.all():
                    accounts = userac.added_by.useracc_customer.all()[0].accnt_usr_accnt.all()
            else:
                if userac.accnt_usr_accnt.all():
                    accounts = userac.accnt_usr_accnt.all()
            for account in accounts:
                status = False
                if accountno:
                    if account.accountno == accountno:
                        status = True
                if not accountno or status:
                    account_data = {
                        'customer_name': f'{userac.firstname if userac.firstname else ""} '
                                         f'{userac.middlename if userac.middlename else ""} '
                                         f'{userac.lastname if userac.lastname else ""}',
                        'email': userac.customer.user.email,
                        'accountno': account.accountno,
                        'accountid': account.id,
                        'currency_code': account.currency.code,
                    }
                    accountlist.append(account_data)
        return accountlist

    def get_balance_amount(self,transaction):
        transaction_type = self.get_transaction_type(transaction)
        if transaction_type in ["Inward Remittance", "Other Charges","Refund","Affiliate Fee","Other Charges Fee"]:
            balance_amount = transaction.toaccountbalance
        else:
            try:
                if transaction_type == "International Transfer":
                    if transaction.amount_type == "Wire Transfer Fee":
                        last_transaction = Transactions.active.filter(transactionno=transaction.transactionno,amount_type="Wire Transfer Fee").order_by('-id')[0]
                    elif transaction.amount_type == "Net Amount":
                        last_transaction = Transactions.active.filter(transactionno=transaction.transactionno,amount_type="Net Amount").order_by('-id')[0]
                elif transaction_type == "Wallet Withdrawal Transfer":
                    if transaction.amount_type == "Wallet Withdrawal Fee":
                        last_transaction = Transactions.active.filter(transactionno=transaction.transactionno,amount_type="Wallet Withdrawal Fee").order_by('-id')[0]
                    elif transaction.amount_type == "Net Amount":
                        last_transaction = Transactions.active.filter(transactionno=transaction.transactionno,amount_type="Net Amount").order_by('-id')[0]
                elif transaction_type == "Domestic Transfer":
                    if transaction.amount_type == "Domestic Transfer Fee":
                        last_transaction = Transactions.active.filter(transactionno=transaction.transactionno,amount_type="Domestic Transfer Fee").order_by('-id')[0]
                    elif transaction.amount_type == "Net Amount":
                        last_transaction = Transactions.active.filter(transactionno=transaction.transactionno,amount_type="Net Amount").order_by('-id')[0]
                else:
                    last_transaction = Transactions.active.filter(transactionno=transaction.transactionno).order_by('-id')[0]
                balance_amount = last_transaction.fromaccountbalance
            except Exception as e:
                logger.info(e)
                balance_amount = transaction.fromaccountbalance
        if transaction_type in  ["International Transfer Fee", "Wallet Withdrawal Transfer Fee", "Domestic Transfer Fee"]:
            cable_charge = self.get_transaction_amounts(transaction).get("cable_charge")
            balance_amount -= cable_charge if cable_charge else 0
        if balance_amount:
            balance_amount = format(math.ceil(balance_amount*100)/100,".2f")
        return balance_amount

    def get_debitcredit_amount(self,transaction,accountno):
        if self.is_debit_or_credit(transaction,accountno) == "credit":
            return format(math.ceil(transaction.toamount*100)/100,".2f")
        else:
            return self.get_debit_amount(transaction)

class TransactionMixins:
    def get_affiliate_amount(self,int_transaction):
        try:
            transaction = int_transaction.transaction
            if get_class_name(int_transaction) == "Internationaltransactions":
                wire_fee = Transactions.active.get(transactionno=transaction.transactionno, amount_type="Wire Transfer Fee").fromamount
            elif get_class_name(int_transaction) == "DomesticTransaction":
                wire_fee = Transactions.active.get(transactionno=transaction.transactionno, amount_type="Domestic Transfer Fee").fromamount
        except Exception as e:
            logger.info(e)
            return None
        if wire_fee > 0:
            affiliate_amount = Decimal(wire_fee) * round((transaction.affiliate_fee_percentage/100),2)
            return affiliate_amount
        return None
    
    def get_wallet_withdrawal_affiliate_amount(self,transaction):
        try:
            wallet_fee = Transactions.active.get(transactionno=transaction.transactionno,amount_type="Wallet Withdrawal Fee").fromamount
        except Exception as e:
            logger.info(e)
            return None
        if wallet_fee > 0:
            affiliate_amount = Decimal(wallet_fee) * round((transaction.affiliate_fee_percentage/100),2)
            return affiliate_amount
        return None

class PermissionEmail:
    def send_email_permission(self,recepient_email,user_email):
        subject = 'Requesting your permission'
        template = render_to_string('accounts/openaccount/business/req-permission-email.html',{
            'user_email' : user_email,
            'domain' : settings.CURRENT_DOMAIN
            })
        to_user = recepient_email
        from_user = settings.EMAIL_HOST_USER
        def thread_send_transaction_mail(Subject,template,from_user,to_user):
            email = EmailMessage(Subject,template,from_user,to_user)
            email.content_subtype = 'html'
            email.fail_silently=False
            email.send()
        process_mail = threading.Thread(target=thread_send_transaction_mail,args=(subject,template,from_user,to_user))
        process_mail.start()
        return True

def acc_list(user_acc):
    customer = user_acc.added_by
    account_details =  Accounts.objects.filter(user_account__customer=customer, isdeleted=False).order_by('isprimary')
    return account_details


def add_log_action(request,model_obj,status,status_id,user_id=None):
    try:
        log = LogEntry.objects.log_action(
            user_id=user_id if user_id else request.user.id,
            content_type_id=ContentType.objects.get_for_model(model_obj).pk,
            object_id=model_obj.id,
            object_repr=six.text_type(model_obj),
            change_message=status,
            action_flag=status_id)
    except Exception as e:
        logger.info(f"LogEntry error ->{e}")

class FindAccount:
    def find_master_account_convert_amount(self,debit_account,amount,status):
        logger.info(f"find_master_account_convert_amount, params: currency code :{debit_account.currency}, amount :{amount}, to test master account : {status}")
        if debit_account.currency.code == "EUR":
            credit_account = Accounts.objects.get(user_account__ismaster_account=True,user_account__test_account=status,currency=debit_account.currency,isdeleted=False)
            credit_amount = amount
        else:
            credit_account = Accounts.objects.get(user_account__ismaster_account=True,user_account__test_account=status,currency__code="USD",isdeleted=False)
            currency_conversion = Currencyconversionratescombined.objects.get(fromcurrency__code=debit_account.currency.code,
                                                                          tocurrency__code=credit_account.currency.code, isdeleted=False)
            conversionrate = currency_conversion.conversionrate
            credit_amount = round(Decimal(amount) * conversionrate,2)
            logger.info(f"currency_conversion:{currency_conversion}")
        logger.info(f"find_master_account_convert_amount ends, credit_account:{credit_account},credit_amount:{credit_amount} ")
        return credit_account,credit_amount

    def find_affiliate_usdaccount_convert_amount(self,referred_by_user,currency,amount):
        logger.info(f"find_affiliate_usdaccount_convert_amount, params: referred by: {referred_by_user}, currency:{currency}, amount:{amount}")
        try:
            if referred_by_user.customer.customertype == 1: 
                credit_account = Accounts.active.get(user_account=referred_by_user, currency__code="USD")
            else:
                credit_account = Accounts.active.get(user_account=Useraccounts.active.get(customer=referred_by_user.added_by), currency__code="USD")
            currency_conversion = Currencyconversionratescombined.objects.get(fromcurrency__code=currency.code,
                                                                        tocurrency__code=credit_account.currency.code, isdeleted=False)
            conversionrate = currency_conversion.conversionrate
            credit_amount = round(Decimal(amount) * conversionrate,2)
            logger.info(f"currency_conversion:{currency_conversion}")
        except Exception as e:
            logger.info(f"{e}")
            credit_account = None
            credit_amount = None
        logger.info(f"find_affiliate_usdaccount_convert_amount ends, credit_account: {credit_account}, credit_amount:{credit_amount}")
        return credit_account,credit_amount

    def find_affiliate_account_convert_amount(self,referred_by_user,currency,amount):
        logger.info(f"find_affiliate_account_convert_amount, params: referred by: {referred_by_user}, currency:{currency}, amount:{amount}")
        if currency.code == "EUR":
            try:
                if referred_by_user.customer.customertype == 1:
                    credit_account = Accounts.active.get(user_account=referred_by_user, currency=currency)
                    credit_amount = amount
                else:
                    credit_account = Accounts.active.get(user_account=Useraccounts.active.get(customer=referred_by_user.added_by), currency=currency)
                    credit_amount = amount
            except Exception as e:
                logger.info(f"{e}")
                credit_account, credit_amount = self.find_affiliate_usdaccount_convert_amount(referred_by_user,currency,amount)
        else:
            credit_account, credit_amount = self.find_affiliate_usdaccount_convert_amount(referred_by_user,currency,amount)
        logger.info(f"find_affiliate_account_convert_amount ends, credit_account: {credit_account}, credit_amount:{credit_amount}")
        return credit_account,credit_amount

def checkNonAsciiChracters(input_field):
    if input_field and isinstance(input_field, list):
        if not all(ord(ch) < 128  for input in input_field for ch in input):
            return False
    elif input_field and not all(ord(c) < 128 for c in input_field):
        return False
    return True

def transaction_lock_fn(request,is_lock=True):
    user_account = Useraccounts.active.get(customer__user=request.user)
    message = ""
    status = ""
    if is_lock:
        user_account.transaction_try_count += 0 if user_account.transaction_try_count > 5 else 1
        user_account.save()
        if user_account.transaction_try_count >= 5:
            message = "Transactions has been locked out for 12 hours due to multiple failed otp attempts."
            status = 0
            user_account.transaction_locked_for = datetime.datetime.now() + datetime.timedelta(hours=12)
            user_account.save()
        else:
            message = "Verification failed, wrong user or otp"
            status = 1
    else:
        user_account.transaction_locked_for = None
        user_account.transaction_try_count = 0
        user_account.save()
    return {"message": message, "status": status}


def get_class_name(obj):
    return type(obj).__name__
