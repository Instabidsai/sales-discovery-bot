"""Conversation state management using LangGraph."""

from typing import Annotated, List, Dict, Any, Optional, Literal
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel
from datetime import datetime


class BusinessInfo(BaseModel):
    """Extracted business information."""
    business_type: Optional[str] = None
    team_size: Optional[int] = None
    biggest_challenge: Optional[str] = None
    time_wasters: List[str] = []
    current_tools: List[str] = []


class MVPProposal(BaseModel):
    """MVP agent proposal."""
    agent_name: str
    description: str
    time_saved: str
    integrations: List[str]
    success_metric: str
    delivery_time: str = "2-3 weeks"
    

class ConversationState(TypedDict):
    """State for the sales discovery conversation."""
    # Message history
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Conversation metadata
    conversation_id: str
    source: Literal["widget", "email", "api"]
    
    # Current stage in the flow
    stage: Literal[
        "start",
        "understand",
        "identify", 
        "scope",
        "propose",
        "recommend",
        "book",
        "complete"
    ]
    
    # Extracted information
    business_info: Dict[str, Any]
    identified_task: Optional[str]
    mvp_proposal: Optional[Dict[str, Any]]
    partnership_tier: Optional[Literal["starter", "growth", "enterprise"]]
    
    # Tracking
    questions_asked: int
    started_at: datetime
    calendly_shown: bool