import boto3
import botocore
from botocore.exceptions import ClientError

from entrebiz import settings
import logging
logger = logging.getLogger('lessons')


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
