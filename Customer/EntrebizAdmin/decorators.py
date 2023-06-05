import logging

from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template import RequestContext
from django.utils import timezone

from utils.models import Customers, Useraccounts

logger = logging.getLogger('lessons')


def allowed_users(admin_type=[]):
    def decorator(view_func):
        def wrapper_func(request, *args, **kwargs):
            try:
                user = request.user.adminacc_created_by
            except Exception as e:
                logger.info(e)
                return HttpResponse('You are not authorized to view this page')
            # group = None
            # if user:
            admin_group = user.admin_level
            admin_permission = user.approval_level
            if admin_group in admin_type or admin_permission in admin_type:
                return view_func(request, *args, **kwargs)
            else:
                return HttpResponse('You are not authorized to view this page')
        return wrapper_func
    return decorator


def admin_only(view_func):
    def wrapper_function(request, *args, **kwargs):
        try:
            user = request.user.adminacc_created_by
        except Exception as e:
            logger.info(e)
            return HttpResponse('You are not authorized to view this page')
        # group = None
        # if user:
        group = user.admin_level

        if group in ['Admin','Super Admin'] :
            return view_func(request, *args, **kwargs)
        else:
            return HttpResponse('You are not authorized to view this page')
    return wrapper_function


def template_decorator(title):
    def wrapper(view_func):
        def call(request, *args, **kwargs):
            template = 'accounts/openaccount/business/template_dec.html'
            current_customer = Customers.objects.get(user=request.user)
            if current_customer.customertype == 2:
                current_user_acc = Useraccounts.objects.get(customer__user = request.user)
                if (current_user_acc.account_tran_status or current_user_acc.ultimate_ben_user) and current_user_acc.activestatus == "Verified":
                    return view_func(request, *args, **kwargs)
                else:
                    return render(request,template,{'title':title})
            else:
                current_user_acc = Useraccounts.objects.get(customer__user = request.user)
                if current_user_acc.activestatus == 'Verified':
                    return view_func(request, *args, **kwargs)
                else:
                    return render(request,template,{'title':title})
        return call
    return wrapper



def superuser_only(view_func):
    def wrapper_function(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        else:
            return HttpResponse('You are not authorized to view this page')
    return wrapper_function

def transaction_status(view_func):
    def wrapper_function(request, *args, **kwargs):
        now = timezone.now()
        user_account = request.user.customer_details.all()[0].useracc_customer.all()[0]
        if (user_account.transaction_locked_for and now < user_account.transaction_locked_for):
            return render(request, "common/restrict-transaction.html")
        else:
            if user_account.transaction_try_count >= 5:
                user_account.transaction_try_count = 0
                user_account.transaction_locked_for = None
                user_account.save()
            return view_func(request, *args, **kwargs)
    return wrapper_function