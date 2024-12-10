from PIL import Image
from moviepy import VideoFileClip
import boto3
from botocore.exceptions import NoCredentialsError
from django.conf import settings
import uuid
import os
from io import BytesIO
import tempfile

import logging
logger = logging.getLogger(__name__)

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

        logger.info(f"Uploading {image_file.name} to S3 bucket {settings.AWS_STORAGE_BUCKET_NAME} at {s3_object_key}")
        s3.upload_fileobj(image_file, settings.AWS_STORAGE_BUCKET_NAME, s3_object_key)
        logger.info("Upload successful")

        # Return the path or URL to the uploaded image
        return s3_object_key
    except NoCredentialsError:
        logger.error("No AWS credentials found")
        return None  # Handle as needed
    except Exception as e:
        logger.error(f"Error occurred during upload: {e}")
        return None


def compress_file(file_path, file_type):
    if file_type == 'image':
        return compress_image(file_path)
    elif file_type == 'video':
        return compress_video(file_path)
    else:
        raise ValueError("Unsupported file type")

def compress_image(image_file_path):
    # Open and compress the image
    with Image.open(image_file_path) as img:
        img = img.convert("RGB")
        output = BytesIO()
        img.save(output, format='JPEG', optimize=True, quality=30)  # Adjust quality as needed
        output.seek(0)

        # Create a temporary file to save the compressed image 
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file: 
            temp_file.write(output.getvalue()) 
            temp_file_path = temp_file.name 
        
    return temp_file_path

def compress_video(video_file_path):
    # Load the video file
    clip = VideoFileClip(video_file_path)

    # Create a temporary file to save the compressed video
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
        temp_file_path = temp_file.name
        clip.write_videofile(temp_file_path, codec='libx264', bitrate="240k")  # Adjust bitrate as needed

    return temp_file_path

def save_file_to_s3(file_path, folder_name, file_type):
    s3 = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )

    try:
        # Compress the file before uploading
        compressed_file_path = compress_file(file_path, file_type)

        # Generate a unique file name using the original file extension
        unique_filename = f"{uuid.uuid4()}{os.path.splitext(file_path)[1]}"
        
        s3_object_key = f'{folder_name}/{unique_filename}'

        # Open the compressed file and upload it to S3
        with open(compressed_file_path, 'rb') as compressed_file:
            s3.upload_fileobj(compressed_file, settings.AWS_STORAGE_BUCKET_NAME, s3_object_key)

        # Remove the temporary file after uploading
        os.remove(compressed_file_path)

        # Return the path or URL to the uploaded file
        return s3_object_key
    except NoCredentialsError:
        return None  # Handle as needed
