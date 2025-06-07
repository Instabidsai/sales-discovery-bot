"""Database management for Sales Discovery Bot."""

import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

import asyncpg
from asyncpg.pool import Pool


class DatabaseManager:
    """Handles all database operations."""
    
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[Pool] = None
    
    async def initialize(self):
        """Initialize database connection pool."""
        self.pool = await asyncpg.create_pool(
            self.dsn,
            min_size=5,
            max_size=20,
            command_timeout=60
        )
    
    async def close(self):
        """Close database connections."""
        if self.pool:
            await self.pool.close()
    
    async def health_check(self) -> bool:
        """Check database connectivity."""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            return result == 1
    
    async def run_migrations(self):
        """Run database migrations."""
        async with self.pool.acquire() as conn:
            # Create conversations table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    conversation_id VARCHAR(255) UNIQUE NOT NULL,
                    source VARCHAR(50) NOT NULL,
                    state JSONB DEFAULT '{}',
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create messages table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    conversation_id VARCHAR(255) REFERENCES conversations(conversation_id),
                    role VARCHAR(10) NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create leads table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS leads (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    conversation_id VARCHAR(255) REFERENCES conversations(conversation_id),
                    business_name VARCHAR(255),
                    contact_email VARCHAR(255),
                    proposed_mvp JSONB,
                    partnership_tier VARCHAR(20),
                    calendly_booked BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_created 
                ON conversations(created_at DESC)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_conversation 
                ON messages(conversation_id, created_at)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_leads_conversation 
                ON leads(conversation_id)
            """)
    
    async def create_conversation(
        self,
        conversation_id: str,
        source: str
    ) -> Dict[str, Any]:
        """Create a new conversation."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO conversations (conversation_id, source)
                VALUES ($1, $2)
                RETURNING *
            """, conversation_id, source)
            return dict(row)
    
    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation by ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM conversations
                WHERE conversation_id = $1
            """, conversation_id)
            return dict(row) if row else None
    
    async def update_conversation_state(
        self,
        conversation_id: str,
        state: Dict[str, Any]
    ):
        """Update conversation state."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE conversations
                SET state = $2, updated_at = CURRENT_TIMESTAMP
                WHERE conversation_id = $1
            """, conversation_id, json.dumps(state))
    
    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str
    ) -> Dict[str, Any]:
        """Add a message to conversation."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO messages (conversation_id, role, content)
                VALUES ($1, $2, $3)
                RETURNING *
            """, conversation_id, role, content)
            return dict(row)
    
    async def get_messages(
        self,
        conversation_id: str
    ) -> List[Dict[str, Any]]:
        """Get all messages for a conversation."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM messages
                WHERE conversation_id = $1
                ORDER BY created_at ASC
            """, conversation_id)
            return [dict(row) for row in rows]
    
    async def list_conversations(
        self,
        limit: int = 50,
        offset: int = 0,
        source: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List conversations with summaries."""
        async with self.pool.acquire() as conn:
            query = """
                SELECT 
                    c.*,
                    COUNT(m.id) as message_count,
                    COALESCE(c.state->>'stage', 'unknown') as stage,
                    COALESCE(c.state->>'calendly_shown', 'false')::boolean as calendly_shown,
                    CASE 
                        WHEN c.state->>'mvp_proposal' IS NOT NULL 
                        THEN true ELSE false 
                    END as has_proposal
                FROM conversations c
                LEFT JOIN messages m ON c.conversation_id = m.conversation_id
            """
            
            params = []
            if source:
                query += " WHERE c.source = $1"
                params.append(source)
            
            query += """
                GROUP BY c.id, c.conversation_id, c.source, c.state, c.metadata, 
                         c.created_at, c.updated_at
                ORDER BY c.created_at DESC
                LIMIT $%d OFFSET $%d
            """ % (len(params) + 1, len(params) + 2)
            
            params.extend([limit, offset])
            
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
    
    async def create_lead(
        self,
        conversation_id: str,
        mvp_proposal: Optional[Dict[str, Any]] = None,
        partnership_tier: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a lead from conversation."""
        async with self.pool.acquire() as conn:
            # Extract business info from conversation state
            conv = await self.get_conversation(conversation_id)
            if not conv:
                raise ValueError(f"Conversation {conversation_id} not found")
            
            state = json.loads(conv["state"]) if isinstance(conv["state"], str) else conv["state"]
            business_info = state.get("business_info", {})
            
            row = await conn.fetchrow("""
                INSERT INTO leads (
                    conversation_id,
                    business_name,
                    proposed_mvp,
                    partnership_tier
                ) VALUES ($1, $2, $3, $4)
                ON CONFLICT (conversation_id) DO UPDATE
                SET 
                    proposed_mvp = EXCLUDED.proposed_mvp,
                    partnership_tier = EXCLUDED.partnership_tier
                RETURNING *
            """, 
                conversation_id,
                business_info.get("business_type", "Unknown"),
                json.dumps(mvp_proposal) if mvp_proposal else None,
                partnership_tier
            )
            return dict(row)