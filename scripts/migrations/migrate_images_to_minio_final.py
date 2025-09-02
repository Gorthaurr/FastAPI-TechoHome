#!/usr/bin/env python3
"""
Final migration script using minio-py.
"""

import json
import logging
import os
import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List

from minio import Minio
from minio.error import S3Error
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm

# Add project path
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.append(project_root)

from app.core.config import settings

# Logging setup
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FinalMinioMigrationService:
    def __init__(self):
        self.source_base_path = Path(r"C:\Users\demon\Desktop\парсинг\out")
        self.minio_client = self._create_minio_client()
        self.db_session = self._create_db_session()
        self.bucket_name = "product-images"

    def _create_minio_client(self):
        return Minio(
            "localhost:9002",
            access_key="minioadmin",
            secret_key="minioadmin",
            secure=False,
        )

    def _create_db_session(self):
        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionLocal()

    def get_migration_data(self) -> List[Dict[str, Any]]:
        logger.info("Getting migration data from database...")

        query = text(
            """
            SELECT 
                pi.id,
                pi.product_id,
                pi.path as relative_path,
                pi.filename,
                pi.sort_order,
                pi.is_primary,
                pi.alt_text,
                pi.file_size,
                pi.mime_type,
                pi.width,
                pi.height,
                p.name as product_name
            FROM product_images pi
            JOIN products p ON pi.product_id = p.id
            ORDER BY pi.product_id, pi.sort_order
        """
        )

        result = self.db_session.execute(query)
        records = []

        for row in result:
            record = {
                "id": row.id,
                "product_id": row.product_id,
                "relative_path": row.relative_path,
                "filename": row.filename,
                "sort_order": row.sort_order,
                "is_primary": row.is_primary,
                "alt_text": row.alt_text,
                "file_size": row.file_size,
                "mime_type": row.mime_type,
                "width": row.width,
                "height": row.height,
                "product_name": row.product_name,
            }
            records.append(record)

        logger.info(f"Found {len(records)} records for migration")
        return records

    def validate_source_files(
        self, migration_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        logger.info("Checking source files existence...")

        valid_records = []
        missing_files = []

        for record in tqdm(migration_data, desc="Checking files"):
            absolute_path = self.source_base_path / record["relative_path"]

            if absolute_path.exists():
                record["absolute_path"] = str(absolute_path)
                record["file_exists"] = True
                valid_records.append(record)
            else:
                record["file_exists"] = False
                missing_files.append(record)
                logger.warning(f"File not found: {absolute_path}")

        logger.info(f"Found {len(valid_records)} existing files")
        logger.info(f"Missing {len(missing_files)} files")

        if missing_files:
            with open("missing_files.json", "w", encoding="utf-8") as f:
                json.dump(missing_files, f, ensure_ascii=False, indent=2)
            logger.info("Missing files report saved to missing_files.json")

        return valid_records

    def migrate_file_to_minio(self, record: Dict[str, Any]) -> Dict[str, Any]:
        try:
            minio_path = f"products/{record['product_id']}/{record['filename']}"

            # Read file and upload to MinIO
            with open(record["absolute_path"], "rb") as file_data:
                file_content = file_data.read()
                data = BytesIO(file_content)

                self.minio_client.put_object(
                    self.bucket_name, minio_path, data, len(file_content)
                )

            # Check if file was uploaded
            try:
                stat = self.minio_client.stat_object(self.bucket_name, minio_path)
                record["minio_path"] = minio_path
                record["migration_status"] = "success"
                record["migrated_at"] = datetime.utcnow().isoformat()
                return record
            except S3Error:
                record["migration_status"] = "error"
                record["error"] = "File not found in MinIO after upload"
                return record

        except Exception as e:
            record["migration_status"] = "error"
            record["error"] = str(e)
            return record

    def migrate_all_files(
        self, valid_records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        logger.info("Starting file migration to MinIO...")

        results = []
        successful = 0
        failed = 0

        for record in tqdm(valid_records, desc="Migrating to MinIO"):
            result = self.migrate_file_to_minio(record)
            results.append(result)

            if result["migration_status"] == "success":
                successful += 1
            else:
                failed += 1
                logger.error(
                    f"Migration error {record['filename']}: {result.get('error')}"
                )

        logger.info(f"Migration completed: {successful} successful, {failed} errors")
        return results

    def update_database(self, migration_results: List[Dict[str, Any]]) -> tuple:
        logger.info("Updating database with new paths...")

        updated = 0
        errors = 0

        for result in tqdm(migration_results, desc="Updating database"):
            if result["migration_status"] == "success":
                try:
                    self.db_session.execute(
                        text(
                            """
                            UPDATE product_images 
                            SET path = :minio_path, 
                                updated_at = :updated_at
                            WHERE id = :id
                        """
                        ),
                        {
                            "minio_path": result["minio_path"],
                            "updated_at": datetime.utcnow(),
                            "id": result["id"],
                        },
                    )
                    updated += 1
                except Exception as e:
                    errors += 1
                    logger.error(f"Database update error for ID {result['id']}: {e}")

        try:
            self.db_session.commit()
            logger.info(f"Database updated: {updated} records, {errors} errors")
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Database commit error: {e}")
            return 0, updated + errors

        return updated, errors

    def generate_migration_report(
        self, migration_results: List[Dict[str, Any]]
    ) -> None:
        logger.info("Generating migration report...")

        total = len(migration_results)
        successful = len(
            [r for r in migration_results if r["migration_status"] == "success"]
        )
        failed = total - successful

        products_stats = {}
        for result in migration_results:
            product_id = result["product_id"]
            if product_id not in products_stats:
                products_stats[product_id] = {"total": 0, "success": 0, "failed": 0}

            products_stats[product_id]["total"] += 1
            if result["migration_status"] == "success":
                products_stats[product_id]["success"] += 1
            else:
                products_stats[product_id]["failed"] += 1

        report = {
            "migration_info": {
                "started_at": datetime.utcnow().isoformat(),
                "total_files": total,
                "successful": successful,
                "failed": failed,
                "success_rate": f"{(successful/total*100):.1f}%" if total > 0 else "0%",
            },
            "products_summary": products_stats,
            "failed_files": [
                {
                    "id": r["id"],
                    "product_id": r["product_id"],
                    "filename": r["filename"],
                    "error": r.get("error", "Unknown error"),
                }
                for r in migration_results
                if r["migration_status"] == "error"
            ],
        }

        with open("migration_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info("Report saved to migration_report.json")

        print(f"\n=== MIGRATION REPORT ===")
        print(f"Total files: {total}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Success rate: {report['migration_info']['success_rate']}")
        print(f"Products processed: {len(products_stats)}")

    def run_migration(self) -> None:
        logger.info("Starting image migration to MinIO")

        try:
            migration_data = self.get_migration_data()
            if not migration_data:
                logger.warning("No data for migration")
                return

            valid_records = self.validate_source_files(migration_data)
            if not valid_records:
                logger.error("No valid files for migration")
                return

            migration_results = self.migrate_all_files(valid_records)
            updated, errors = self.update_database(migration_results)
            self.generate_migration_report(migration_results)

            logger.info("Migration completed successfully!")

        except Exception as e:
            logger.error(f"Critical migration error: {e}")
            raise
        finally:
            self.db_session.close()


def main():
    print("=== FINAL MINIO MIGRATION ===")
    print("Make sure:")
    print("1. MinIO server is running on port 9002")
    print("2. Database is available and contains product_images table")
    print()

    response = input("Continue migration? (y/N): ")
    if response.lower() != "y":
        print("Migration cancelled")
        return

    try:
        migration_service = FinalMinioMigrationService()
        migration_service.run_migration()
    except Exception as e:
        logger.error(f"Migration startup error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
