import json
import logging
from django.views import View
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.http import JsonResponse

from decimal import Decimal
from Transactions.mixins import ModelQueries, SendAddMoneySuccessMailtoUser, add_log_action
from EntrebizAdmin.decorators import allowed_users, admin_only
from utils.models import Accounts, Businessdetails, Inwardremittancetransactions, Transactions, Transactiontypes, Useraccounts
logger = logging.getLogger('lessons')

@method_decorator(login_required, name='dispatch')
@method_decorator(admin_only,name='dispatch')
@method_decorator(allowed_users(admin_type=['Inputter']),name='dispatch')
class InwardRemittanceStatus(View,ModelQueries):
    def get(self, request):
        inwardrem_trs = Inwardremittancetransactions.objects.filter(isdeleted=False).order_by('-id')
        inwardrem_trs = self.paginate(inwardrem_trs, page=1,
                                      per_page=100)
        context = {
            'inwardrem_trs' : inwardrem_trs
        }
        return render(request,'inward-remittance-status/inward-remittance-list.html',context)
    def post(self, request):
        inwardrem_trs = Inwardremittancetransactions.objects.filter(isdeleted=False).order_by('-id')
        inwardrem_trs = self.paginate(inwardrem_trs, page=request.POST.get("page", 1),
                                        per_page=100)
        context = {'inwardrem_trs' : inwardrem_trs}
        action_type = request.POST.get('action_type')
        if action_type == 'filterinwardremitance':
            template = render_to_string('inward-remittance-status/inward-remittance-list-table.html', context)
            response = {'inwardrem_data': template, }
            return JsonResponse(response)

@method_decorator(login_required, name='dispatch')
@method_decorator(admin_only,name='dispatch')
@method_decorator(allowed_users(admin_type=['Approver','Inputter / Approver']),name='dispatch')
class InwardRemittancePending(View,SendAddMoneySuccessMailtoUser,ModelQueries):
    def get(self, request):
        slug = request.GET.get('slug')
        if slug:
            inwardrem_tr = Inwardremittancetransactions.objects.get(slug=slug,isdeleted=False)
            context = {
            'inwardrem_tr' : inwardrem_tr
            }
            return render(request,'inward-remittance-approval/inward-remittance-pending-view.html',context)
        inwardrem_trs = Inwardremittancetransactions.objects.filter(isdeleted=False).order_by('-id')
        inwardrem_trs = self.paginate(inwardrem_trs, page=1,
                                      per_page=100)
        context = {
            'inwardrem_trs' : inwardrem_trs
        }
        return render(request,'inward-remittance-approval/inward-remittance-approval.html',context)
    def post(self, request):
        inwardrem_trs = Inwardremittancetransactions.objects.filter(isdeleted=False).order_by('-id')
        inwardrem_trs = self.paginate(inwardrem_trs, page=request.POST.get("page", 1),
                                        per_page=100)
        context = {'inwardrem_trs' : inwardrem_trs}
        action_type = request.POST.get('action_type')
        if action_type == 'approve_confirm':
            def validate():
                if not request.POST.get('InwardRemittanceIds'):
                    return {
                        'status' : False,
                        'message' : 'Something went wrong'
                    }
                InwardRemittanceIds = json.loads(request.POST.get('InwardRemittanceIds'))
                counter = 0
                for InwardRemittanceId in InwardRemittanceIds:
                    inwardrem_tr = Inwardremittancetransactions.objects.get(id=InwardRemittanceId,isdeleted=False)
                    account_no = inwardrem_tr.account.accountno
                    account = Accounts.objects.get(accountno=account_no)
                    amount = inwardrem_tr.amount
                    inwardrem_tr.approvallevel = 1
                    inwardrem_tr.modifiedby = request.user
                    if inwardrem_tr.transactiontype.name == 'Inward Remittance':
                        transactiontype = Transactiontypes.objects.get(name='Inward Remittance')
                        account.balance = account.balance + Decimal(amount)
                        account.save()
                        add_log_action(request, account, status=f"amount of {amount} {account.currency.code} has been credited to account '{account.accountno}'", status_id=2)
                        message = 'Amount Added Successfully'
                        counter +=1
                    elif inwardrem_tr.transactiontype.name == 'Other Charges':
                        transactiontype = Transactiontypes.objects.get(name='Other Charges')
                        account.balance = account.balance - Decimal(amount)
                        account.save()
                        add_log_action(request, account, status=f"charge of {amount} {account.currency.code} has been debited from account '{account.accountno}'", status_id=2)
                        message = 'Charges debited successfully'
                        counter +=1
                    try:
                        last_transactionno = Transactions.objects.latest('transactionno').transactionno
                    except Exception as e:
                        logger.info(e)
                        last_transactionno = 10000000
                    transaction_obj = Transactions.objects.create(
                    transactionno=int(last_transactionno) + 1,
                    toaccount=account,
                    fromamount=amount,
                    toamount=amount,
                    initiatedby=request.user,
                    transactiontype=transactiontype,
                    createdby=request.user,
                    note=inwardrem_tr.comment,
                    toaccountbalance=account.balance,
                    )
                    add_log_action(request, transaction_obj, status=f"transaction(Inward Remittance) created for account {str(transaction_obj.toaccount.accountno)}", status_id=1)
                    inwardrem_tr.transaction=transaction_obj
                    inwardrem_tr.save()
                    if inwardrem_tr.transactiontype.name == 'Inward Remittance':
                        user_account = inwardrem_tr.account.user_account
                        curr_code = inwardrem_tr.currency.code
                        if user_account.added_by:
                            try:
                                company_detials = Businessdetails.objects.get(customer=user_account.customer, isdeleted=False)
                                company_customers = Useraccounts.objects.filter(customer__bsnssdtls_cstmr__companyname=company_detials.companyname, 
                                account_tran_status=True, activestatus='Verified')
                                for useracc in company_customers:
                                    full_name = f"{useracc.firstname} {useracc.lastname}"
                                    sendermail=useracc.customer.user.email
                                    self.send_mail(full_name,round(amount,2),curr_code,'Your Account has been credited',sendermail)
                            except Exception as e:
                                logger.info(e)

                        full_name = f"{user_account.firstname} {user_account.lastname}"
                        sendermail=user_account.customer.user.email
                        self.send_mail(full_name,round(amount,2),curr_code,'Your Account has been credited',sendermail)
                return {
                    'status' : True,
                    'message' : message if counter<2 else 'Approved Successfully'
                }
            data = validate()
            if data.get('status'):
                context['status'] = True
                context['message'] = data.get('message')
            else:
                context['status'] = False
                context['message'] = data.get('message')
        elif action_type == 'rejectInwardRemittance':
            InwardRemittanceId = request.POST.get('InwardRemittanceId')
            ReasonForReject = request.POST.get('ReasonForReject')
            def validate():
                if not InwardRemittanceId:
                    return {
                        'status' : False,
                        'message' : 'Something went wrong'
                    }
                elif not ReasonForReject:
                    return {
                        'status' : False,
                        'message' : 'Reason for rejection is required'
                    }
                try:
                    inwardrem_tr = Inwardremittancetransactions.objects.get(id=InwardRemittanceId,isdeleted=False)
                    inwardrem_tr.modifiedby = request.user
                    inwardrem_tr.reasonforreject = ReasonForReject
                    inwardrem_tr.approvallevel = 2
                    inwardrem_tr.save()
                    add_log_action(request, inwardrem_tr, status=f"inward remttance of debit/credit amount of {inwardrem_tr.amount} {inwardrem_tr.currency.code} has been rejected due to '{inwardrem_tr.reasonforreject}'", status_id=3)
                except Exception as e:
                    logger.info(e)
                    return {
                        'status' : False,
                        'message' : 'Something went wrong'
                    }
                return {
                    'status' : True,
                }
            data = validate()
            if data.get('status'):
                context['status'] = True
                context['message'] = 'Inward Remittance Rejected Successfully'
            else:
                context['status'] = False
                context['message'] = data.get('message')
        elif action_type == 'filterinwardremitance':
            template = render_to_string('inward-remittance-approval/inward-remittance-approval-table.html', context)
            response = {'inwardrem_data': template, }
            return JsonResponse(response)
        return render(request,'inward-remittance-approval/inward-remittance-approval.html',context)