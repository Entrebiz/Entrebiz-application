import logging
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from utils.models import Customerdocuments, Documenttypes
from api.v1.documentVerification.serializers import (
    AddressVerificationSerializer,
    CompanyVerificationSerializer,
    CustomerdocumentSerializer,
    DocumenttypeSerializer,
    IdVerificationSerializer,
)

logger = logging.getLogger("lessons")


class AddressVerificationAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        customer_doc = Customerdocuments.active.filter(
            customer__user=request.user, verificationtype__verificationtype=2
        )
        serializer = CustomerdocumentSerializer(customer_doc, many=True)
        content = {"status": 1, "data": serializer.data, "message": "success"}
        return Response(content, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = AddressVerificationSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            content = {"status": 1, "data": {}, "message": "Updated successfully"}
            return Response(content)
        content = {
            "status": 0,
            "error": serializer.errors,
            "message": "validation error",
        }
        return Response(content, status=status.HTTP_200_OK)


class DocumentsTypesAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        customer_doc = Documenttypes.active.all()
        serializer = DocumenttypeSerializer(customer_doc, many=True)
        content = {"status": 1, "data": serializer.data, "message": "success"}
        return Response(content, status=status.HTTP_200_OK)

    def post(self, request):
        description = request.data.get("description")
        customer_doc = Documenttypes.active.filter(description=description)
        serializer = DocumenttypeSerializer(customer_doc, many=True)
        content = {"status": 1, "data": serializer.data, "message": "success"}
        return Response(content, status=status.HTTP_200_OK)


class IdVerificationListAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        customer_doc = Customerdocuments.active.filter(
            customer__user=request.user, verificationtype__verificationtype=1
        )
        serializer = CustomerdocumentSerializer(customer_doc, many=True)
        content = {"status": 1, "data": serializer.data, "message": "success"}
        return Response(content, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = IdVerificationSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            content = {"status": 1, "data": {}, "message": "Updated successfully"}
            return Response(content)
        content = {
            "status": 0,
            "error": serializer.errors,
            "message": "validation error",
        }
        return Response(content, status=status.HTTP_200_OK)


class CompanyVerificationListAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        customer_doc = Customerdocuments.active.filter(
            customer__user=request.user, verificationtype__verificationtype=3
        )
        serializer = CustomerdocumentSerializer(customer_doc, many=True)
        content = {"status": 1, "data": serializer.data, "message": "success"}
        return Response(content, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = CompanyVerificationSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            content = {"status": 1, "data": {}, "message": "Updated successfully"}
            return Response(content)
        content = {
            "status": 0,
            "error": serializer.errors,
            "message": "validation error",
        }
        return Response(content, status=status.HTTP_200_OK)
