import boto3
from botocore.exceptions import NoCredentialsError
from django.conf import settings
import uuid
import os

def save_image_to_s3(image_file, folder_name):
    s3 = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )

    try:
        # Generate a unique file name using UUID and keep the original file extension
        unique_filename = f"{uuid.uuid4()}{os.path.splitext(image_file.name)[1]}"
        s3_object_key = f'{folder_name}/{unique_filename}'
        
        s3.upload_fileobj(image_file, settings.AWS_STORAGE_BUCKET_NAME, s3_object_key)

        # Return the path or URL to the uploaded image
        return s3_object_key
    except NoCredentialsError:
        return None  # Handle as needed
