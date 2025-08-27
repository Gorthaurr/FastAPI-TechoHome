#!/usr/bin/env python3
"""
Check table structure.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

def main():
    print("=== CHECKING TABLE STRUCTURE ===")

    try:
        # Create database session
        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db_session = SessionLocal()

        # Check products table structure
        query = text("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'products' 
            ORDER BY ordinal_position
        """)
        result = db_session.execute(query)

        print("Products table structure:")
        for row in result:
            print(f"  {row.column_name}: {row.data_type} ({'NULL' if row.is_nullable == 'YES' else 'NOT NULL'})")

        # Check categories table structure
        query = text("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'categories' 
            ORDER BY ordinal_position
        """)
        result = db_session.execute(query)

        print("\nCategories table structure:")
        for row in result:
            print(f"  {row.column_name}: {row.data_type} ({'NULL' if row.is_nullable == 'YES' else 'NOT NULL'})")

        # Check product_images table structure
        query = text("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'product_images' 
            ORDER BY ordinal_position
        """)
        result = db_session.execute(query)

        print("\nProduct_images table structure:")
        for row in result:
            print(f"  {row.column_name}: {row.data_type} ({'NULL' if row.is_nullable == 'YES' else 'NOT NULL'})")

        db_session.close()
        print("\n✅ Table structure check completed!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
