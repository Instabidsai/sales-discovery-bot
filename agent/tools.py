"""Tools and utilities for the Sales Discovery Bot."""

import re
from typing import List, Dict, Any, Optional
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from .state import BusinessInfo, MVPProposal


async def extract_business_info(
    llm: ChatOpenAI,
    messages: List[BaseMessage]
) -> BusinessInfo:
    """Extract business information from conversation history."""
    
    # Create a prompt to extract structured information
    extraction_prompt = f"""
Analyze the following conversation and extract business information.
Return a JSON object with these fields:
- business_type: what kind of business they run
- team_size: number of employees (null if not mentioned)
- biggest_challenge: their main operational challenge
- time_wasters: list of tasks that waste time
- current_tools: list of tools/software they use

Conversation:
{chr(10).join([f'{m.type}: {m.content}' for m in messages])}

JSON:
"""
    
    response = await llm.ainvoke(extraction_prompt)
    
    # Parse JSON from response
    try:
        import json
        # Extract JSON from response (handle markdown code blocks)
        json_str = response.content
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0]
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0]
            
        data = json.loads(json_str.strip())
        return BusinessInfo(**data)
    except:
        # Return empty if parsing fails
        return BusinessInfo()


async def generate_mvp_proposal(
    llm: ChatOpenAI,
    messages: List[BaseMessage],
    business_info: Dict[str, Any],
    identified_task: str
) -> MVPProposal:
    """Generate an MVP proposal based on the conversation."""
    
    proposal_prompt = f"""
Based on this business context:
- Type: {business_info.get('business_type')}
- Challenge: {business_info.get('biggest_challenge')}
- Task to automate: {identified_task}
- Current tools: {business_info.get('current_tools', [])}

Create an MVP AI agent proposal. Return a JSON object with:
- agent_name: catchy name for the agent
- description: specific description of what it does (2-3 sentences)
- time_saved: realistic time saved per week
- integrations: list of tools it integrates with
- success_metric: measurable outcome

Make it specific and achievable. Focus on quick wins.

JSON:
"""
    
    response = await llm.ainvoke(proposal_prompt)
    
    try:
        import json
        json_str = response.content
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0]
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0]
            
        data = json.loads(json_str.strip())
        return MVPProposal(**data)
    except:
        # Fallback proposal
        return MVPProposal(
            agent_name="Process Automation Assistant",
            description="Automates your most time-consuming task with AI-powered intelligence.",
            time_saved="10+ hours/week",
            integrations=["Email", "Spreadsheets"],
            success_metric="90% reduction in manual processing time"
        )


async def determine_partnership_tier(
    business_info: Dict[str, Any],
    mvp_proposal: Dict[str, Any]
) -> str:
    """Determine the appropriate partnership tier."""
    
    team_size = business_info.get("team_size", 0) or 0
    
    # Simple rules for tier selection
    if team_size > 50:
        return "enterprise"
    elif team_size > 15 or len(business_info.get("time_wasters", [])) > 3:
        return "growth"
    else:
        return "starter"