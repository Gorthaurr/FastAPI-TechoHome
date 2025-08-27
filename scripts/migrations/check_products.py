#!/usr/bin/env python3
"""
Check products table content.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

def main():
    print("=== CHECKING PRODUCTS TABLE ===")

    try:
        # Create database session
        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db_session = SessionLocal()

        # Check products table count
        query = text("SELECT COUNT(*) as count FROM products")
        result = db_session.execute(query)
        count = result.scalar()
        print(f"Total products records: {count}")

        # Get first few products with details
        query = text("""
            SELECT id, name, description, price_raw, price_cents, category_id, product_url 
            FROM products 
            LIMIT 5
        """)
        result = db_session.execute(query)

        print("\nFirst 5 products:")
        for row in result:
            print(f"ID: {row.id}")
            print(f"Name: {row.name}")
            print(f"Description: {row.description[:100] if row.description else 'None'}...")
            print(f"Price Raw: {row.price_raw}")
            print(f"Price Cents: {row.price_cents}")
            print(f"Category ID: {row.category_id}")
            print(f"Product URL: {row.product_url}")
            print("-" * 50)

        # Check categories table
        query = text("SELECT COUNT(*) as count FROM categories")
        result = db_session.execute(query)
        count = result.scalar()
        print(f"\nTotal categories records: {count}")

        # Get categories
        query = text("SELECT id, slug FROM categories LIMIT 5")
        result = db_session.execute(query)

        print("\nFirst 5 categories:")
        for row in result:
            print(f"ID: {row.id}, Slug: {row.slug}")

        db_session.close()
        print("\n✅ Products check completed successfully!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
