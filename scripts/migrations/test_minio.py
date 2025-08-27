#!/usr/bin/env python3
"""
Test MinIO connection using minio-py.
"""

from minio import Minio
from minio.error import S3Error
from io import BytesIO

def test_minio_connection():
    print("=== TESTING MINIO CONNECTION WITH MINIO-PY ===")
    
    try:
        # Create MinIO client
        client = Minio(
            "localhost:9002",
            access_key="minioadmin",
            secret_key="minioadmin",
            secure=False  # Use HTTP instead of HTTPS
        )
        
        print("✅ MinIO client created successfully")
        
        # List buckets
        print("\n--- Listing buckets ---")
        buckets = list(client.list_buckets())
        bucket_names = [b.name for b in buckets]
        print(f"Available buckets: {bucket_names}")
        
        # Check if product-images bucket exists
        bucket_name = 'product-images'
        if bucket_name in bucket_names:
            print(f"✅ Bucket '{bucket_name}' exists")
        else:
            print(f"❌ Bucket '{bucket_name}' does not exist")
            
            # Try to create bucket
            print(f"\n--- Creating bucket '{bucket_name}' ---")
            try:
                client.make_bucket(bucket_name)
                print(f"✅ Bucket '{bucket_name}' created successfully")
            except S3Error as e:
                print(f"❌ Error creating bucket: {e}")
        
        # Test upload a small file
        print(f"\n--- Testing upload to bucket '{bucket_name}' ---")
        try:
            test_content = b"test file content"
            data = BytesIO(test_content)
            client.put_object(
                bucket_name,
                'test.txt',
                data,
                len(test_content)
            )
            print("✅ Test upload successful")
            
            # Check if file exists
            stat = client.stat_object(bucket_name, 'test.txt')
            print(f"✅ Test file verified, size: {stat.size} bytes")
            
            # Clean up test file
            client.remove_object(bucket_name, 'test.txt')
            print("✅ Test file cleaned up")
            
        except S3Error as e:
            print(f"❌ Upload test failed: {e}")
        
    except Exception as e:
        print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    test_minio_connection()
