import datetime
from shutil import ExecError
from entrebiz import settings
from django.utils import timezone
from rest_framework import exceptions
from rest_framework.authentication import get_authorization_header

from utils.models import Useraccounts, Apiaccesskeygenerate
from django.utils.crypto import get_random_string



class APIV1UtilMixins:

    def fetch_token(self,request):
        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != b'token':
            return None

        if len(auth) == 1:
            msg = 'Invalid token header. No credentials provided.'
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = 'Invalid token header. Token string should not contain sssspaces.'
            raise exceptions.AuthenticationFailed(msg)
        return auth[1].decode()

    def hide_characters(self, string):
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

    def add_apiuser(self,user):

        try:
            api = Apiaccesskeygenerate.objects.get(user=user)
        except:
            api = Apiaccesskeygenerate.objects.create(user=user, apikey=get_random_string(length=16))

        return api

    def transaction_lockedforapi(self,user_account):
        now = timezone.now()
        if user_account.transaction_locked_for and now < user_account.transaction_locked_for:
            return True
        else:
            return False