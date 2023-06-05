# custom handler
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        if response.data.get('detail'):
            response.data['message'] = response.data.pop("detail")
        if response.data.get("is_auth"):
            response.data['status'] = int(response.data.get('status'))
            del response.data['is_auth']
        elif response.data.get('is_lock_api'):
            response.data['status'] = int(response.data.get('status'))
            del response.data['is_lock_api']
        else:
            response.data['status'] = 0
        response.data['data'] = None
        if response.data.get('message') == "tr_permission_denied":
            response.data['message'] = "Transactions has been locked out for 12 hours due to multiple failed otp attempts."
            response.data['status'] = 3
        if response.data.get('ext_api_ben'):
            response.data['status'] = False
            response.data['data'] = {}
            response.data['message'] = "beneficiary not found"
            del response.data['ext_api_ben']
        if response.data.get('ext_api_account'):
            response.data['status'] = False
            response.data['errors'] = {"email":"Account doesn't exits"}
            response.data['message'] = "validation error"
            del response.data['data']
            del response.data['ext_api_account']
        if response.data.get('ext_api_account_lock'):
            response.data['status'] = False
            response.data['data'] = {}
            response.data['message'] = "Your account has been locked out for 12 hours due to multiple failed login attempts."
            del response.data['ext_api_account_lock']
        if response.data.get('ext_api_account_lock1'):
            response.data['status'] = False
            response.data['data'] = {}
            response.data['message'] = "You will not be able to make any transactions for the next 12 hours as your account has been locked."
            del response.data['ext_api_account_lock1']
        if response.data.get('ext_api_transaction_lock'):
            response.data['status'] = False
            response.data['data'] = {}
            response.data['message'] = "Transactions has been locked out for 12 hours due to multiple failed otp attempts."
            del response.data['ext_api_transaction_lock']
        if response.data.get('ext_api_account_verified'):
            response.data['status'] = False
            response.data['data'] = {}
            response.data['message'] = "You are not allowed to access this feature without completing your registration process."
            del response.data['ext_api_account_verified']
        if response.data.get('apikey_access_token_header'):
            response.data['status'] = False
            response.data['data'] = {}
            response.data['message'] = "Authentication credentials were not provided."
            del response.data['apikey_access_token_header']
        if response.data.get('apikey_access_token_header1'):
            response.data['status'] = False
            response.data['data'] = {}
            response.data['message'] = "Invalid token header. No credentials provided."
            del response.data['apikey_access_token_header1']
        if response.data.get('apikey_access_token_permission_denied'):
            response.data['status'] = False
            response.data['data'] = {}
            response.data['message'] = "Invalid token"
            del response.data['apikey_access_token_permission_denied']
    return response