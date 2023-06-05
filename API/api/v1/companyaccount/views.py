from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from api.v1.companyaccount.serializers import (
    CompanyDetailsSerializer,
    CompanyDetailsUpdateSerializer,
    OtpSerializer,
)
from api.v1.mixins import APIV1UtilMixins
from utils.models import Businessdetails, Useraccounts
from Transactions.mixins import OTP

import logging

logger = logging.getLogger("lessons")


class CompanyDetailsAPIView(APIView, APIV1UtilMixins, OTP):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        business_details = Businessdetails.objects.get(
            customer__user=request.user, isdeleted=False
        )
        serializer = CompanyDetailsSerializer(business_details)
        content = {"status": 1, "data": serializer.data, "message": "success"}
        return Response(content)

    def post(self, request):
        content = {"status": 1, "data": {}, "message": ""}
        if (
            request.data.get("action_type") == "send_otp"
            or request.data.get("action_type") == "resend_otp"
        ):
            token = self.fetch_token(request)
            user_account = Useraccounts.objects.get(customer__user=request.user)
            full_name = f"{user_account.firstname} {user_account.lastname}"
           
            if otp_send_status:
                if request.data.get("action_type") == "send_otp":
                    message = "OTP sent, Please verify!"
                elif request.data.get("action_type") == "resend_otp":
                    message = "OTP resent, Please verify!"
                content["message"] = message
            else:
                content["status"] = 0
                content["message"] = "something went wrong"
        elif request.data.get("action_type") == "otp_validation":
            token = self.fetch_token(request)
            transactiontype = "Update Company Details"
            serializer = OtpSerializer(
                data=request.data,
                context={
                    "token": token,
                    "transactiontype": transactiontype,
                    "user": request.user,
                },
            )
            if serializer.is_valid():
                serializer.save()
                business_details = Businessdetails.objects.get(
                    customer__user=request.user, isdeleted=False
                )
                serializer = CompanyDetailsSerializer(business_details)
                content["data"] = serializer.data
                content["message"] = "success"
            else:
                content = {
                    "status": 0,
                    "error": serializer.errors,
                    "message": "validation error",
                }
        return Response(content)

    def patch(self, request):
        user = request.user
        user_account = Useraccounts.active.get(customer__user=request.user)
        if user_account.added_by:
            user = user_account.added_by.user
        serializer = CompanyDetailsUpdateSerializer(
            data=request.data, context={"user": user}
        )
        if serializer.is_valid():
            serializer.save()
            content = {
                "status": 1,
                "data": serializer.data,
                "message": "Updated successfully",
            }
        else:
            content = {
                "status": 0,
                "error": serializer.errors,
                "message": "validation error",
            }
        return Response(content, status=status.HTTP_200_OK)
