#!/usr/bin/env python3
"""
Migration script for product data (excluding images).
This script handles migration of products, categories, and other related data.

Usage:
    python migrations/migrate_products_data.py

Note: This is a template script for future product data migrations.
The actual migration logic would depend on the source data format and requirements.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm

# Add project path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.config import settings

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ProductDataMigrationService:
    def __init__(self):
        self.db_session = self._create_db_session()
        
    def _create_db_session(self):
        """Create database session for PostgreSQL."""
        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionLocal()
    
    def get_current_data_summary(self) -> Dict[str, Any]:
        """Get summary of current data in database."""
        logger.info("Getting current data summary...")
        
        summary = {}
        
        # Count products
        query = text("SELECT COUNT(*) as count FROM products")
        result = self.db_session.execute(query)
        summary['products_count'] = result.scalar()
        
        # Count categories
        query = text("SELECT COUNT(*) as count FROM categories")
        result = self.db_session.execute(query)
        summary['categories_count'] = result.scalar()
        
        # Count product images
        query = text("SELECT COUNT(*) as count FROM product_images")
        result = self.db_session.execute(query)
        summary['product_images_count'] = result.scalar()
        
        # Get sample data
        query = text("SELECT id, name, category_id FROM products LIMIT 3")
        result = self.db_session.execute(query)
        summary['sample_products'] = [{'id': row.id, 'name': row.name, 'category_id': row.category_id} for row in result]
        
        query = text("SELECT id, slug FROM categories LIMIT 3")
        result = self.db_session.execute(query)
        summary['sample_categories'] = [{'id': row.id, 'slug': row.slug} for row in result]
        
        logger.info(f"Current data summary: {summary}")
        return summary
    
    def validate_data_integrity(self) -> Dict[str, Any]:
        """Validate data integrity and relationships."""
        logger.info("Validating data integrity...")
        
        validation_results = {}
        
        # Check for orphaned product images
        query = text("""
            SELECT COUNT(*) as count 
            FROM product_images pi 
            LEFT JOIN products p ON pi.product_id = p.id 
            WHERE p.id IS NULL
        """)
        result = self.db_session.execute(query)
        orphaned_images = result.scalar()
        validation_results['orphaned_images'] = orphaned_images
        
        # Check for products without images
        query = text("""
            SELECT COUNT(*) as count 
            FROM products p 
            LEFT JOIN product_images pi ON p.id = pi.product_id 
            WHERE pi.id IS NULL
        """)
        result = self.db_session.execute(query)
        products_without_images = result.scalar()
        validation_results['products_without_images'] = products_without_images
        
        # Check for products without categories
        query = text("""
            SELECT COUNT(*) as count 
            FROM products p 
            LEFT JOIN categories c ON p.category_id = c.id 
            WHERE c.id IS NULL
        """)
        result = self.db_session.execute(query)
        products_without_categories = result.scalar()
        validation_results['products_without_categories'] = products_without_categories
        
        logger.info(f"Validation results: {validation_results}")
        return validation_results
    
    def generate_data_report(self) -> None:
        """Generate comprehensive data report."""
        logger.info("Generating data report...")
        
        summary = self.get_current_data_summary()
        validation = self.validate_data_integrity()
        
        report = {
            'generated_at': datetime.utcnow().isoformat(),
            'data_summary': summary,
            'validation_results': validation,
            'recommendations': []
        }
        
        # Add recommendations based on validation
        if validation['orphaned_images'] > 0:
            report['recommendations'].append(f"Found {validation['orphaned_images']} orphaned product images")
        
        if validation['products_without_images'] > 0:
            report['recommendations'].append(f"Found {validation['products_without_images']} products without images")
        
        if validation['products_without_categories'] > 0:
            report['recommendations'].append(f"Found {validation['products_without_categories']} products without categories")
        
        report_path = Path(__file__).parent / 'products_data_report.json'
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Report saved to {report_path}")
        
        print(f"\n=== PRODUCTS DATA REPORT ===")
        print(f"Products: {summary['products_count']}")
        print(f"Categories: {summary['categories_count']}")
        print(f"Product Images: {summary['product_images_count']}")
        print(f"Orphaned Images: {validation['orphaned_images']}")
        print(f"Products without Images: {validation['products_without_images']}")
        print(f"Products without Categories: {validation['products_without_categories']}")
        
        if report['recommendations']:
            print(f"\nRecommendations:")
            for rec in report['recommendations']:
                print(f"  - {rec}")
    
    def backup_current_data(self) -> str:
        """Create backup of current data."""
        logger.info("Creating data backup...")
        
        backup_data = {}
        
        # Backup products
        query = text("SELECT id, name, description, price_raw, price_cents, category_id, product_url FROM products")
        result = self.db_session.execute(query)
        backup_data['products'] = [
            {
                'id': row.id,
                'name': row.name,
                'description': row.description,
                'price_raw': row.price_raw,
                'price_cents': row.price_cents,
                'category_id': row.category_id,
                'product_url': row.product_url
            }
            for row in result
        ]
        
        # Backup categories
        query = text("SELECT id, slug FROM categories")
        result = self.db_session.execute(query)
        backup_data['categories'] = [
            {
                'id': row.id,
                'slug': row.slug
            }
            for row in result
        ]
        
        # Backup product images metadata
        query = text("""
            SELECT id, product_id, path, filename, sort_order, is_primary, 
                   alt_text, file_size, mime_type, width, height
            FROM product_images
        """)
        result = self.db_session.execute(query)
        backup_data['product_images'] = [
            {
                'id': row.id,
                'product_id': row.product_id,
                'path': row.path,
                'filename': row.filename,
                'sort_order': row.sort_order,
                'is_primary': row.is_primary,
                'alt_text': row.alt_text,
                'file_size': row.file_size,
                'mime_type': row.mime_type,
                'width': row.width,
                'height': row.height
            }
            for row in result
        ]
        
        backup_path = Path(__file__).parent / f'data_backup_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.json'
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Backup saved to {backup_path}")
        return str(backup_path)
    
    def run_analysis(self) -> None:
        """Run complete data analysis."""
        logger.info("Starting products data analysis")
        
        try:
            # Generate report
            self.generate_data_report()
            
            # Create backup
            backup_path = self.backup_current_data()
            
            logger.info("Analysis completed successfully!")
            logger.info(f"Backup created at: {backup_path}")
            
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            raise
        finally:
            self.db_session.close()


def main():
    print("=== PRODUCTS DATA ANALYSIS ===")
    print("This script analyzes current product data and creates backup.")
    print()
    print("What it does:")
    print("1. Generates data summary report")
    print("2. Validates data integrity")
    print("3. Creates backup of current data")
    print("4. Provides recommendations")
    print()
    
    response = input("Continue analysis? (y/N): ")
    if response.lower() != 'y':
        print("Analysis cancelled")
        return
    
    try:
        migration_service = ProductDataMigrationService()
        migration_service.run_analysis()
    except Exception as e:
        logger.error(f"Analysis startup error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
