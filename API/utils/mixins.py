import boto3
import botocore
from botocore.exceptions import ClientError

from entrebiz import settings
import logging

from utils.models import Activitylog

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

    def get_last_login(self,user):
        try:
            if Activitylog.objects.filter(user=user, activity='login'):
                try:
                    logintime = Activitylog.objects.filter(user=user, activity='login').order_by("-activitytime")[
                        1].activitytime
                except Exception as e:
                    logger.info(e)
                    logintime = Activitylog.objects.filter(user=user, activity='login').order_by("-activitytime")[
                        0].activitytime

                logintime = logintime.strftime("%d %b %Y, %H:%M") + " UTC"
                return logintime
            else:
                return "---"
        except Exception as e:
            logger.info(e)
            return "---"

