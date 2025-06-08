"""Core agent logic using LangGraph for conversation management."""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent

from .state import ConversationState, BusinessInfo, MVPProposal
from .prompts import SYSTEM_PROMPT, QUESTION_PROMPTS
from .config import get_config
from .tools import extract_business_info, generate_mvp_proposal, determine_partnership_tier

logger = logging.getLogger(__name__)


class SalesDiscoveryAgent:
    """Sales discovery agent with LangGraph conversation management."""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        
        # Initialize LLM - using Anthropic
        self.llm = ChatAnthropic(
            model=self.config.llm_model,
            temperature=self.config.llm_temperature,
            max_tokens=self.config.max_tokens,
            anthropic_api_key=self.config.anthropic_api_key
        )
        
        # Initialize checkpointer for conversation persistence
        self.checkpointer = InMemorySaver()
        
        # Build the conversation graph
        self.graph = self._build_graph()
        
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph conversation state machine."""
        graph = StateGraph(ConversationState)
        
        # Add nodes for each conversation stage
        graph.add_node("understand", self._understand_business)
        graph.add_node("identify", self._identify_mvp)
        graph.add_node("scope", self._scope_mvp)
        graph.add_node("propose", self._create_proposal)
        graph.add_node("recommend", self._recommend_tier)
        graph.add_node("book", self._book_demo)
        
        # Define the flow
        graph.set_entry_point("understand")
        
        # Add conditional edges based on conversation progress
        graph.add_conditional_edges(
            "understand",
            self._should_continue_understanding,
            {
                "continue": "understand",
                "next": "identify"
            }
        )
        
        graph.add_edge("identify", "scope")
        graph.add_edge("scope", "propose")
        graph.add_edge("propose", "recommend")
        graph.add_edge("recommend", "book")
        graph.add_edge("book", END)
        
        return graph.compile(checkpointer=self.checkpointer)
    
    async def _understand_business(self, state: ConversationState) -> Dict[str, Any]:
        """Understand the business through 2-3 questions."""
        questions_asked = state.get("questions_asked", 0)
        
        # Extract business info from the conversation so far
        if state["messages"]:
            business_info = await extract_business_info(
                self.llm, 
                state["messages"]
            )
            state["business_info"] = business_info.dict()
        
        # Determine which question to ask
        if questions_asked < len(QUESTION_PROMPTS["understand"]):
            question = QUESTION_PROMPTS["understand"][questions_asked]
            response = AIMessage(content=question)
            
            return {
                "messages": [response],
                "questions_asked": questions_asked + 1,
                "stage": "understand"
            }
        
        return {"stage": "identify"}
    
    def _should_continue_understanding(self, state: ConversationState) -> str:
        """Determine if we should continue understanding or move to identify."""
        questions_asked = state.get("questions_asked", 0)
        business_info = state.get("business_info", {})
        
        # Need at least 2 questions answered with substantive info
        if questions_asked < 2:
            return "continue"
        
        # Check if we have enough business context
        if business_info.get("business_type") and business_info.get("biggest_challenge"):
            return "next"
        
        # Max 3 questions in understand phase
        if questions_asked >= 3:
            return "next"
            
        return "continue"
    
    async def _identify_mvp(self, state: ConversationState) -> Dict[str, Any]:
        """Identify the MVP opportunity."""
        prompt = [
            SystemMessage(content=SYSTEM_PROMPT),
            *state["messages"],
            HumanMessage(content=QUESTION_PROMPTS["identify"])
        ]
        
        response = await self.llm.ainvoke(prompt)
        
        return {
            "messages": [AIMessage(content=response.content)],
            "stage": "identify"
        }
    
    async def _scope_mvp(self, state: ConversationState) -> Dict[str, Any]:
        """Get specific details about the MVP."""
        # Extract the identified task from previous messages
        last_human_msg = None
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                last_human_msg = msg.content
                break
        
        identified_task = last_human_msg or "the process you mentioned"
        
        # Ask scoping questions
        scope_questions = QUESTION_PROMPTS["scope"]
        formatted_questions = [
            q.format(task=identified_task) for q in scope_questions
        ]
        
        question = "\n".join(formatted_questions)
        
        return {
            "messages": [AIMessage(content=question)],
            "identified_task": identified_task,
            "stage": "scope"
        }
    
    async def _create_proposal(self, state: ConversationState) -> Dict[str, Any]:
        """Create the MVP proposal."""
        # Generate the proposal based on all collected information
        proposal = await generate_mvp_proposal(
            self.llm,
            state["messages"],
            state.get("business_info", {}),
            state.get("identified_task", "")
        )
        
        # Format the proposal
        formatted_proposal = f"""
🎉 **Here's your MVP AI Agent proposal:**

* 🎯 **Your First AI Agent:** {proposal.agent_name}
* 📋 **What it does:** {proposal.description}
* ⏰ **Time saved:** {proposal.time_saved}
* 🔌 **Integrates with:** {', '.join(proposal.integrations)}
* 📊 **Success metric:** {proposal.success_metric}
* 🚀 **Delivery:** {proposal.delivery_time}
"""
        
        return {
            "messages": [AIMessage(content=formatted_proposal)],
            "mvp_proposal": proposal.dict(),
            "stage": "propose"
        }
    
    async def _recommend_tier(self, state: ConversationState) -> Dict[str, Any]:
        """Recommend partnership tier."""
        tier = await determine_partnership_tier(
            state.get("business_info", {}),
            state.get("mvp_proposal", {})
        )
        
        tier_details = {
            "starter": f"**Starter Partnership** (${self.config.starter_price}/month): Perfect for your first AI agent.",
            "growth": f"**Growth Partnership** (${self.config.growth_price}/month): Ideal for expanding automation across multiple areas.",
            "enterprise": f"**Enterprise Partnership** (${self.config.enterprise_price}/month): Comprehensive AI transformation."
        }
        
        recommendation = f"""
💡 **Recommended Partnership:** {tier_details[tier]}

This gives you everything needed to deploy your {state.get('mvp_proposal', {}).get('agent_name', 'AI agent')} and see immediate ROI.

Ready to see this in action?
"""
        
        return {
            "messages": [AIMessage(content=recommendation)],
            "partnership_tier": tier,
            "stage": "recommend"
        }
    
    async def _book_demo(self, state: ConversationState) -> Dict[str, Any]:
        """Drive to Calendly booking."""
        calendly_prompt = QUESTION_PROMPTS["calendly"].format(
            calendly_url=self.config.calendly_url
        )
        
        return {
            "messages": [AIMessage(content=calendly_prompt)],
            "calendly_shown": True,
            "stage": "complete"
        }
    
    async def process_message(
        self, 
        conversation_id: str,
        message: str,
        source: str = "api"
    ) -> Dict[str, Any]:
        """Process a message in the conversation."""
        config = {"configurable": {"thread_id": conversation_id}}
        
        # Get current state or initialize
        current_state = self.graph.get_state(config)
        
        if not current_state.values:
            # Initialize new conversation
            initial_state = {
                "messages": [],
                "conversation_id": conversation_id,
                "source": source,
                "stage": "start",
                "business_info": {},
                "questions_asked": 0,
                "started_at": datetime.now(timezone.utc),
                "calendly_shown": False
            }
            await self.graph.ainvoke(initial_state, config)
        else:
            # Add user message and continue
            user_message = HumanMessage(content=message)
            await self.graph.ainvoke(
                {"messages": [user_message]},
                config
            )
        
        # Get the updated state
        updated_state = self.graph.get_state(config)
        state_values = updated_state.values if updated_state.values else {}
        
        # Get the last AI message as response
        last_ai_message = None
        for msg in reversed(state_values.get("messages", [])):
            if isinstance(msg, AIMessage):
                last_ai_message = msg.content
                break
        
        return {
            "response": last_ai_message,
            "stage": state_values.get("stage"),
            "conversation_id": conversation_id,
            "calendly_shown": state_values.get("calendly_shown", False)
        }