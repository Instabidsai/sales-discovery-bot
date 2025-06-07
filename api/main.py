"""FastAPI application for Sales Discovery Bot."""

import os
import uuid
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, generate_latest
import asyncpg
import redis.asyncio as redis

from agent import SalesDiscoveryAgent, AgentConfig
from .database import DatabaseManager
from .models import (
    ChatRequest, ChatResponse, ConversationResponse,
    ConversationListResponse
)

# Initialize FastAPI app
app = FastAPI(
    title="Sales Discovery Bot API",
    description="AI-powered sales discovery agent for Insta Agents",
    version="1.0.0"
)

# Add CORS middleware for web embedding
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Metrics
conversations_started = Counter(
    "conversations_started_total",
    "Total conversations initiated"
)
conversations_completed = Counter(
    "conversations_completed_total",
    "Conversations reaching proposal stage"
)
demos_booked = Counter(
    "demos_booked_total",
    "Successful Calendly redirects"
)
response_time = Histogram(
    "response_time_seconds",
    "Time to generate response"
)

# Global instances
agent: Optional[SalesDiscoveryAgent] = None
db: Optional[DatabaseManager] = None
redis_client: Optional[redis.Redis] = None


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global agent, db, redis_client
    
    # Initialize configuration
    config = AgentConfig()
    
    # Initialize agent
    agent = SalesDiscoveryAgent(config)
    
    # Initialize database
    db = DatabaseManager(config.postgres_dsn)
    await db.initialize()
    
    # Initialize Redis
    redis_client = redis.from_url(config.redis_url)
    
    # Run migrations
    await db.run_migrations()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    if db:
        await db.close()
    if redis_client:
        await redis_client.close()


@app.get("/health")
async def health():
    """Health check endpoint."""
    checks = {
        "api": "healthy",
        "agent": agent is not None,
        "database": False,
        "redis": False
    }
    
    # Check database
    try:
        if db:
            await db.health_check()
            checks["database"] = True
    except:
        pass
    
    # Check Redis
    try:
        if redis_client:
            await redis_client.ping()
            checks["redis"] = True
    except:
        pass
    
    status = "healthy" if all(checks.values()) else "unhealthy"
    
    return {
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "checks": checks
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a chat message."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    with response_time.time():
        # Generate conversation ID if not provided
        conversation_id = request.conversation_id or str(uuid.uuid4())
        
        # Track new conversations
        is_new = request.conversation_id is None
        if is_new:
            conversations_started.inc()
            # Store conversation metadata
            await db.create_conversation(
                conversation_id=conversation_id,
                source=request.source
            )
        
        # Process message
        result = await agent.process_message(
            conversation_id=conversation_id,
            message=request.message,
            source=request.source
        )
        
        # Store message in database
        await db.add_message(
            conversation_id=conversation_id,
            role="human",
            content=request.message
        )
        await db.add_message(
            conversation_id=conversation_id,
            role="ai",
            content=result["response"]
        )
        
        # Update conversation state
        await db.update_conversation_state(
            conversation_id=conversation_id,
            state=result
        )
        
        # Track completions
        if result.get("stage") == "propose":
            conversations_completed.inc()
        elif result.get("calendly_shown"):
            demos_booked.inc()
            # Create lead record
            await db.create_lead(
                conversation_id=conversation_id,
                mvp_proposal=result.get("mvp_proposal"),
                partnership_tier=result.get("partnership_tier")
            )
        
        return ChatResponse(
            conversation_id=conversation_id,
            response=result["response"],
            stage=result.get("stage"),
            calendly_shown=result.get("calendly_shown", False)
        )


@app.get("/conversation/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str):
    """Get conversation history."""
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    conversation = await db.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = await db.get_messages(conversation_id)
    
    return ConversationResponse(
        conversation_id=conversation_id,
        messages=messages,
        state=conversation.get("state", {}),
        created_at=conversation["created_at"],
        updated_at=conversation["updated_at"]
    )


@app.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    source: Optional[str] = None
):
    """List all conversations (admin endpoint)."""
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    conversations = await db.list_conversations(
        limit=limit,
        offset=offset,
        source=source
    )
    
    return ConversationListResponse(
        conversations=conversations,
        total=len(conversations),
        limit=limit,
        offset=offset
    )


@app.get("/widget.js")
async def widget_script():
    """Serve the embeddable widget script."""
    widget_js = """
(function() {
    window.InstaAgentsChat = {
        init: function(config) {
            const defaults = {
                position: 'bottom-right',
                theme: 'light',
                apiUrl: window.location.origin
            };
            const settings = Object.assign({}, defaults, config);
            
            // Create chat widget iframe
            const iframe = document.createElement('iframe');
            iframe.id = 'insta-agents-chat';
            iframe.src = settings.apiUrl + '/widget';
            iframe.style.cssText = `
                position: fixed;
                ${settings.position.includes('bottom') ? 'bottom: 20px' : 'top: 20px'};
                ${settings.position.includes('right') ? 'right: 20px' : 'left: 20px'};
                width: 400px;
                height: 600px;
                border: none;
                border-radius: 10px;
                box-shadow: 0 0 20px rgba(0,0,0,0.1);
                z-index: 9999;
                display: none;
            `;
            
            // Create toggle button
            const button = document.createElement('button');
            button.id = 'insta-agents-toggle';
            button.innerHTML = '💬';
            button.style.cssText = `
                position: fixed;
                ${settings.position.includes('bottom') ? 'bottom: 20px' : 'top: 20px'};
                ${settings.position.includes('right') ? 'right: 20px' : 'left: 20px'};
                width: 60px;
                height: 60px;
                border-radius: 50%;
                background: #2563eb;
                color: white;
                border: none;
                font-size: 24px;
                cursor: pointer;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                z-index: 9998;
            `;
            
            button.onclick = function() {
                const isVisible = iframe.style.display === 'block';
                iframe.style.display = isVisible ? 'none' : 'block';
                button.style.display = isVisible ? 'block' : 'none';
            };
            
            // Add to page
            document.body.appendChild(iframe);
            document.body.appendChild(button);
            
            // Message passing
            window.addEventListener('message', function(event) {
                if (event.data.type === 'insta-agents-resize') {
                    iframe.style.height = event.data.height + 'px';
                }
            });
        }
    };
})();
"""
    return Response(content=widget_js, media_type="application/javascript")


@app.get("/widget")
async def widget_html():
    """Serve the widget HTML interface."""
    html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Insta Agents Chat</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        
        .chat-container {
            height: 100vh;
            display: flex;
            flex-direction: column;
            background: #f9fafb;
        }
        
        .chat-header {
            background: #2563eb;
            color: white;
            padding: 1rem;
            font-weight: 600;
        }
        
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
        }
        
        .message {
            margin-bottom: 1rem;
            display: flex;
            gap: 0.5rem;
        }
        
        .message.ai { justify-content: flex-start; }
        .message.human { justify-content: flex-end; }
        
        .message-bubble {
            max-width: 80%;
            padding: 0.75rem 1rem;
            border-radius: 1rem;
        }
        
        .message.ai .message-bubble {
            background: white;
            border: 1px solid #e5e7eb;
        }
        
        .message.human .message-bubble {
            background: #2563eb;
            color: white;
        }
        
        .chat-input {
            padding: 1rem;
            background: white;
            border-top: 1px solid #e5e7eb;
        }
        
        .input-group {
            display: flex;
            gap: 0.5rem;
        }
        
        input {
            flex: 1;
            padding: 0.75rem;
            border: 1px solid #e5e7eb;
            border-radius: 0.5rem;
            font-size: 1rem;
        }
        
        button {
            padding: 0.75rem 1.5rem;
            background: #2563eb;
            color: white;
            border: none;
            border-radius: 0.5rem;
            font-weight: 500;
            cursor: pointer;
        }
        
        button:hover { background: #1d4ed8; }
        button:disabled { background: #9ca3af; cursor: not-allowed; }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            🤖 Insta Agents - AI Partnership Discovery
        </div>
        
        <div class="chat-messages" id="messages">
            <div class="message ai">
                <div class="message-bubble">
                    Hi! I'm here to help you discover how AI can transform your business. 
                    Let's start with a quick question - what does your business do?
                </div>
            </div>
        </div>
        
        <div class="chat-input">
            <form id="chat-form" class="input-group">
                <input 
                    type="text" 
                    id="message-input" 
                    placeholder="Type your message..."
                    autocomplete="off"
                    required
                />
                <button type="submit" id="send-button">Send</button>
            </form>
        </div>
    </div>
    
    <script>
        const messagesEl = document.getElementById('messages');
        const formEl = document.getElementById('chat-form');
        const inputEl = document.getElementById('message-input');
        const buttonEl = document.getElementById('send-button');
        
        let conversationId = localStorage.getItem('insta-agents-conversation-id');
        
        function addMessage(content, role) {
            const messageEl = document.createElement('div');
            messageEl.className = `message ${role}`;
            
            const bubbleEl = document.createElement('div');
            bubbleEl.className = 'message-bubble';
            bubbleEl.textContent = content;
            
            messageEl.appendChild(bubbleEl);
            messagesEl.appendChild(messageEl);
            messagesEl.scrollTop = messagesEl.scrollHeight;
        }
        
        async function sendMessage(message) {
            // Disable form
            inputEl.disabled = true;
            buttonEl.disabled = true;
            
            // Add user message
            addMessage(message, 'human');
            
            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        conversation_id: conversationId,
                        message: message,
                        source: 'widget'
                    })
                });
                
                const data = await response.json();
                
                // Store conversation ID
                if (!conversationId) {
                    conversationId = data.conversation_id;
                    localStorage.setItem('insta-agents-conversation-id', conversationId);
                }
                
                // Add AI response
                addMessage(data.response, 'ai');
                
                // Check if Calendly link shown
                if (data.calendly_shown && data.response.includes('calendly.com')) {
                    setTimeout(() => {
                        if (confirm('Ready to book your demo?')) {
                            window.open(data.response.match(/https:\/\/calendly\.com[^\s]+/)[0], '_blank');
                        }
                    }, 1000);
                }
                
            } catch (error) {
                addMessage('Sorry, I encountered an error. Please try again.', 'ai');
            } finally {
                // Re-enable form
                inputEl.disabled = false;
                buttonEl.disabled = false;
                inputEl.value = '';
                inputEl.focus();
            }
        }
        
        formEl.addEventListener('submit', async (e) => {
            e.preventDefault();
            const message = inputEl.value.trim();
            if (message) {
                await sendMessage(message);
            }
        });
        
        // Focus input on load
        inputEl.focus();
        
        // Notify parent of size
        window.parent.postMessage({
            type: 'insta-agents-resize',
            height: document.body.scrollHeight
        }, '*');
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html)