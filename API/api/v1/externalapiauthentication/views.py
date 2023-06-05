from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils.crypto import get_random_string


from api.v1.externalapiauthentication.serializers import (ExternalAuthenticationSerializer,)
from api.v1.utils.permissions import APIAccessTokenPermissions, AccountlockedPermission
from utils.models import Apiaccesskeygenerate, APIaccessToken
from rest_framework import status




class ExternalAuthenticationAPIView(APIView):
    permission_classes = [AccountlockedPermission]
    def post(self, request):
        context = {}
        serializer = ExternalAuthenticationSerializer(data=request.data)
        if serializer.is_valid():
            email = request.data.get("email")
            apikey = request.data.get("apikey")
            if email:
                try:
                    user = User.objects.get(email=email)
                except:
                    context = {
                        "status": False,
                        "errors":{
                            "email":"Account doesn't exits",
                        },
                        "message": "validation error",
                    }
                    return Response(context,status=status.HTTP_401_UNAUTHORIZED)
                if user:
                    try:
                        apiaccesuser = Apiaccesskeygenerate.objects.get(user__email=user,apikey=apikey)
                    except:
                        context = {
                            "status": False,
                            "errors": {
                                "apikey": "Invalid apikey",
                            },
                            "message": "validation error",
                        }
                        return Response(context,status=status.HTTP_401_UNAUTHORIZED)
                    if apiaccesuser:
                        api_access_token,show = APIaccessToken.objects.get_or_create(user=apiaccesuser.user)
                        if show: #if status is True. ie; the row is just now created
                            api_access_token.key = get_random_string(length=86)
                            api_access_token.save()
                        token = api_access_token.key
                        context = {
                            "token": token,
                        }
                    return Response(context,status=status.HTTP_200_OK)
        else:
            context["status"] = False
            context["errors"] = serializer.errors
            context["message"] = "Invalid data"
            return Response(context,status=status.HTTP_401_UNAUTHORIZED)