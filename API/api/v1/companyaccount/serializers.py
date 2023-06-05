import datetime
from Transactions.mixins import checkNonAsciiChracters

from rest_framework import serializers
from utils.models import Businessdetails, Countries, Industrytypes, Otps

import logging

logger = logging.getLogger("lessons")


class CompanyDetailsSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["company_name"] = instance.companyname
        representation["industry_type"] = instance.industrytype.name
        representation["url"] = instance.url
        representation["country"] = instance.company_country.name
        representation["address"] = instance.address
        representation["city"] = instance.city
        representation["state"] = instance.state
        representation["phonenumber"] = instance.phonenumber
        representation["country_code"] = instance.country_code.phonecode
        representation["is_country_of_incorporation_deleted"] = instance.company_country.isdeleted
        representation["is_phonecode_deleted"] = instance.country_code.isdeleted
        return representation

    class Meta:
        model = Businessdetails
        fields = ["id"]


class OtpSerializer(serializers.Serializer):
    otp = serializers.CharField()

    def validate(self, data):
        otp = data.get("otp")
        transactiontype = self.context["transactiontype"]
        token = self.context["token"]
        user = self.context["user"]
        try:
            otp_obj = Otps.objects.get(
                code=otp, token=token, transactiontype=transactiontype, createdby=user
            )
        except Exception as e:
            logger.info(e)
            raise serializers.ValidationError(
                {"otp": "verification failed, wrong user or otp"}
            )
        if otp_obj.validated:
            raise serializers.ValidationError(
                {"otp": "verification failed, already validated"}
            )
        elif otp_obj.validtill < datetime.datetime.now().date():
            raise serializers.ValidationError(
                {"otp": "verification failed, otp expired"}
            )
        return data

    def save(self):
        otp = self.validated_data["otp"]
        transactiontype = self.context["transactiontype"]
        token = self.context["token"]
        user = self.context["user"]
        otp_obj = Otps.objects.get(
            code=otp, token=token, transactiontype=transactiontype, createdby=user
        )
        otp_obj.validated = True
        otp_obj.save()


class CompanyDetailsUpdateSerializer(serializers.Serializer):
    company_name = serializers.CharField()
    industry_type = serializers.CharField()
    url = serializers.CharField()
    country = serializers.CharField()
    address = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    phonenumber = serializers.CharField()
    country_code = serializers.CharField()

    def validate(self, data):
        company_name = data.get("company_name")
        url = data.get("url")
        address = data.get("address")
        city = data.get("city")
        state = data.get("state")
        phonenumber = data.get("phonenumber")
        if not checkNonAsciiChracters(company_name):
            raise serializers.ValidationError(
                {"company_name": "Fancy characters are not allowed"}
            )
        elif not checkNonAsciiChracters(url):
            raise serializers.ValidationError(
                {"url": "Fancy characters are not allowed"}
            )
        elif not checkNonAsciiChracters(address):
            raise serializers.ValidationError(
                {"address": "Fancy characters are not allowed"}
            )
        elif not checkNonAsciiChracters(city):
            raise serializers.ValidationError(
                {"city": "Fancy characters are not allowed"}
            )
        elif not checkNonAsciiChracters(state):
            raise serializers.ValidationError(
                {"state": "Fancy characters are not allowed"}
            )
        elif not checkNonAsciiChracters(phonenumber):
            raise serializers.ValidationError(
                {"phonenumber": "Fancy characters are not allowed"}
            )
        return data

    def save(self):
        user = self.context["user"]
        company_name = self.validated_data["company_name"]
        industry_type = self.validated_data["industry_type"]
        url = self.validated_data["url"]
        country = self.validated_data["country"]
        address = self.validated_data["address"]
        city = self.validated_data["city"]
        state = self.validated_data["state"]
        phonenumber = self.validated_data["phonenumber"]
        country_code = self.validated_data["country_code"]
        Businessdetails.objects.filter(createdby=user).update(
            companyname=company_name,
            industrytype=Industrytypes.objects.get(name=industry_type),
            url=url,
            address=address,
            phonenumber=phonenumber,
            country_code=Countries.objects.filter(phonecode=country_code).first(),
            company_country=Countries.objects.filter(name=country).first(),
            city=city,
            state=state,
        )
