from django.contrib.auth.models import User
from rest_framework import permissions
from django.utils import timezone
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication

from api.v1.externalapiauthentication.serializers import ExternalAuthenticationSerializer
from api.v1.mixins import APIV1UtilMixins
from rest_framework.authentication import get_authorization_header
from rest_framework.response import Response
from utils.models import APIaccessToken
from rest_framework import status


def fetch_token_extapi(request):
    auth = get_authorization_header(request).split()
    if not auth:
        exc_resp = {
            'apikey_access_token_header': True
        }
        raise exceptions.AuthenticationFailed(exc_resp)
    if not auth or auth[0].lower() != b'token':
        return None

    if len(auth) == 1:
        exc_resp = {
            'apikey_access_token_header': True
        }
        raise exceptions.AuthenticationFailed(exc_resp)

    elif len(auth) > 2:
        exc_resp = {
            'apikey_access_token_header1': True
        }
        raise exceptions.AuthenticationFailed(exc_resp)
    return auth[1].decode()

class TransactionPermission(permissions.BasePermission):
    """
    Allows access only based on transaction permission.
    """
    message = "tr_permission_denied"
    def has_permission(self, request, view):
        now = timezone.now()
        user_account = request.user.customer_details.all()[0].useracc_customer.all()[0]
        if (user_account.transaction_locked_for and now < user_account.transaction_locked_for):
            return False
        else:
            if user_account.transaction_try_count >= 5:
                user_account.transaction_try_count = 0
                user_account.transaction_locked_for = None
                user_account.save()
            return True


class APIAccessTokenPermissions(BaseAuthentication, APIV1UtilMixins):
    def authenticate(self, request):
        tokens = fetch_token_extapi(request)

        try:
            token_user = APIaccessToken.objects.get(key=tokens)
        except Exception as e:
            exc_resp={

                'apikey_access_token_permission_denied':True
            }
            raise exceptions.AuthenticationFailed(exc_resp)

        return (token_user.user, tokens)

class AccountVerifiedPermission(permissions.BasePermission):

    def has_permission(self, request, view):

        user_account = request.user.customer_details.all()[0].useracc_customer.all()[0]
        if user_account.activestatus == "Verified":
            return True
        else:
            exc_resp = {
                'ext_api_account_verified': True
            }
            raise exceptions.AuthenticationFailed(exc_resp)
class AccountTransactionPermission(permissions.BasePermission):

    def has_permission(self, request, view):

        user_account = request.user.customer_details.all()[0].useracc_customer.all()[0]
        now = timezone.now()
        if (user_account.transaction_locked_for and now < user_account.transaction_locked_for):
            exc_resp = {
                'ext_api_transaction_lock': True
            }
            raise exceptions.AuthenticationFailed(exc_resp)
        else:
            if user_account.transaction_try_count >= 5:
                user_account.transaction_try_count = 0
                user_account.transaction_locked_for = None
                user_account.save()
            return True
class AccountlockedPermission(permissions.BasePermission):

    def has_permission(self, request, view):
        auth_serializer = ExternalAuthenticationSerializer(data=request.data)
        context = {}
        if not auth_serializer.is_valid():
            context["status"] = False
            context["errors"] = auth_serializer.errors
            context["message"] = "Invalid data"
            return Response(context, status=status.HTTP_401_UNAUTHORIZED)
        email = request.data.get("email")
        try:
            user = User.objects.get(email=email)
        except:
            exc_resp = {
                'ext_api_account': True
            }
            raise exceptions.AuthenticationFailed(exc_resp)
        user_account = user.customer_details.all()[0].useracc_customer.all()[0]
        now = timezone.now()
        if (user_account.account_locked_for and now < user_account.account_locked_for):
            exc_resp={
                'ext_api_account_lock':True
            }
            raise exceptions.AuthenticationFailed(exc_resp)
        else:
            if user_account.logintrycount >= 5:
                user_account.logintrycount = 0
                user_account.account_locked_for = None
                user_account.save()
            return True


class AccountlockedPermissionforextapi(permissions.BasePermission):

    def has_permission(self, request, view):


        user_account = request.user.customer_details.all()[0].useracc_customer.all()[0]
        now = timezone.now()
        if (user_account.account_locked_for and now < user_account.account_locked_for):
            exc_resp={
                'ext_api_account_lock1':True
            }
            raise exceptions.AuthenticationFailed(exc_resp)
        else:
            if user_account.logintrycount >= 5:
                user_account.logintrycount = 0
                user_account.account_locked_for = None
                user_account.save()
            return True