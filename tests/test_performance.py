"""Performance tests for Sales Discovery Bot."""

import pytest
import asyncio
import time
import psutil
import os
from concurrent.futures import ThreadPoolExecutor
from typing import List

from agent import SalesDiscoveryAgent, AgentConfig


class TestPerformance:
    """Performance benchmarks."""
    
    @pytest.fixture
    def test_config(self):
        """Create test configuration."""
        return AgentConfig(
            openai_api_key=os.getenv("OPENAI_API_KEY", "test-key"),
            postgres_dsn="postgresql://test",
            redis_url="redis://localhost",
            llm_model="gpt-3.5-turbo"  # Use cheaper model for tests
        )
    
    @pytest.mark.skipif(
        not os.getenv("PERFORMANCE_TESTS"),
        reason="Performance tests are resource intensive"
    )
    @pytest.mark.asyncio
    async def test_response_time(self, test_config):
        """Test agent response time < 2 seconds."""
        agent = SalesDiscoveryAgent(test_config)
        
        # Warm up
        await agent.process_message("warmup", "Hello")
        
        # Test response times
        response_times = []
        test_messages = [
            "I run a marketing agency",
            "We have 15 employees",
            "Our biggest challenge is lead tracking",
            "We currently use Salesforce and Slack",
            "We spend 20 hours per week on manual data entry"
        ]
        
        for i, message in enumerate(test_messages):
            start = time.time()
            result = await agent.process_message(
                f"perf-test-{i}",
                message
            )
            response_time = time.time() - start
            response_times.append(response_time)
            
            assert result["response"] is not None
        
        avg_response_time = sum(response_times) / len(response_times)
        p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)]
        
        assert avg_response_time < 2.0, f"Average response time {avg_response_time}s exceeds 2s"
        assert p95_response_time < 3.0, f"P95 response time {p95_response_time}s exceeds 3s"
    
    @pytest.mark.skipif(
        not os.getenv("PERFORMANCE_TESTS"),
        reason="Performance tests are resource intensive"
    )
    @pytest.mark.asyncio
    async def test_concurrent_conversations(self, test_config):
        """Test handling 10 concurrent conversations."""
        agent = SalesDiscoveryAgent(test_config)
        
        async def process_conversation(conv_id: str) -> float:
            """Process a single conversation."""
            messages = [
                "I run a tech startup",
                "We have 8 employees",
                "We need help with customer support automation"
            ]
            
            start = time.time()
            for message in messages:
                await agent.process_message(conv_id, message)
            return time.time() - start
        
        # Run 10 concurrent conversations
        tasks = [
            process_conversation(f"concurrent-{i}")
            for i in range(10)
        ]
        
        start = time.time()
        durations = await asyncio.gather(*tasks)
        total_time = time.time() - start
        
        # All conversations should complete
        assert len(durations) == 10
        
        # Average time per conversation should be reasonable
        avg_duration = sum(durations) / len(durations)
        assert avg_duration < 10.0, f"Average conversation duration {avg_duration}s exceeds 10s"
        
        # Total time should show concurrency benefit
        assert total_time < sum(durations) * 0.5, "Insufficient concurrency benefit"
    
    @pytest.mark.skipif(
        not os.getenv("PERFORMANCE_TESTS"),
        reason="Performance tests are resource intensive"
    )
    def test_memory_usage(self, test_config):
        """Test memory usage stays under 512MB."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        agent = SalesDiscoveryAgent(test_config)
        
        # Process multiple conversations
        async def run_conversations():
            for i in range(50):
                await agent.process_message(
                    f"memory-test-{i}",
                    f"Test message {i}"
                )
        
        asyncio.run(run_conversations())
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        assert memory_increase < 200, f"Memory increase {memory_increase}MB exceeds 200MB"
        assert final_memory < 512, f"Total memory {final_memory}MB exceeds 512MB limit"
    
    @pytest.mark.skipif(
        not os.getenv("PERFORMANCE_TESTS"),
        reason="Performance tests are resource intensive"
    )
    @pytest.mark.asyncio
    async def test_token_efficiency(self, test_config):
        """Test token usage efficiency."""
        agent = SalesDiscoveryAgent(test_config)
        
        # Mock token counting
        total_tokens = 0
        conversations_processed = 0
        
        test_conversations = [
            [
                "I run an e-commerce business",
                "We have 25 employees",
                "Order fulfillment takes too much time",
                "We use Shopify and ShipStation",
                "Manual order processing takes 30 hours per week"
            ],
            [
                "We're a consulting firm",
                "Team of 12 consultants",
                "Project tracking is our pain point",
                "Currently using Excel and email",
                "Spending 15 hours weekly on status updates"
            ]
        ]
        
        for i, messages in enumerate(test_conversations):
            for message in messages:
                result = await agent.process_message(
                    f"token-test-{i}",
                    message
                )
                # Estimate tokens (rough approximation)
                total_tokens += len(message.split()) * 1.3
                total_tokens += len(result["response"].split()) * 1.3
            
            conversations_processed += 1
        
        avg_tokens_per_conversation = total_tokens / conversations_processed
        
        # Should complete a conversation in under 5000 tokens on average
        assert avg_tokens_per_conversation < 5000, \
            f"Average tokens {avg_tokens_per_conversation} exceeds 5000 per conversation"


class TestScalability:
    """Test scalability characteristics."""
    
    @pytest.mark.skipif(
        not os.getenv("SCALABILITY_TESTS"),
        reason="Scalability tests require significant resources"
    )
    @pytest.mark.asyncio
    async def test_queue_processing_rate(self):
        """Test task queue processing rate."""
        import redis.asyncio as redis
        
        client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
        queue_name = "test:tasks:queue"
        
        # Add 1000 tasks to queue
        for i in range(1000):
            await client.lpush(queue_name, f"task-{i}")
        
        # Measure processing rate
        start = time.time()
        processed = 0
        
        while processed < 1000 and (time.time() - start) < 30:
            task = await client.rpop(queue_name)
            if task:
                processed += 1
                # Simulate minimal processing
                await asyncio.sleep(0.001)
        
        duration = time.time() - start
        rate = processed / duration
        
        # Should process at least 100 tasks per second
        assert rate >= 100, f"Processing rate {rate:.1f} tasks/sec is below 100 tasks/sec"
        
        # Cleanup
        await client.delete(queue_name)
        await client.close()