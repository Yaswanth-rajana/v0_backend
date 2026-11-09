#!/usr/bin/env python3
"""
Migration script to add result_type and is_walkover columns to the match table.
Run this script to add: result_type, is_walkover
"""

import sys
import os

# Add parent directory to path to import config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from config import Config
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

def run_migration():
    """Add missing walkover and outcome columns to match table safely"""
    app = Flask(__name__)
    app.config.from_object(Config)
    db = SQLAlchemy(app)
    
    with app.app_context():
        try:
            # Check existing columns in match table
            result = db.session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = :db_name 
                AND TABLE_NAME = 'match' 
                AND COLUMN_NAME IN ('result_type', 'is_walkover')
            """), {'db_name': Config.DB_NAME})
            
            existing_columns = {row[0] for row in result.fetchall()}
            columns_to_add = []
            
            if 'result_type' not in existing_columns:
                columns_to_add.append("ADD COLUMN `result_type` VARCHAR(20) NOT NULL DEFAULT 'regular'")
            if 'is_walkover' not in existing_columns:
                columns_to_add.append("ADD COLUMN `is_walkover` TINYINT(1) NOT NULL DEFAULT 0")
            
            if not columns_to_add:
                print("All columns ('result_type', 'is_walkover') already exist. Migration not needed.")
                return
            
            alter_sql = f"ALTER TABLE `match` {', '.join(columns_to_add)}"
            print(f"Executing: {alter_sql}")
            db.session.execute(text(alter_sql))
            db.session.commit()
            print("Successfully added walkover columns to match table.")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error during migration: {str(e)}")
            raise e

if __name__ == '__main__':
    run_migration()

