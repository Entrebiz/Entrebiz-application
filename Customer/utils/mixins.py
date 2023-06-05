import boto3
import botocore
from botocore.exceptions import ClientError

from entrebiz import settings
import logging
logger = logging.getLogger('lessons')
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from utils.models import Customerdocumentfiles, Customerdocuments

class UtilMixins:
    def is_ajax(self, request):
        return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'

    def upload_to_s3(self,fileToUpload,cloudFilename):

        session = boto3.session.Session(aws_access_key_id=settings.AWS_S3_ACCESS_KEY_ID,
                                        aws_secret_access_key=settings.AWS_S3_SECRET_ACCESS_KEY)
        s3 = session.resource('s3')
        s3.Bucket(settings.AWS_STORAGE_BUCKET_NAME).put_object(Key=cloudFilename, Body=open(fileToUpload.name, 'rb'))
        s3_file_path = settings.AWS_S3_BUCKET_URL+cloudFilename
        return s3_file_path

    def check_cloudfile_exists(self,filepath):

        session = boto3.session.Session(aws_access_key_id=settings.AWS_S3_ACCESS_KEY_ID,
                                        aws_secret_access_key=settings.AWS_S3_SECRET_ACCESS_KEY)
        s3 = session.resource('s3')
        try:
            s3.Object(settings.AWS_STORAGE_BUCKET_NAME, filepath).load()
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                return False
            else:
                logger.info(f"BOTO3 error :{e}")
                return False

        return True

    def save_company_doc(self, fileobj, all_customers_list, doc_type):
        converted_file = default_storage.save(fileobj.name, ContentFile(fileobj.read()))
        address_proof = default_storage.open(converted_file, mode="rb")
        for customer in all_customers_list:
            customer_doc = Customerdocuments.objects.filter(
                customer=customer, verificationtype__verificationtype=3).first()
            customer_files, status = Customerdocumentfiles.objects.get_or_create(
                customerdocument=customer_doc, document_type=doc_type)
            customer_files.filelocation = address_proof
            customer_files.save()

    def create_customer_doc(self, customer_doc, fileobj, doc_type):
        customer_files = Customerdocumentfiles.objects.create(
            customerdocument=customer_doc, document_type=doc_type
        )
        customer_files.filelocation = fileobj
        customer_files.save()
