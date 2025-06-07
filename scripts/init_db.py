"""Initialize database schema."""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from api.database import DatabaseManager
from agent.config import get_config


async def init_database():
    """Initialize database with schema."""
    config = get_config()
    
    print(f"Initializing database at: {config.postgres_dsn}")
    
    db = DatabaseManager(config.postgres_dsn)
    await db.initialize()
    
    print("Running migrations...")
    await db.run_migrations()
    
    print("Database initialization complete!")
    
    # Verify tables exist
    async with db.pool.acquire() as conn:
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
        """)
        
        print("\nCreated tables:")
        for table in tables:
            print(f"  - {table['tablename']}")
    
    await db.close()


if __name__ == "__main__":
    asyncio.run(init_database())