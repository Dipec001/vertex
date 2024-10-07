import boto3
from botocore.exceptions import NoCredentialsError
from django.conf import settings

def save_image_to_s3(image_file, folder_name):
    s3 = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )

    try:
        # Construct the S3 object key with the specified folder and image file name
        s3_object_key = f'{folder_name}/{image_file.name}'
        
        s3.upload_fileobj(image_file, settings.AWS_STORAGE_BUCKET_NAME, s3_object_key)

        # Generate the URL of the uploaded image
        return f'{s3_object_key}'
    except NoCredentialsError:
        return None  # Handle the exception based on your application's requirements