#!/usr/bin/env python3
"""
Simple script to check database data.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

def main():
    print("=== CHECKING DATABASE DATA ===")
    
    try:
        # Create database session
        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db_session = SessionLocal()
        
        # Check product_images table
        query = text("SELECT COUNT(*) as count FROM product_images")
        result = db_session.execute(query)
        count = result.scalar()
        print(f"Total product_images records: {count}")
        
        # Get first few records
        query = text("SELECT id, product_id, path, filename FROM product_images LIMIT 5")
        result = db_session.execute(query)
        
        print("\nFirst 5 records:")
        for row in result:
            print(f"ID: {row.id}, Product: {row.product_id}, Path: {row.path}, Filename: {row.filename}")
        
        # Check products table
        query = text("SELECT COUNT(*) as count FROM products")
        result = db_session.execute(query)
        count = result.scalar()
        print(f"\nTotal products records: {count}")
        
        db_session.close()
        print("\n✅ Database check completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
