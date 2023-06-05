from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status,exceptions

from Transactions.mixins import add_log_action
from api.v1.beneficiary.serializers import InternalbeneficySerializer, ExternalbeneficiarySerializer, \
    AccountBeneficiarySerailizer
from api.v1.externalapibeneficiary.serializers import InternalApibeneficySerializer, ExternalApibeneficiarySerializer, \
    ExternalAPIListbeneficiarySerializer, InternalAPIListbeneficiaryerializer, InternalCreatebeneficySerializer
from api.v1.utils.permissions import APIAccessTokenPermissions
from utils.models import Externalbeneficiaries, Internalbeneficiaries, Accounts, Customers, APIaccessToken
import logging
logger = logging.getLogger('lessons')

class BeneficiaryAPIView(APIView):
    authentication_classes = [APIAccessTokenPermissions]

    def get(self, request):
        user = request.user
        externalbeneficiaries = Externalbeneficiaries.objects.filter(isdeleted=False, customer__user=user)
        serializer1 = ExternalAPIListbeneficiarySerializer(externalbeneficiaries, many=True)
        internalbeneficiaries = Internalbeneficiaries.objects.filter(isdeleted=False, customer__user=user)
        serializer2 = InternalAPIListbeneficiaryerializer(internalbeneficiaries, many=True)
        content = {
            "status": True,
            "data": {
                "external_beneficiary": serializer1.data,
                "internal_beneficiary": serializer2.data,
            },

        }
        return Response(content, status=status.HTTP_200_OK)

class UpdateBeneficiaryAPIView(APIView):
    authentication_classes = [APIAccessTokenPermissions]

    def get_object(self, slug):
        try:
            return 'transaction',Internalbeneficiaries.objects.get(slug=slug, isdeleted=False)
        except Exception as e:
            logger.info(e)
            try:
                return 'international',Externalbeneficiaries.objects.get(slug=slug, isdeleted=False)
            except Exception as e:
                logger.info(e)
                exc_resp = {
                    'ext_api_ben': True
                }
                exception = exceptions.APIException(exc_resp)
                exception.status_code = status.HTTP_404_NOT_FOUND
                raise exception

    def patch(self,request,slug):
        bentype, beneficiary = self.get_object(slug)
        if request.user==beneficiary.createdby:
            if bentype == 'transaction':
                is_company = False
                if beneficiary.account.user_account.customer.customertype == 2:
                    is_company = True
                serializer = InternalApibeneficySerializer(instance=beneficiary,data=request.data,partial=True,context={'request': request,'is_company':is_company})
            elif bentype == 'international':
                serializer = ExternalApibeneficiarySerializer(beneficiary,data=request.data,partial=True,context={'request': request})
            if serializer.is_valid():
                serializer.save()
                content = {
                    "status": True,
                    "data": {
                        "beneficiary": serializer.data,
                    },
                    "message": "beneficiary successfully updated!"
                }
                return Response(content,status=status.HTTP_200_OK)
            content = {
                    "status": False,
                    "error": serializer.errors,
                    "message" : "validation error"
                }
            return Response(content, status=status.HTTP_404_NOT_FOUND)
        else:
            content = {
                "status": False,
                "message": "beneficiary not found"
            }
            return Response(content, status=status.HTTP_404_NOT_FOUND)


class DeleteBeneficiaryAPIView(APIView):
    authentication_classes = [APIAccessTokenPermissions]

    def get_object(self, slug):
        try:
            return 'transaction',Internalbeneficiaries.objects.get(slug=slug, isdeleted=False)
        except Exception as e:
            logger.info(e)
            try:
                return 'international',Externalbeneficiaries.objects.get(slug=slug, isdeleted=False)
            except Exception as e:
                logger.info(e)
                exc_resp = {
                    'ext_api_ben': True
                }
                exception = exceptions.APIException(exc_resp)
                exception.status_code = status.HTTP_404_NOT_FOUND
                raise exception
    def delete(self,request,slug):
        bentype, beneficiary = self.get_object(slug)
        if request.user==beneficiary.createdby:
            if bentype == 'transaction':
                    beneficiary.isdeleted = True
                    beneficiary.save()
                    add_log_action(request, beneficiary, status=f"beneficiary account(account to account transfer) {beneficiary.account.accountno} deleted", status_id=3)
            elif bentype == 'international':
                    beneficiary.isdeleted = True
                    beneficiary.save()
                    add_log_action(request, beneficiary, status=f"beneficiary account(international wire transfer) {beneficiary.accountnumber} deleted", status_id=3)
            content = {
                    "status": True,
                    "message": "beneficiary successfully deleted!"
                }
            return Response(content,status=status.HTTP_200_OK)
        else:
            content = {
                "status": False,
                "message": "beneficiary not found"
            }
            return Response(content, status=status.HTTP_404_NOT_FOUND)

class BeneficiaryCreateAPIView(APIView):
    authentication_classes = [APIAccessTokenPermissions]

    def post(self, request):
        ben_type = request.data.get("beneficiary_type")
        user_type = request.data.get("user_type")
        if request.data.get("type") == 'from_transaction':
            serializer = AccountBeneficiarySerailizer(data=request.data)
            if serializer.is_valid():
                account_number = request.data.get("account_number")
                nickname = request.data.get("nick_name")
                try:
                    account = Accounts.objects.get(accountno=account_number, isdeleted=False)
                    customer = Customers.objects.get(user=request.user)
                    nick_name = nickname
                except Exception as e:
                    context = {
                        'status': False,
                        'message': 'receiver Account number not exist'
                    }
                    return Response(context,status=status.HTTP_404_NOT_FOUND)
                try:
                    if Internalbeneficiaries.objects.filter(createdby=request.user,
                                                            receivername=nick_name, isdeleted=False).exists():
                        context = {
                            'status': False,
                            'message': 'nick name already exist'
                        }
                    elif Internalbeneficiaries.objects.filter(account=account, createdby=request.user,
                                                              isdeleted=False).exists():
                        context = {
                            'status': False,
                            'message': 'beneficiary already exist'
                        }
                    return Response(context,status=status.HTTP_404_NOT_FOUND)
                except Exception as e:
                    logger.info(e)
                    pass
                internal_ben = Internalbeneficiaries.objects.create(receivername=nick_name,
                                                                    account=account, createdby=request.user,
                                                                    customer=customer)
                context = {
                    'status': True,
                    'message': 'beneficiary added successfully'
                }
                return Response(context,status=status.HTTP_200_OK)
            else:
                context = {
                    'status': False,
                    'errors': serializer.errors,
                    'message': 'Validation error'
                }
                return Response(context,status=status.HTTP_404_NOT_FOUND)
        else:
            if ben_type == "internal":
                if not user_type:
                    context = {
                        "status": False,
                        "error": {
                            "user_type": [
                                "This field may not be blank."
                            ]
                        },
                        "message": "Invalid data"
                    }
                    return Response(context,status=status.HTTP_404_NOT_FOUND)
                serializer = InternalCreatebeneficySerializer(data=request.data,
                                                        context={'request': request, 'user_type': user_type,
                                                                 'nick_name_check': True})
            elif ben_type == "international":
                serializer = ExternalbeneficiarySerializer(data=request.data,
                                                           context={'request': request, 'beneficiary_check': True})
            elif ben_type == "":
                serializer = ExternalbeneficiarySerializer(data=request.data,
                                                           context={'request': request, 'beneficiary_check': True})
            else:
                content = {
                    "status": False,
                    "error": {
                        "beneficiary_type":" Invalid beneficiary type!"
                    },
                    "message": "validation error"

                }
                return Response(content,status=status.HTTP_404_NOT_FOUND)
            if serializer.is_valid():
                serializer.save()
                content = {
                    "status": True,
                    "data": {
                        "beneficiary": serializer.data,
                    },

                }
                return Response(content)
        content = {
            "status": False,
            "error": serializer.errors,
            "message": "validation error"
        }
        return Response(content, status=status.HTTP_404_NOT_FOUND)