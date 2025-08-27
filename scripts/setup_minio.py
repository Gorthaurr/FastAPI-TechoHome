#!/usr/bin/env python3
"""
Setup MinIO bucket for migration.
"""

import boto3
import os
import sys

# Add project path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from app.core.config import settings

def main():
    print("=== SETTING UP MINIO BUCKET ===")
    
    try:
        # Create S3 client using settings from .env
        s3 = boto3.client(
            's3',
            endpoint_url=settings.S3_ENDPOINT_URL or 'http://localhost:9000',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'minioadmin'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'minioadmin')
        )
        
        bucket_name = settings.S3_BUCKET_NAME or 'product-images'
        
        # Check if bucket exists
        try:
            s3.head_bucket(Bucket=bucket_name)
            print(f"Bucket '{bucket_name}' already exists")
        except:
            # Create bucket
            s3.create_bucket(Bucket=bucket_name)
            print(f"Bucket '{bucket_name}' created successfully")
        
        # List buckets
        response = s3.list_buckets()
        print(f"\nAvailable buckets: {[b['Name'] for b in response['Buckets']]}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
