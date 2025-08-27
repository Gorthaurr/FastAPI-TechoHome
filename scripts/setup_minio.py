#!/usr/bin/env python3
"""
Setup MinIO bucket for migration.
"""

import boto3
import os

def main():
    print("=== SETTING UP MINIO BUCKET ===")
    
    try:
        # Create S3 client
        s3 = boto3.client(
            's3',
            endpoint_url='http://localhost:9000',
            aws_access_key_id='minioadmin',
            aws_secret_access_key='minioadmin'
        )
        
        bucket_name = 'product-images'
        
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
