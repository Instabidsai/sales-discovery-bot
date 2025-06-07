"""Unit tests for Sales Discovery Bot."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from agent import SalesDiscoveryAgent, AgentConfig
from agent.state import BusinessInfo, MVPProposal
from agent.tools import extract_business_info, generate_mvp_proposal, determine_partnership_tier


class TestAgentConfig:
    """Test configuration handling."""
    
    def test_config_defaults(self):
        """Test default configuration values."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            config = AgentConfig(
                postgres_dsn="postgresql://test"
            )
            assert config.llm_model == "gpt-4o"
            assert config.llm_temperature == 0.7
            assert config.starter_price == 1250
            assert config.growth_price == 2500
            assert config.enterprise_price == 5000
    
    def test_config_from_env(self):
        """Test configuration from environment variables."""
        env_vars = {
            'OPENAI_API_KEY': 'test-key',
            'LLM_MODEL': 'gpt-3.5-turbo',
            'LLM_TEMPERATURE': '0.5',
            'POSTGRES_DSN': 'postgresql://test',
            'CALENDLY_URL': 'https://test.calendly.com'
        }
        with patch.dict('os.environ', env_vars):
            config = AgentConfig()
            assert config.llm_model == "gpt-3.5-turbo"
            assert config.llm_temperature == 0.5
            assert config.calendly_url == "https://test.calendly.com"


class TestBusinessExtraction:
    """Test business information extraction."""
    
    @pytest.mark.asyncio
    async def test_extract_business_info(self):
        """Test extracting business info from messages."""
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = Mock(
            content='''{"business_type": "marketing agency", "team_size": 15, "biggest_challenge": "lead tracking"}'''
        )
        
        messages = [
            Mock(type="human", content="I run a marketing agency"),
            Mock(type="ai", content="How many people are on your team?"),
            Mock(type="human", content="We have 15 employees")
        ]
        
        result = await extract_business_info(mock_llm, messages)
        
        assert isinstance(result, BusinessInfo)
        assert result.business_type == "marketing agency"
        assert result.team_size == 15
        assert result.biggest_challenge == "lead tracking"
    
    @pytest.mark.asyncio
    async def test_extract_business_info_invalid_json(self):
        """Test handling of invalid JSON response."""
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = Mock(content="Not valid JSON")
        
        result = await extract_business_info(mock_llm, [])
        
        assert isinstance(result, BusinessInfo)
        assert result.business_type is None
        assert result.team_size is None


class TestMVPProposal:
    """Test MVP proposal generation."""
    
    @pytest.mark.asyncio
    async def test_generate_mvp_proposal(self):
        """Test generating MVP proposal."""
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = Mock(
            content='''
```json
{
    "agent_name": "Lead Tracker Pro",
    "description": "Automatically captures and qualifies leads from multiple sources.",
    "time_saved": "15 hours/week",
    "integrations": ["Email", "CRM", "Slack"],
    "success_metric": "50% reduction in lead response time"
}
```
'''
        )
        
        business_info = {
            "business_type": "marketing agency",
            "biggest_challenge": "lead tracking"
        }
        
        result = await generate_mvp_proposal(
            mock_llm, [], business_info, "lead tracking and qualification"
        )
        
        assert isinstance(result, MVPProposal)
        assert result.agent_name == "Lead Tracker Pro"
        assert "15 hours/week" in result.time_saved
        assert "Email" in result.integrations
        assert "50%" in result.success_metric
    
    @pytest.mark.asyncio
    async def test_generate_mvp_proposal_fallback(self):
        """Test fallback when proposal generation fails."""
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = Mock(content="Invalid response")
        
        result = await generate_mvp_proposal(mock_llm, [], {}, "")
        
        assert isinstance(result, MVPProposal)
        assert result.agent_name == "Process Automation Assistant"
        assert result.time_saved == "10+ hours/week"


class TestPartnershipTiers:
    """Test partnership tier determination."""
    
    @pytest.mark.asyncio
    async def test_starter_tier(self):
        """Test starter tier selection."""
        business_info = {"team_size": 5}
        tier = await determine_partnership_tier(business_info, {})
        assert tier == "starter"
    
    @pytest.mark.asyncio
    async def test_growth_tier(self):
        """Test growth tier selection."""
        business_info = {"team_size": 20}
        tier = await determine_partnership_tier(business_info, {})
        assert tier == "growth"
    
    @pytest.mark.asyncio
    async def test_enterprise_tier(self):
        """Test enterprise tier selection."""
        business_info = {"team_size": 100}
        tier = await determine_partnership_tier(business_info, {})
        assert tier == "enterprise"
    
    @pytest.mark.asyncio
    async def test_growth_tier_by_complexity(self):
        """Test growth tier based on complexity."""
        business_info = {
            "team_size": 10,
            "time_wasters": ["data entry", "reporting", "scheduling", "invoicing"]
        }
        tier = await determine_partnership_tier(business_info, {})
        assert tier == "growth"


class TestSalesDiscoveryAgent:
    """Test the main agent class."""
    
    @pytest.fixture
    def agent_config(self):
        """Create test configuration."""
        return AgentConfig(
            openai_api_key="test-key",
            postgres_dsn="postgresql://test",
            redis_url="redis://localhost"
        )
    
    def test_agent_initialization(self, agent_config):
        """Test agent initialization."""
        agent = SalesDiscoveryAgent(agent_config)
        assert agent.config == agent_config
        assert agent.llm is not None
        assert agent.graph is not None
    
    @pytest.mark.asyncio
    async def test_process_new_conversation(self, agent_config):
        """Test processing a new conversation."""
        with patch('agent.logic.ChatOpenAI') as mock_llm:
            agent = SalesDiscoveryAgent(agent_config)
            
            # Mock the graph execution
            with patch.object(agent.graph, 'ainvoke') as mock_ainvoke:
                with patch.object(agent.graph, 'get_state') as mock_get_state:
                    mock_get_state.return_value.values = None
                    mock_ainvoke.return_value = {
                        "messages": [Mock(content="Welcome! What does your business do?")]
                    }
                    
                    result = await agent.process_message(
                        "test-conversation",
                        "I need help with automation"
                    )
                    
                    assert result["conversation_id"] == "test-conversation"
                    assert "response" in result