#!/usr/bin/env python3
"""
Database initialization script.
"""

import asyncio
import asyncpg
import os
import sys

async def init_database():
    """Initialize the database schema."""
    
    DATABASE_URL = os.getenv("DATABASE_URL", default=None)
    
    try:
        print("Connecting to database...")
        conn = await asyncpg.connect(DATABASE_URL)
        print("Connected")
        
        print("Creating tables...")       
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_users (
                user_id VARCHAR(255) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("Table created")
        
        # Create indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_users_connected_at 
            ON chat_users(connected_at)
        """)
        print("Created indexes")
        
        # Clear any existing data (for development)
        await conn.execute("DELETE FROM chat_users")
        print("Cleared existing data")
        
        # Close connection
        await conn.close()
        print("Database initialization completed!")
        
    except asyncpg.InvalidCatalogNameError:
        print("Error: Database does not exist.")
        print("Please create the database first:")
        sys.exit(1)
        
    except asyncpg.InvalidPasswordError:
        print("Error: Invalid database credentials.")
        print("Please check your DATABASE_URL environment variable.")
        sys.exit(1)
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        sys.exit(1)

async def test_connection():
    """Test the database connection."""
    
    DATABASE_URL = os.getenv("DATABASE_URL", default=None)
    
    try:
        print("Testing database connection...")
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Test query
        result = await conn.fetchval("SELECT current_database()")
        print(f"Connected to database: {result}")
        
        # Test table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'chat_users'
            )
        """)
        
        if table_exists:
            print("Table 'chat_users' exists")
        else:
            print("Table 'chat_users' does not exist")
            
        await conn.close()
        print("Database test completed successfully!")
        
    except Exception as e:
        print(f"Database test failed: {e}")
        sys.exit(1)

def print_usage():
    """Print usage instructions."""
    print("Database Management Script for Real-time Chat App")
    print("Usage:")
    print("  python init_db.py init    # Initialize database schema")
    print("  python init_db.py test    # Test database connection")
    print("")
    print("Environment Variables:")
    print("  DATABASE_URL - PostgreSQL connection string")

async def main():
    """Main function."""
    
    if len(sys.argv) != 2:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "init":
        await init_database()
    elif command == "test":
        await test_connection()
    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())