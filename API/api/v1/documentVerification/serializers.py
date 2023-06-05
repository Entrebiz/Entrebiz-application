import os
import logging
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from rest_framework import serializers

from Transactions.mixins import checkNonAsciiChracters
from utils.models import (
    Businessdetails,
    Customerdocumentdetails,
    Customerdocumentfiles,
    Customerdocuments,
    Customers,
    Documentfields,
    Documenttypes,
    Documenttypesforverification,
    Useraccounts,
)

logger = logging.getLogger("lessons")


class CustomerdocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customerdocuments
        fields = ["id"]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.verificationtype.verificationtype == 2:
            document_type = Customerdocumentdetails.objects.get(
                customerdocument=instance
            ).customerdocument.documenttype.name
            field_name = Customerdocumentdetails.objects.get(
                customerdocument=instance
            ).field.fieldname
            value = Customerdocumentdetails.objects.get(customerdocument=instance).value
            representation["document_type"] = document_type
            representation[field_name] = value
        elif instance.verificationtype.verificationtype == 1:
            if instance.documenttype.name == "Passport":
                representation["document_type"] = "Passport"
                representation["document_number"] = Customerdocumentdetails.objects.get(
                    customerdocument=instance,
                    field__fieldname="Passport Number",
                ).value
                representation["Valid To"] = Customerdocumentdetails.objects.get(
                    customerdocument=instance, field__fieldname="Validity"
                ).value

            elif instance.documenttype.name == "Driving License":
                representation["document_type"] = "Driving License"
                representation["document_number"] = Customerdocumentdetails.objects.get(
                    customerdocument=instance,
                    field__fieldname="Driving License Number",
                ).value
                representation["Valid To"] = Customerdocumentdetails.objects.get(
                    customerdocument=instance, field__fieldname="Valid To"
                ).value

            elif instance.documenttype.name == "ID Card":
                representation["document_type"] = "ID Card"
                representation["document_number"] = Customerdocumentdetails.objects.get(
                    customerdocument=instance, field__fieldname="ID Card Number"
                ).value
                representation["Valid To"] = None

            elif instance.documenttype.name == "Other":
                representation["document_type"] = "Other"
                representation["document_number"] = Customerdocumentdetails.objects.get(
                    customerdocument=instance,
                    field__fieldname="ID Proof Number",
                ).value
                representation["Valid To"] = None
            if Customerdocumentfiles.objects.filter(
                customerdocument=instance, document_type="additionalPage"
            ).exists():
                representation["additional_file"] = True
            else:
                representation["additional_file"] = False
            
        elif instance.verificationtype.verificationtype == 3:
            document_details = Customerdocumentdetails.objects.filter(
                customerdocument=instance
            )
            document_type = instance.documenttype.name
            representation["document_type"] = instance.documenttype.name
            representation[ "Certificate of Incorporation Number" ] = Customerdocumentdetails.objects.get(
                customerdocument=instance,
                field__fieldname="Certificate of Incorporation Number",
            ).value
            representation["Date of Incorporation"] = Customerdocumentdetails.objects.get(
                customerdocument=instance,
                field__fieldname="Date of Incorporation",
            ).value
            if Customerdocumentfiles.objects.filter(
                customerdocument=instance, document_type="AdditionalDocument1" ).exists():
                representation["additional_file1"] = True
            else:
                representation["additional_file1"] = False
            if Customerdocumentfiles.objects.filter(
                customerdocument=instance, document_type="AdditionalDocument2" ).exists():
                representation["additional_file2"] = True
            else:
                representation["additional_file2"] = False
            if Customerdocumentfiles.objects.filter(
                customerdocument=instance, document_type="AdditionalDocument3" ).exists():
                representation["additional_file3"] = True
            else:
                representation["additional_file3"] = False

        return representation


class DocumenttypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Documenttypes
        fields = ["id", "name", "description", "filesrequired"]


class AddressVerificationSerializer(serializers.Serializer):
    document_type = serializers.CharField()
    document_number = serializers.CharField()
    file = serializers.FileField(error_messages = {"invalid": "This field is required."})

    def validate(self, data):
        file = data.get("file")
        document_number=data.get('document_number').strip()
        if not checkNonAsciiChracters(document_number):
            raise serializers.ValidationError({"document_number": "Fancy characters are not allowed."})
        elif not document_number.isalnum():
            raise serializers.ValidationError({"document_number": "Special characters not allowed."})
        elif isinstance(file, InMemoryUploadedFile) or isinstance(
            file, TemporaryUploadedFile
        ):
            ext = os.path.splitext(file.name)[1]
            if not ext in settings.ALLOWED_FORMATS:
                raise serializers.ValidationError({"file": "Incorrect file format"})
            elif file.size > settings.MAX_FILE_SIZE:
                raise serializers.ValidationError(
                    {"file": "Maximum file size allowed is 10 MB"}
                )
            elif not all(ord(c) < 128 for c in file.name):
                raise serializers.ValidationError(
                    {"file": "Special characters should not be in file name"}
                )
        else:
            raise serializers.ValidationError({"file": "Invalid file"})
        return data

    def save(self):
        document_type = self.validated_data["document_type"]
        document_number = self.validated_data["document_number"]
        file = self.validated_data["file"]
        user = self.context["request"].user
        try:
            customer_doc = Customerdocuments.objects.get(
                customer__user=user,
                verificationtype__verificationtype=2,
                isdeleted=False,
            )
            if customer_doc.documenttype.name != document_type:
                customer_doc.delete()
        except Exception as e:
            logger.info(e)
        customer_doc, created = Customerdocuments.objects.get_or_create(
            customer=Customers.objects.get(user=user),
            useraccount=Useraccounts.objects.get(customer__user=user),
            verificationtype=Documenttypesforverification.objects.get(
                documenttype__name=document_type, verificationtype=2
            ),
            createdby=user,
            isdeleted=False,
        )
        customer_doc.documenttype = Documenttypes.objects.get(
            name=document_type,
            description="Address verification proof",
            isdeleted=False,
        )
        customer_doc.save()

        doc_file_loc, created = Customerdocumentfiles.objects.get_or_create(
            customerdocument=customer_doc
        )
        doc_file_loc.filelocation = file
        doc_file_loc.save()

        doc_details, created = Customerdocumentdetails.objects.get_or_create(
            customerdocument=customer_doc, createdby=user
        )
        doc_details.field = Documentfields.objects.get(
            documenttype=customer_doc.documenttype, isdeleted=False
        )
        doc_details.value = document_number
        doc_details.save()


class IdVerificationSerializer(serializers.Serializer):
    def __init__(self, *args, **kwargs):
        super(IdVerificationSerializer, self).__init__(*args, **kwargs)
        if kwargs["data"].get("document_type") in ["Other", "ID Card"]:
            self.fields.pop("validity_month")
            self.fields.pop("validity_year")

    document_type = serializers.CharField()
    document_number = serializers.CharField()
    validity_month = serializers.CharField()
    validity_year = serializers.CharField()
    file1 = serializers.FileField(error_messages = {"invalid": "This field is required."})
    file2 = serializers.FileField(error_messages = {"invalid": "This field is required."})
    file3 = serializers.FileField(error_messages = {"invalid": "This field is required."})
    file4 = serializers.FileField(required=False, allow_null=True)

    def validate(self, data):
        document_number=data.get("document_number").strip()
        file1 = data.get("file1")
        file2 = data.get("file2")
        file3 = data.get("file3")
        file4 = data.get("file4") 
        if not isinstance(file1, InMemoryUploadedFile) and not isinstance(
            file1, TemporaryUploadedFile
        ):
            raise serializers.ValidationError({"file1": "Invalid file"})
        elif not isinstance(file2, InMemoryUploadedFile) and not isinstance(
            file2, TemporaryUploadedFile
        ):
            raise serializers.ValidationError({"file2": "Invalid file"})
        elif not isinstance(file3, InMemoryUploadedFile) and not isinstance(
            file3, TemporaryUploadedFile
        ):
            raise serializers.ValidationError({"file3": "Invalid file"})
        elif file4 and not isinstance(file4, InMemoryUploadedFile) and not isinstance(
            file4, TemporaryUploadedFile
        ):
            raise serializers.ValidationError({"file4": "Invalid file"})
        elif not checkNonAsciiChracters(document_number):
            raise serializers.ValidationError({"document_number":"Fancy characters are not allowed."})
        elif not document_number.isalnum():
            raise serializers.ValidationError({"document_number":"Special characters not allowed."})
        else:
            ext1 = os.path.splitext(file1.name)[1]
            ext2 = os.path.splitext(file2.name)[1]
            ext3 = os.path.splitext(file3.name)[1]
            ext4 = os.path.splitext(file4.name)[1] if file4 else None
            
            if not ext1 in settings.ALLOWED_FORMATS:
                raise serializers.ValidationError({"file1": "Incorrect file format"})
            elif not ext2 in settings.ALLOWED_FORMATS:
                raise serializers.ValidationError({"file2": "Incorrect file format"})
            elif not ext3 in settings.ALLOWED_FORMATS:
                raise serializers.ValidationError({"file3": "Incorrect file format"})
            elif ext4 and not ext4 in settings.ALLOWED_FORMATS:
                raise serializers.ValidationError({"file4": "Incorrect file format"})
            elif file1.size > settings.MAX_FILE_SIZE:
                raise serializers.ValidationError(
                    {"file1": "Maximum file size allowed is 10 MB"}
                )
            elif file2.size > settings.MAX_FILE_SIZE:
                raise serializers.ValidationError(
                    {"file2": "Maximum file size allowed is 10 MB"}
                )
            elif file3.size > settings.MAX_FILE_SIZE:
                raise serializers.ValidationError(
                    {"file3": "Maximum file size allowed is 10 MB"}
            )
            elif file4 and file4.size > settings.MAX_FILE_SIZE:
                raise serializers.ValidationError(
                {"file4": "Maximum file size allowed is 10 MB"}
            )
            elif not all(ord(c) < 128 for c in file1.name):
                raise serializers.ValidationError(
                    {"file1": "Special characters should not be in file name"}
                )
            elif not all(ord(c) < 128 for c in file2.name):
                raise serializers.ValidationError(
                    {"file2": "Special characters should not be in file name"}
                )
            elif not all(ord(c) < 128 for c in file3.name):
                raise serializers.ValidationError(
                    {"file3": "Special characters should not be in file name"}
            )
            if file4 :
                if not all(ord(c) < 128 for c in file4.name):
                    raise serializers.ValidationError(
                    {"file4": "Special characters should not be in file name"}
                )
        return data

    def save(self):
        document_type = self.validated_data["document_type"]
        document_number = self.validated_data["document_number"]
        file1 = self.validated_data["file1"]
        file2 = self.validated_data["file2"]
        file3 = self.validated_data["file3"]
        file4 = self.validated_data.get("file4") 
        user = self.context["request"].user
        if document_type in ["Passport", "Driving License"]:
            validity_month = self.validated_data["validity_month"]
            validity_year = self.validated_data["validity_year"]
        try:
            customer_doc = Customerdocuments.objects.get(
                customer__user=user,
                verificationtype__verificationtype=1,
                isdeleted=False,
            )
            if customer_doc.documenttype.name != document_type:
                customer_doc.delete()
        except Exception as e:
            logger.info(e)

        customer_doc, created = Customerdocuments.objects.get_or_create(
            customer=Customers.objects.get(user=user),
            verificationtype=Documenttypesforverification.objects.get(
                documenttype__name=document_type, verificationtype=1
            ),
        )
        customer_doc.documenttype = Documenttypes.objects.get(
            name=document_type, description="ID verification proof", isdeleted=False
        )
        customer_doc.save()
        document_list = {
            file1: "frontPage",
            file2: "backPage",
            file3: "selfiePage",
        }
        if file4 :
            document_list.update({file4 :"additionalPage" })
        for file, file_type in document_list.items():
            doc_file_loc, created = Customerdocumentfiles.objects.get_or_create(
                customerdocument=customer_doc, document_type=file_type
            )
            doc_file_loc.filelocation = file
            doc_file_loc.save()

        if document_type in ["Passport", "Driving License"]:
            doc_detail1, created = Customerdocumentdetails.objects.get_or_create(
                customerdocument=customer_doc,
                field=Documentfields.objects.get(
                    fieldname="Passport Number"
                    if document_type == "Passport"
                    else "Driving License Number"
                ),
            )
            doc_detail1.value = document_number
            doc_detail1.save()

            doc_detail2, created = Customerdocumentdetails.objects.get_or_create(
                customerdocument=customer_doc,
                field=Documentfields.objects.get(
                    fieldname="Validity" if document_type == "Passport" else "Valid To"
                ),
            )
            doc_detail2.value = f"{validity_month}-{validity_year}"
            doc_detail2.save()
        else:
            doc_details, created = Customerdocumentdetails.objects.get_or_create(
                customerdocument=customer_doc
            )
            doc_details.field = Documentfields.objects.get(
                documenttype=customer_doc.documenttype, isdeleted=False
            )
            doc_details.value = document_number
            doc_details.save()


class CompanyVerificationSerializer(serializers.Serializer):
    document_type = serializers.CharField()
    document_number = serializers.CharField()
    date = serializers.CharField()
    file = serializers.FileField(error_messages = {"invalid": "This field is required."})
    additionaldocument1 = serializers.FileField(required=False,allow_null=True)
    additionaldocument2 = serializers.FileField(required=False,allow_null=True)
    additionaldocument3 = serializers.FileField(required=False,allow_null=True)

    def validate(self, data):
        document_number = data.get('document_number').strip()
        if not checkNonAsciiChracters(document_number):
            raise serializers.ValidationError({"document_number": "Fancy characters are not allowed."})
        elif not document_number.isalnum():
            raise serializers.ValidationError({"document_number": "Special characters not allowed."})

        file = data.get("file")
        additionaldocument1 = data.get("additionaldocument1")
        additionaldocument2 = data.get("additionaldocument2")
        additionaldocument3 = data.get("additionaldocument3")

        if not isinstance(file, InMemoryUploadedFile) and not isinstance(
                file, TemporaryUploadedFile):
            raise serializers.ValidationError({"file1": "Invalid file"})
        elif additionaldocument1 and not isinstance(additionaldocument1, InMemoryUploadedFile) and not isinstance(
                additionaldocument1, TemporaryUploadedFile ):
            raise serializers.ValidationError({"additionaldocument1": "Invalid file"})

        elif additionaldocument2 and not isinstance(additionaldocument2, InMemoryUploadedFile) and not isinstance(
                additionaldocument2, TemporaryUploadedFile ):
            raise serializers.ValidationError({"additionaldocument2": "Invalid file"})

        elif additionaldocument3 and not isinstance(additionaldocument3, InMemoryUploadedFile) and not isinstance(
                additionaldocument3, TemporaryUploadedFile ):
            raise serializers.ValidationError({"additionaldocument3": "Invalid file"})
        else:
            ext1 = os.path.splitext(file.name)[1]
            ext2 = os.path.splitext(additionaldocument1.name)[1] if additionaldocument1 else None
            ext3 = os.path.splitext(additionaldocument2.name)[1] if additionaldocument2 else None
            ext4 = os.path.splitext(additionaldocument3.name)[1] if additionaldocument3 else None

            if not ext1 in settings.ALLOWED_FORMATS:
                raise serializers.ValidationError({"file": "Incorrect file format"})
            elif ext2 and not ext2 in settings.ALLOWED_FORMATS:
                raise serializers.ValidationError({"additionaldocument1": "Incorrect file format"})
            elif ext3 and not ext3 in settings.ALLOWED_FORMATS:
                raise serializers.ValidationError({"additionaldocument2": "Incorrect file format"})
            elif ext4 and not ext4 in settings.ALLOWED_FORMATS:
                raise serializers.ValidationError({"additionaldocument3": "Incorrect file format"})
            elif file.size > settings.MAX_FILE_SIZE:
                raise serializers.ValidationError(
                    {"file": "Maximum file size allowed is 10 MB"}
                )
            elif additionaldocument1 and additionaldocument1.size > settings.MAX_FILE_SIZE:
                raise serializers.ValidationError(
                    {"additionaldocument1": "Maximum file size allowed is 10 MB"}
                )
            elif additionaldocument2 and additionaldocument2.size > settings.MAX_FILE_SIZE:
                raise serializers.ValidationError(
                    {"additionaldocument2": "Maximum file size allowed is 10 MB"}
                )
            elif additionaldocument3 and additionaldocument3.size > settings.MAX_FILE_SIZE:
                raise serializers.ValidationError(
                    {"additionaldocument3": "Maximum file size allowed is 10 MB"}
                )
            elif not all(ord(c) < 128 for c in file.name):
                raise serializers.ValidationError(
                    {"file": "Special characters should not be in file name"}
                )
            if additionaldocument1:
                if not all(ord(c) < 128 for c in additionaldocument1.name):
                    raise serializers.ValidationError(
                        {"additionaldocument1": "Special characters should not be in file name"}
                    )
            if additionaldocument2:
                if not all(ord(c) < 128 for c in additionaldocument2.name):
                    raise serializers.ValidationError(
                        {"additionaldocument2": "Special characters should not be in file name"}
                    )
            if additionaldocument3:
                if not all(ord(c) < 128 for c in additionaldocument3.name):
                    raise serializers.ValidationError(
                        {"additionaldocument3": "Special characters should not be in file name"}
                    )
        return data

    def save(self):
        document_type = self.validated_data["document_type"]
        document_number = self.validated_data["document_number"]
        file = self.validated_data["file"]
        date = self.validated_data["date"]
        user = self.context["request"].user
        additionaldocument1 = self.validated_data.get("additionaldocument1")
        additionaldocument2 = self.validated_data.get("additionaldocument2")
        additionaldocument3 = self.validated_data.get("additionaldocument3")

        business_detail = Businessdetails.objects.get(customer__user=user)
        all_business_detail = Businessdetails.objects.filter(
            createdby=business_detail.createdby
        )
        all_customers_list = []
        for customer_each in all_business_detail:
            all_customers_list.append(customer_each.customer)

        converted_file = default_storage.save(file.name, ContentFile(file.read()))
        company_proof = default_storage.open(converted_file, mode="rb")
        files = {
                company_proof: "Document",
            }
        if additionaldocument1:
            converted_file = default_storage.save(additionaldocument1.name, ContentFile(additionaldocument1.read()))
            company_proof1 = default_storage.open(converted_file, mode="rb")
            files.update({company_proof1: "AdditionalDocument1"})
        if additionaldocument2:
            converted_file = default_storage.save(additionaldocument2.name, ContentFile(additionaldocument2.read()))
            company_proof2 = default_storage.open(converted_file, mode="rb")
            files.update({company_proof2: "AdditionalDocument2"})
        if additionaldocument3:
            converted_file = default_storage.save(additionaldocument3.name, ContentFile(additionaldocument3.read()))
            company_proof3 = default_storage.open(converted_file, mode="rb")
            files.update({company_proof3: "AdditionalDocument3"})
        for customer in all_customers_list:
            customer_doc, created = Customerdocuments.objects.get_or_create(
                customer=customer,
                verificationtype=Documenttypesforverification.objects.get(
                    documenttype__name=document_type, verificationtype=3
                ),
            )
            customer_doc.documenttype = Documenttypes.objects.get(
                name=document_type,
                description="Company registration document",
                isdeleted=False,
            )
            customer_doc.save()


            for file,file_type in files.items():
                doc_file_loc, created = Customerdocumentfiles.objects.get_or_create(
                    customerdocument=customer_doc,document_type=file_type
                )
                doc_file_loc.filelocation = file
                doc_file_loc.save()

                doc_detail1, created = Customerdocumentdetails.objects.get_or_create(
                    customerdocument=customer_doc,
                    field=Documentfields.objects.get(
                        fieldname="Certificate of Incorporation Number"
                    ),
                )
                doc_detail1.value = document_number
                doc_detail1.save()

                doc_detail2, created = Customerdocumentdetails.objects.get_or_create(
                    customerdocument=customer_doc,
                    field=Documentfields.objects.get(fieldname="Date of Incorporation"),
                )
                doc_detail2.value = date
                doc_detail2.save()