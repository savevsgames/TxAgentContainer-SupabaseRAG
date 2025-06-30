"""
Conversation State Management for TxAgent Agent Overhaul.

This module manages conversation state and session data for
reliable conversational health tracking.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger("conversation_state")

class ConversationState(Enum):
    """Conversation state enumeration."""
    IDLE = "idle"
    GREETING = "greeting"
    COLLECTING_SYMPTOM = "collecting_symptom"
    COLLECTING_TREATMENT = "collecting_treatment"
    COLLECTING_APPOINTMENT = "collecting_appointment"
    CONFIRMING_DATA = "confirming_data"
    SAVING_DATA = "saving_data"
    COMPLETED = "completed"

class ConversationSession:
    """Represents a conversation session with a user."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.state = ConversationState.IDLE
        self.current_collector = None
        self.collected_data = {}
        self.questions_asked = []
        self.created_at = datetime.now()
        self.last_updated = datetime.now()
        self.completion_progress = 0
        
    def update_state(self, new_state: ConversationState):
        """Update conversation state."""
        logger.info(f"🔄 STATE: User {self.user_id} state change: {self.state.value} -> {new_state.value}")
        self.state = new_state
        self.last_updated = datetime.now()
    
    def update_data(self, new_data: Dict[str, Any]):
        """Update collected data."""
        self.collected_data.update(new_data)
        self.last_updated = datetime.now()
        logger.info(f"📊 DATA: User {self.user_id} data updated: {self.collected_data}")
    
    def add_question_asked(self, question_type: str):
        """Track what questions have been asked."""
        if question_type not in self.questions_asked:
            self.questions_asked.append(question_type)
            logger.info(f"❓ QUESTION: User {self.user_id} asked about: {question_type}")
    
    def calculate_progress(self, required_fields: list, optional_fields: list = None) -> int:
        """Calculate completion progress as percentage."""
        if optional_fields is None:
            optional_fields = []
        
        total_fields = len(required_fields) + min(2, len(optional_fields))  # Max 2 optional
        filled_fields = 0
        
        for field in required_fields:
            if field in self.collected_data:
                filled_fields += 1
        
        # Count up to 2 optional fields
        optional_count = 0
        for field in optional_fields:
            if field in self.collected_data and optional_count < 2:
                filled_fields += 1
                optional_count += 1
        
        self.completion_progress = int((filled_fields / total_fields) * 100) if total_fields > 0 else 0
        return self.completion_progress
    
    def is_complete(self, required_fields: list) -> bool:
        """Check if all required fields are collected."""
        return all(field in self.collected_data for field in required_fields)
    
    def reset(self):
        """Reset session for new conversation."""
        self.state = ConversationState.IDLE
        self.current_collector = None
        self.collected_data = {}
        self.questions_asked = []
        self.completion_progress = 0
        self.last_updated = datetime.now()
        logger.info(f"🔄 RESET: User {self.user_id} session reset")

class ConversationSessionManager:
    """Manages conversation sessions for all users."""
    
    def __init__(self):
        # In-memory storage for sessions
        # In production, this would be Redis or similar
        self.sessions: Dict[str, ConversationSession] = {}
        
    def get_or_create_session(self, user_id: str) -> ConversationSession:
        """Get existing session or create new one."""
        if user_id not in self.sessions:
            self.sessions[user_id] = ConversationSession(user_id)
            logger.info(f"🆕 SESSION: Created new session for user {user_id}")
        else:
            logger.info(f"📋 SESSION: Retrieved existing session for user {user_id}")
        
        return self.sessions[user_id]
    
    def get_session(self, user_id: str) -> Optional[ConversationSession]:
        """Get existing session without creating new one."""
        return self.sessions.get(user_id)
    
    def end_session(self, user_id: str):
        """End and clean up session."""
        if user_id in self.sessions:
            del self.sessions[user_id]
            logger.info(f"🗑️ SESSION: Ended session for user {user_id}")
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Clean up old sessions to prevent memory leaks."""
        current_time = datetime.now()
        expired_users = []
        
        for user_id, session in self.sessions.items():
            age_hours = (current_time - session.last_updated).total_seconds() / 3600
            if age_hours > max_age_hours:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            del self.sessions[user_id]
            logger.info(f"🧹 CLEANUP: Removed expired session for user {user_id}")
        
        if expired_users:
            logger.info(f"🧹 CLEANUP: Removed {len(expired_users)} expired sessions")

# Global session manager
session_manager = ConversationSessionManager()