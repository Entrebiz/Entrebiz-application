from rest_framework.response import Response
from rest_framework import status, exceptions
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from Transactions.mixins import add_log_action
from utils.models import Internalbeneficiaries, Externalbeneficiaries, Accounts, Customers
from api.v1.beneficiary.serializers import ExternalbeneficiarySerializer, InternalbeneficySerializer, \
    AccountBeneficiarySerailizer
import logging
logger = logging.getLogger('lessons')


class BeneficiaryListAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self,request):
        user = request.user
        externalbeneficiaries = Externalbeneficiaries.objects.filter(isdeleted=False,customer__user=user)
        serializer1 = ExternalbeneficiarySerializer(externalbeneficiaries, many=True)
        internalbeneficiaries = Internalbeneficiaries.objects.filter(isdeleted=False,customer__user=user)
        serializer2 = InternalbeneficySerializer(internalbeneficiaries, many=True)
        content = {
            "status": 1,
            "data": {
                "EnternalBeneficiary": serializer1.data,
                "InternalBeneficiary": serializer2.data,
            },
            "message": "success"
        }
        return Response(content, status=status.HTTP_200_OK)
    


class UpdateORDeleteBeneficiaryAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
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
                    'message': 'Beneficiary not found',
                }
                exception = exceptions.APIException(exc_resp)
                exception.status_code = status.HTTP_200_OK
                raise exception

    def patch(self,request,slug):
        bentype, beneficiary = self.get_object(slug)
        if bentype == 'transaction':
            is_company = False
            if beneficiary.account.user_account.customer.customertype == 2:
                is_company = True
            serializer = InternalbeneficySerializer(instance=beneficiary,data=request.data,partial=True,context={'request': request,'is_company':is_company})
        elif bentype == 'international':
            serializer = ExternalbeneficiarySerializer(beneficiary,data=request.data,partial=True,context={'request': request})
        if serializer.is_valid():
            serializer.save()
            content = {
                "status": 1,
                "data": {
                    "Beneficiary": serializer.data,
                },
                "message": "Beneficiary Successfully Updated!"
            }
            return Response(content)
        content = {
                "status": 0,
                "error": serializer.errors,
                "message" : "validation error"
            }
        return Response(content, status=status.HTTP_200_OK)
    def delete(self,request,slug):
        bentype, beneficiary = self.get_object(slug)
        if bentype == 'transaction':
                beneficiary.isdeleted = True
                beneficiary.save()
                add_log_action(request, beneficiary, status=f"beneficiary account(account to account transfer) {beneficiary.account.accountno} deleted", status_id=3)
        elif bentype == 'international':
                beneficiary.isdeleted = True
                beneficiary.save()
                add_log_action(request, beneficiary, status=f"beneficiary account(international wire transfer) {beneficiary.accountnumber} deleted", status_id=3)
        content = {
                "status": 1,
                "data": {},
                "message": "Beneficiary Successfully Deleted!"
            }
        return Response(content)

class CreateBeneficiaryAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        ben_type = request.data.get("beneficiary_type")
        user_type = request.data.get("user_type")
        account_type = request.data.get("account_type")
        if request.data.get("type") == 'from_transaction':
            serializer=AccountBeneficiarySerailizer(data=request.data)
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
                        'message': 'Receiver Account number not exist'
                    }
                    return Response(context)
                try:
                    if Internalbeneficiaries.objects.filter(createdby=request.user,
                                                            receivername=nick_name, isdeleted=False).exists():
                        context = {
                            'status': False,
                            'message': 'Nick name already exist'
                        }
                    elif Internalbeneficiaries.objects.filter(account=account, createdby=request.user,
                                                              isdeleted=False).exists():
                        context = {
                            'status': False,
                            'message': 'Beneficiary already exist'
                        }
                    return Response(context)
                except Exception as e:
                    logger.info(e)
                    pass
                internal_ben = Internalbeneficiaries.objects.create(receivername=nick_name,
                                                                    account=account, createdby=request.user,
                                                                    customer=customer)
                context = {
                    'status': True,
                    'message': 'Beneficiary added successfully'
                }
                return Response(context)
            else:
                context={
                    'status':False,
                    'errors':serializer.errors,
                    'message':'Validation error'
                }
                return Response(context)
        else:
            if ben_type == "transaction":
                serializer = InternalbeneficySerializer(data=request.data,context={'request': request,'user_type':user_type,'nick_name_check':True})
            else:
                serializer = ExternalbeneficiarySerializer(data=request.data,context={'request': request,'beneficiary_check':True})
            if serializer.is_valid():
                serializer.save()
                content = {
                    "status": 1,
                    "data": {
                        "Beneficiary": serializer.data,
                    },
                    "message": "Beneficiary Successfully Added!"
                }
                return Response(content)
        content = {
                "status": 0,
                "error": serializer.errors,
                "message" : "validation error"
            }
        return Response(content, status=status.HTTP_200_OK)