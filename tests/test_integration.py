"""Integration tests for Sales Discovery Bot."""

import pytest
import asyncio
import aiohttp
from datetime import datetime
import os

from fastapi.testclient import TestClient
from api.main import app
from api.database import DatabaseManager


class TestAPIIntegration:
    """Test API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
    
    def test_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint."""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        assert "conversations_started_total" in response.text
    
    @pytest.mark.skipif(
        not os.getenv("INTEGRATION_TESTS"),
        reason="Integration tests require live services"
    )
    def test_chat_endpoint(self, client):
        """Test chat endpoint with real services."""
        response = client.post("/chat", json={
            "message": "I run a software company with 10 employees",
            "source": "api"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert "response" in data
        assert data["stage"] is not None
    
    def test_widget_js(self, client):
        """Test widget JavaScript delivery."""
        response = client.get("/widget.js")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/javascript"
        assert "InstaAgentsChat" in response.text
    
    def test_widget_html(self, client):
        """Test widget HTML interface."""
        response = client.get("/widget")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"
        assert "Insta Agents Chat" in response.text


class TestDatabaseIntegration:
    """Test database operations."""
    
    @pytest.fixture
    async def db_manager(self):
        """Create test database manager."""
        if not os.getenv("POSTGRES_TEST_DSN"):
            pytest.skip("Database tests require POSTGRES_TEST_DSN")
        
        db = DatabaseManager(os.getenv("POSTGRES_TEST_DSN"))
        await db.initialize()
        await db.run_migrations()
        yield db
        await db.close()
    
    @pytest.mark.asyncio
    async def test_create_conversation(self, db_manager):
        """Test creating a conversation."""
        conv_id = "test-conv-" + str(datetime.utcnow().timestamp())
        conversation = await db_manager.create_conversation(
            conversation_id=conv_id,
            source="test"
        )
        
        assert conversation["conversation_id"] == conv_id
        assert conversation["source"] == "test"
        assert conversation["created_at"] is not None
    
    @pytest.mark.asyncio
    async def test_add_and_get_messages(self, db_manager):
        """Test adding and retrieving messages."""
        conv_id = "test-conv-" + str(datetime.utcnow().timestamp())
        await db_manager.create_conversation(conv_id, "test")
        
        # Add messages
        await db_manager.add_message(conv_id, "human", "Hello")
        await db_manager.add_message(conv_id, "ai", "Hi there!")
        
        # Retrieve messages
        messages = await db_manager.get_messages(conv_id)
        
        assert len(messages) == 2
        assert messages[0]["role"] == "human"
        assert messages[0]["content"] == "Hello"
        assert messages[1]["role"] == "ai"
        assert messages[1]["content"] == "Hi there!"
    
    @pytest.mark.asyncio
    async def test_update_conversation_state(self, db_manager):
        """Test updating conversation state."""
        conv_id = "test-conv-" + str(datetime.utcnow().timestamp())
        await db_manager.create_conversation(conv_id, "test")
        
        state = {
            "stage": "propose",
            "mvp_proposal": {"agent_name": "Test Agent"},
            "calendly_shown": True
        }
        
        await db_manager.update_conversation_state(conv_id, state)
        
        conversation = await db_manager.get_conversation(conv_id)
        assert conversation["state"]["stage"] == "propose"
        assert conversation["state"]["calendly_shown"] is True
    
    @pytest.mark.asyncio
    async def test_create_lead(self, db_manager):
        """Test creating a lead."""
        conv_id = "test-conv-" + str(datetime.utcnow().timestamp())
        await db_manager.create_conversation(conv_id, "test")
        
        # Update conversation with business info
        state = {
            "business_info": {"business_type": "Test Company"},
            "mvp_proposal": {"agent_name": "Test Agent"}
        }
        await db_manager.update_conversation_state(conv_id, state)
        
        # Create lead
        lead = await db_manager.create_lead(
            conversation_id=conv_id,
            mvp_proposal={"agent_name": "Test Agent"},
            partnership_tier="starter"
        )
        
        assert lead["conversation_id"] == conv_id
        assert lead["business_name"] == "Test Company"
        assert lead["partnership_tier"] == "starter"


class TestRedisIntegration:
    """Test Redis operations."""
    
    @pytest.mark.skipif(
        not os.getenv("REDIS_TEST_URL"),
        reason="Redis tests require REDIS_TEST_URL"
    )
    @pytest.mark.asyncio
    async def test_redis_connectivity(self):
        """Test Redis connection and basic operations."""
        import redis.asyncio as redis
        
        client = redis.from_url(os.getenv("REDIS_TEST_URL"))
        
        # Test ping
        pong = await client.ping()
        assert pong is True
        
        # Test set/get
        await client.set("test:key", "test_value")
        value = await client.get("test:key")
        assert value == b"test_value"
        
        # Cleanup
        await client.delete("test:key")
        await client.close()