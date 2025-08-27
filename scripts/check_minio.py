#!/usr/bin/env python3
"""
Check MinIO bucket contents.
"""

import boto3
import os

def main():
    print("=== CHECKING MINIO BUCKET ===")
    
    try:
        # Create S3 client
        s3 = boto3.client(
            's3',
            endpoint_url='http://localhost:9000',
            aws_access_key_id='minioadmin',
            aws_secret_access_key='minioadmin'
        )
        
        # List objects in bucket
        response = s3.list_objects_v2(Bucket='product-images')
        
        if 'Contents' in response:
            objects = response['Contents']
            print(f"Total objects in bucket: {len(objects)}")
            
            # Show first 10 objects
            print("\nFirst 10 objects:")
            for i, obj in enumerate(objects[:10]):
                print(f"{i+1}. {obj['Key']} ({obj['Size']} bytes)")
                
            if len(objects) > 10:
                print(f"... and {len(objects) - 10} more objects")
        else:
            print("Bucket is empty")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
