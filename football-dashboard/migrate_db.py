#!/usr/bin/env python3
"""
Database migration script to add half-time prediction columns to existing database.
Run this script after updating the database schema to support half-time predictions.
"""

import sqlite3
import os

def migrate_database(db_path='football_predictions.db'):
    """Migrate existing database to support half-time predictions."""
    
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found. No migration needed.")
        return
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            print("Starting database migration for half-time predictions...")
            
            # Check if columns already exist
            cursor.execute("PRAGMA table_info(predictions)")
            columns = [row[1] for row in cursor.fetchall()]
            
            # Add half-time prediction columns to predictions table if they don't exist
            if 'ht_home_win_ft_lose_prob' not in columns:
                cursor.execute('ALTER TABLE predictions ADD COLUMN ht_home_win_ft_lose_prob REAL')
                print("Added ht_home_win_ft_lose_prob column to predictions table")
            
            if 'ht_away_win_ft_lose_prob' not in columns:
                cursor.execute('ALTER TABLE predictions ADD COLUMN ht_away_win_ft_lose_prob REAL')
                print("Added ht_away_win_ft_lose_prob column to predictions table")
            
            # Check match_results table columns
            cursor.execute("PRAGMA table_info(match_results)")
            result_columns = [row[1] for row in cursor.fetchall()]
            
            # Add half-time result columns to match_results table if they don't exist
            if 'ht_home_score' not in result_columns:
                cursor.execute('ALTER TABLE match_results ADD COLUMN ht_home_score INTEGER')
                print("Added ht_home_score column to match_results table")
            
            if 'ht_away_score' not in result_columns:
                cursor.execute('ALTER TABLE match_results ADD COLUMN ht_away_score INTEGER')
                print("Added ht_away_score column to match_results table")
            
            if 'ht_outcome' not in result_columns:
                cursor.execute('ALTER TABLE match_results ADD COLUMN ht_outcome TEXT')
                print("Added ht_outcome column to match_results table")
            
            if 'ht_win_ft_lose_outcome' not in result_columns:
                cursor.execute('ALTER TABLE match_results ADD COLUMN ht_win_ft_lose_outcome TEXT DEFAULT "NONE"')
                print("Added ht_win_ft_lose_outcome column to match_results table")
            
            conn.commit()
            print("Database migration completed successfully!")
            
            # Display migration summary
            cursor.execute("SELECT COUNT(*) FROM predictions")
            prediction_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM match_results")
            result_count = cursor.fetchone()[0]
            
            print(f"\nMigration Summary:")
            print(f"- Predictions table: {prediction_count} records")
            print(f"- Match results table: {result_count} records")
            print(f"- Half-time prediction columns added successfully")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        print("Please check your database file and try again.")

if __name__ == "__main__":
    import sys
    
    # Allow specifying database path as command line argument
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'football_predictions.db'
    
    print("Football Dashboard Database Migration")
    print("=" * 40)
    print(f"Target database: {db_path}")
    print()
    
    migrate_database(db_path)
    
    print("\nMigration process completed.")
    print("You can now restart the football dashboard to use half-time predictions.")