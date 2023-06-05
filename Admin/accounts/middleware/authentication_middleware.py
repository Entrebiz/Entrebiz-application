from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import logout

excluded_paths = ['/twoStepVerification','/login','/logout']


class TwoFactorValidateMiddleware(MiddlewareMixin):

    def process_request(self, request):
        if request.path not in excluded_paths and request.session.get('isTwoStepPassed') == 0:
            return redirect('/twoStepVerification')

class UserStatusMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_authenticated and request.user.customer_details.all():
            user_acc = request.user.customer_details.all()[0].useracc_customer.all()[0]
            is_deleted = user_acc.isdeleted
            is_locked = user_acc.islocked
            is_rejected = True if user_acc.activestatus == 'Rejected' else False
            is_suspended = True if user_acc.activestatus == 'Suspended' else False
            is_deactivated_by_ubo = True if user_acc.activestatus == 'Deactivated by UBO' else False
            if is_deleted or is_locked or is_rejected or is_suspended or is_deactivated_by_ubo:
                logout(request)
                return redirect('/login')