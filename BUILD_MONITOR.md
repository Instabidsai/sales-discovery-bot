# Meta-Agent Factory Build Monitor

This demonstrates how the Factory monitors GitHub Actions builds.

## Current Build Status
- **Workflow Updated**: 2025-06-08T04:41:43Z
- **Expected Image**: `ghcr.io/instabidsai/sales-discovery-bot:main-41d612b2`
- **Status**: 🔄 Building...

## Polling Implementation
```python
class BuildMonitor:
    def __init__(self, repo, sha):
        self.repo = repo
        self.sha = sha
        self.start_time = datetime.utcnow()
        
    async def wait_for_completion(self):
        """Poll until build completes or timeout"""
        attempt = 0
        while attempt < 60:  # 5 min timeout
            # Check notifications
            notifications = await github.list_notifications(
                repo=self.repo,
                since=self.start_time
            )
            
            # Check for completion
            for notif in notifications:
                if "workflow run succeeded" in notif.title:
                    return await self.test_agent()
                elif "workflow run failed" in notif.title:
                    return await self.debug_failure()
            
            # Try to pull image directly
            if await self.image_exists():
                return await self.test_agent()
                
            await asyncio.sleep(5)
            attempt += 1
            
        return {"status": "timeout", "error": "Build took too long"}
```

## Next Steps
1. Wait for build completion (~2-3 minutes)
2. Pull the Docker image
3. Start container with test configuration
4. Run conversation tests with the agent
5. Validate all 6 conversation steps work
