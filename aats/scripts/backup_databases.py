"""
Database Backup Script for AATS
Handles backing up all databases and managing backup rotations
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta
import shutil
import os
import json
import argparse

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from integration.databases.db_factory import DatabaseFactory, DatabaseType
from config.settings.base_config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DatabaseBackup")

class BackupManager:
    """Manages database backups and rotations"""

    def __init__(self, backup_dir: str, retention_days: int = 30):
        self.backup_dir = Path(backup_dir)
        self.retention_days = retention_days
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create backup directory structure
        self.backup_path = self.backup_dir / self.timestamp
        self.backup_path.mkdir(parents=True, exist_ok=True)
        
        # Create database-specific directories
        for db_type in DatabaseType:
            (self.backup_path / db_type.value).mkdir(exist_ok=True)

    async def backup_all(self) -> None:
        """Backup all databases"""
        try:
            backup_tasks = []
            for db_type in DatabaseType:
                backup_tasks.append(self.backup_database(db_type))
            
            # Run backups concurrently
            await asyncio.gather(*backup_tasks)
            
            # Create backup manifest
            await self._create_manifest()
            
            # Cleanup old backups
            await self._cleanup_old_backups()
            
            logger.info(f"All database backups completed successfully: {self.timestamp}")
            
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            # Cleanup failed backup
            if self.backup_path.exists():
                shutil.rmtree(self.backup_path)
            raise

    async def backup_database(self, db_type: DatabaseType) -> None:
        """Backup specific database"""
        logger.info(f"Starting backup of {db_type.value} database")
        
        try:
            db = await DatabaseFactory.get_database(db_type)
            backup_file = self.backup_path / db_type.value / f"{db_type.value}.backup"
            
            # Perform backup
            result = await db.backup(str(backup_file))
            
            if result["status"] != "success":
                raise Exception(f"Backup failed: {result.get('error')}")
            
            logger.info(f"Successfully backed up {db_type.value} database")
            
        except Exception as e:
            logger.error(f"Failed to backup {db_type.value} database: {str(e)}")
            raise

    async def _create_manifest(self) -> None:
        """Create backup manifest file"""
        manifest = {
            "timestamp": self.timestamp,
            "databases": {},
            "config": {
                "retention_days": self.retention_days
            }
        }
        
        # Collect database sizes and metadata
        for db_type in DatabaseType:
            db_path = self.backup_path / db_type.value
            if db_path.exists():
                size = sum(f.stat().st_size for f in db_path.rglob('*') if f.is_file())
                manifest["databases"][db_type.value] = {
                    "size_bytes": size,
                    "files": [f.name for f in db_path.rglob('*') if f.is_file()]
                }
        
        # Write manifest
        manifest_path = self.backup_path / "manifest.json"
        with manifest_path.open('w') as f:
            json.dump(manifest, f, indent=2)

    async def _cleanup_old_backups(self) -> None:
        """Clean up backups older than retention period"""
        logger.info("Cleaning up old backups...")
        
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        for backup_dir in self.backup_dir.iterdir():
            if not backup_dir.is_dir():
                continue
                
            try:
                # Parse backup timestamp
                backup_time = datetime.strptime(backup_dir.name, "%Y%m%d_%H%M%S")
                
                # Check if backup is older than retention period
                if backup_time < cutoff_date:
                    logger.info(f"Removing old backup: {backup_dir.name}")
                    shutil.rmtree(backup_dir)
                    
            except ValueError:
                # Skip directories that don't match timestamp format
                continue

    @staticmethod
    async def restore_backup(backup_path: str, db_types: Optional[List[str]] = None) -> None:
        """Restore databases from backup"""
        backup_dir = Path(backup_path)
        
        if not backup_dir.exists():
            raise ValueError(f"Backup directory not found: {backup_path}")
        
        # Load manifest
        manifest_path = backup_dir / "manifest.json"
        if not manifest_path.exists():
            raise ValueError("Backup manifest not found")
            
        with manifest_path.open('r') as f:
            manifest = json.load(f)
        
        # Determine which databases to restore
        if db_types is None:
            db_types = list(manifest["databases"].keys())
        
        logger.info(f"Starting restore from backup: {backup_dir.name}")
        
        for db_type in db_types:
            if db_type not in manifest["databases"]:
                logger.warning(f"No backup found for database: {db_type}")
                continue
            
            try:
                logger.info(f"Restoring {db_type} database")
                
                db = await DatabaseFactory.get_database(DatabaseType[db_type.upper()])
                backup_file = backup_dir / db_type / f"{db_type}.backup"
                
                if not backup_file.exists():
                    raise ValueError(f"Backup file not found: {backup_file}")
                
                # Perform restore
                result = await db.restore(str(backup_file))
                
                if result["status"] != "success":
                    raise Exception(f"Restore failed: {result.get('error')}")
                
                logger.info(f"Successfully restored {db_type} database")
                
            except Exception as e:
                logger.error(f"Failed to restore {db_type} database: {str(e)}")
                raise

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="AATS Database Backup Tool")
    
    parser.add_argument(
        '--action',
        choices=['backup', 'restore'],
        default='backup',
        help='Action to perform (backup or restore)'
    )
    
    parser.add_argument(
        '--backup-dir',
        default=config.data_dir / 'backups',
        help='Directory for storing backups'
    )
    
    parser.add_argument(
        '--retention-days',
        type=int,
        default=30,
        help='Number of days to retain backups'
    )
    
    parser.add_argument(
        '--restore-path',
        help='Path to backup directory for restore'
    )
    
    parser.add_argument(
        '--databases',
        nargs='+',
        help='Specific databases to restore (default: all)'
    )
    
    return parser.parse_args()

async def main():
    """Main execution function"""
    args = parse_args()
    
    try:
        if args.action == 'backup':
            backup_manager = BackupManager(args.backup_dir, args.retention_days)
            await backup_manager.backup_all()
            
        elif args.action == 'restore':
            if not args.restore_path:
                raise ValueError("--restore-path is required for restore action")
                
            await BackupManager.restore_backup(args.restore_path, args.databases)
            
    except Exception as e:
        logger.error(f"Operation failed: {str(e)}")
        sys.exit(1)
    finally:
        # Close all database connections
        await DatabaseFactory.close_all()

if __name__ == "__main__":
    asyncio.run(main())
