"""
Conversation Engine for TxAgent Agent Overhaul.

This module orchestrates the entire conversational flow for health tracking,
managing state transitions and coordinating data collection.
"""

import logging
import re
from typing import Dict, Any, Optional
from datetime import datetime

from simple_intent_detector import simple_intent_detector
from conversation_state import ConversationState, session_manager
from data_collectors import symptom_collector, treatment_collector, appointment_collector
from core.auth_service import auth_service

logger = logging.getLogger("conversation_engine")

class ConversationEngine:
    """Main conversation orchestrator for health tracking."""
    
    def __init__(self):
        self.intent_detector = simple_intent_detector
        self.session_manager = session_manager
        
        # Map collectors to their types
        self.collectors = {
            "symptom": symptom_collector,
            "treatment": treatment_collector,
            "appointment": appointment_collector
        }

    async def process_message(self, user_id: str, message: str, user_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user message and return appropriate response.
        
        Args:
            user_id: User identifier
            message: User's message
            user_profile: Optional user profile for personalization
            
        Returns:
            Response dictionary with message, questions, and metadata
        """
        logger.info(f"🚀 CONVERSATION_ENGINE: Processing message from user {user_id}: '{message}'")
        
        # Get or create session
        session = self.session_manager.get_or_create_session(user_id)
        
        # Handle based on current conversation state
        if session.state == ConversationState.IDLE:
            return await self._handle_new_conversation(session, message, user_profile)
        
        elif session.state == ConversationState.GREETING:
            return await self._handle_post_greeting(session, message)
        
        elif session.state in [ConversationState.COLLECTING_SYMPTOM, 
                              ConversationState.COLLECTING_TREATMENT,
                              ConversationState.COLLECTING_APPOINTMENT]:
            return await self._handle_data_collection(session, message)
        
        elif session.state == ConversationState.CONFIRMING_DATA:
            return await self._handle_confirmation(session, message)
        
        elif session.state == ConversationState.SAVING_DATA:
            return await self._handle_saving(session, message)
        
        else:
            return await self._handle_general_response(session, message)

    async def _handle_new_conversation(self, session, message: str, user_profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle the start of a new conversation."""
        logger.info(f"🆕 NEW_CONVERSATION: Starting new conversation for user {session.user_id}")
        
        # Detect intent
        intent_result = self.intent_detector.detect_intent(message)
        intent = intent_result["intent"]
        extracted_data = intent_result["extracted_data"]
        
        logger.info(f"🔍 INTENT: Detected '{intent}' with confidence {intent_result['confidence']}")
        
        if intent == "greeting":
            session.update_state(ConversationState.GREETING)
            name = ""
            if user_profile and user_profile.get("full_name"):
                name = f" {user_profile['full_name'].split()[0]}"  # First name only
            
            return {
                "message": f"Hello{name}! I'm here to help you track symptoms, medications, and appointments. How can I help you today?",
                "question": None,
                "session_id": None,
                "progress": 0,
                "complete": False
            }
        
        elif intent in ["symptom", "treatment", "appointment"]:
            # Start data collection
            return await self._start_data_collection(session, intent, message, extracted_data)
        
        elif intent == "history":
            # Handle history request
            return await self._handle_history_request(session, extracted_data)
        
        else:
            # Enhanced general conversation handling with symptom detection fallback
            return await self._handle_general_conversation(session, message)

    async def _handle_post_greeting(self, session, message: str) -> Dict[str, Any]:
        """Handle message after greeting."""
        logger.info(f"📝 POST_GREETING: Handling post-greeting message for user {session.user_id}")
        
        # Detect intent for what they want to do
        intent_result = self.intent_detector.detect_intent(message)
        intent = intent_result["intent"]
        extracted_data = intent_result["extracted_data"]
        
        if intent in ["symptom", "treatment", "appointment"]:
            return await self._start_data_collection(session, intent, message, extracted_data)
        else:
            # Enhanced fallback with symptom detection
            return await self._handle_general_conversation(session, message)

    async def _start_data_collection(self, session, intent: str, message: str, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Start data collection for the specified intent."""
        logger.info(f"📊 START_COLLECTION: Starting {intent} collection for user {session.user_id}")
        
        # Update session state
        if intent == "symptom":
            session.update_state(ConversationState.COLLECTING_SYMPTOM)
        elif intent == "treatment":
            session.update_state(ConversationState.COLLECTING_TREATMENT)
        elif intent == "appointment":
            session.update_state(ConversationState.COLLECTING_APPOINTMENT)
        
        session.current_collector = intent
        
        # Start collection with appropriate collector
        collector = self.collectors[intent]
        result = collector.start_collection(message, extracted_data)
        
        # Update session with collected data
        session.update_data(result["data"])
        
        # Track question if one was asked
        if result["question"]:
            question_type = self._determine_question_type(result["question"])
            session.add_question_asked(question_type)
        
        return {
            "message": result["message"],
            "question": result["question"],
            "session_id": f"{intent}_{session.user_id}_{int(session.created_at.timestamp())}",
            "progress": result["progress"],
            "complete": result["complete"]
        }

    async def _handle_data_collection(self, session, message: str) -> Dict[str, Any]:
        """Handle ongoing data collection."""
        logger.info(f"📊 DATA_COLLECTION: Continuing {session.current_collector} collection for user {session.user_id}")
        
        # Get the appropriate collector
        collector = self.collectors[session.current_collector]
        
        # Process the response
        result = collector.process_response(message, session.collected_data, session.questions_asked)
        
        # Update session with new data
        session.update_data(result["data"])
        
        # Track question if one was asked
        if result["question"] and not result["complete"]:
            question_type = self._determine_question_type(result["question"])
            session.add_question_asked(question_type)
        
        # Check if collection is complete
        if result["complete"]:
            session.update_state(ConversationState.CONFIRMING_DATA)
        
        return {
            "message": result["message"],
            "question": result["question"],
            "summary": result.get("summary"),
            "session_id": f"{session.current_collector}_{session.user_id}_{int(session.created_at.timestamp())}",
            "progress": result["progress"],
            "complete": result["complete"]
        }

    async def _handle_confirmation(self, session, message: str) -> Dict[str, Any]:
        """Handle user confirmation of collected data."""
        logger.info(f"✅ CONFIRMATION: Handling confirmation for user {session.user_id}")
        logger.info(f"✅ CONFIRMATION: Message: '{message}'")
        
        message_lower = message.lower().strip()
        
        # Check for positive confirmation
        if any(word in message_lower for word in ["yes", "y", "correct", "save", "looks good", "that's right"]):
            session.update_state(ConversationState.SAVING_DATA)
            return await self._save_data_to_database(session)
        
        # Check for explicit negative confirmation
        elif any(word in message_lower for word in ["no", "n", "wrong", "incorrect"]) and not self._contains_correction_data(message):
            # Reset to data collection state to handle corrections
            if session.current_collector == "symptom":
                session.update_state(ConversationState.COLLECTING_SYMPTOM)
            elif session.current_collector == "treatment":
                session.update_state(ConversationState.COLLECTING_TREATMENT)
            elif session.current_collector == "appointment":
                session.update_state(ConversationState.COLLECTING_APPOINTMENT)
            
            # Clear questions asked to allow re-collection
            session.questions_asked = []
            
            return {
                "message": "What would you like to change? Please tell me the correct information.",
                "question": None,
                "session_id": f"{session.current_collector}_{session.user_id}_{int(session.created_at.timestamp())}",
                "progress": session.completion_progress,
                "complete": False
            }
        
        # Check if the message contains correction data (numbers, time references, etc.)
        elif self._contains_correction_data(message):
            logger.info(f"✅ CONFIRMATION: Detected correction data in message")
            
            # Process the correction through the collector
            collector = self.collectors[session.current_collector]
            
            # Extract corrections from the message
            correction_data = self._extract_correction_data(message, session.current_collector)
            
            if correction_data:
                # Update session data with corrections
                session.update_data(correction_data)
                
                # Generate new confirmation with updated data
                result = collector._generate_completion(session.collected_data)
                
                return {
                    "message": result["message"],
                    "summary": result["summary"],
                    "question": result["question"],
                    "session_id": f"{session.current_collector}_{session.user_id}_{int(session.created_at.timestamp())}",
                    "progress": result["progress"],
                    "complete": result["complete"]
                }
        
        # Unclear response, ask again
        return {
            "message": "I didn't understand. Please say 'yes' to save this information or tell me what you'd like to change.",
            "question": None,
            "session_id": f"{session.current_collector}_{session.user_id}_{int(session.created_at.timestamp())}",
            "progress": session.completion_progress,
            "complete": False
        }

    def _contains_correction_data(self, message: str) -> bool:
        """Check if message contains correction data like numbers, time references, etc."""
        message_lower = message.lower()
        
        # Check for numbers (severity, duration)
        if re.search(r'\b\d+\b', message_lower):
            return True
        
        # Check for time references
        time_indicators = ["hour", "day", "week", "month", "morning", "afternoon", "evening", "yesterday", "today", "tomorrow"]
        if any(word in message_lower for word in time_indicators):
            return True
        
        # Check for location/body part references
        body_parts = ["head", "neck", "back", "chest", "stomach", "arm", "leg", "knee", "shoulder"]
        if any(word in message_lower for word in body_parts):
            return True
        
        # Check for medication/dosage references
        dosage_indicators = ["mg", "tablet", "pill", "capsule", "times", "daily", "twice", "once"]
        if any(word in message_lower for word in dosage_indicators):
            return True
        
        return False

    def _extract_correction_data(self, message: str, collector_type: str) -> Dict[str, Any]:
        """Extract correction data from user message."""
        logger.info(f"🔧 EXTRACT_CORRECTION: Extracting corrections from '{message}' for {collector_type}")
        
        collector = self.collectors[collector_type]
        
        # Use the collector's extraction method to get the corrections
        if hasattr(collector, '_extract_from_response'):
            corrections = collector._extract_from_response(message, {}, [])
            logger.info(f"🔧 EXTRACT_CORRECTION: Found corrections: {corrections}")
            return corrections
        
        return {}

    async def _save_data_to_database(self, session) -> Dict[str, Any]:
        """Save collected data to database."""
        logger.info(f"💾 SAVE_DATA: Saving {session.current_collector} data for user {session.user_id}")
        
        try:
            # Get the appropriate collector
            collector = self.collectors[session.current_collector]
            
            # Prepare data for database
            db_data = collector.prepare_for_database(session.collected_data)
            
            # Get authenticated client (we'll need JWT token from the calling context)
            # For now, we'll return the data and let the main endpoint handle the save
            session.update_state(ConversationState.COMPLETED)
            
            return {
                "message": f"{session.current_collector.title()} successfully saved to your health log!",
                "question": None,
                "session_id": None,
                "progress": 100,
                "complete": True,
                "save_data": {
                    "type": session.current_collector,
                    "data": db_data
                }
            }
            
        except Exception as e:
            logger.error(f"❌ SAVE_ERROR: Failed to save {session.current_collector} data: {str(e)}")
            return {
                "message": f"I'm sorry, there was an error saving your {session.current_collector}. Please try again.",
                "question": None,
                "session_id": f"{session.current_collector}_{session.user_id}_{int(session.created_at.timestamp())}",
                "progress": session.completion_progress,
                "complete": False
            }

    async def _handle_history_request(self, session, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request for health history."""
        logger.info(f"📚 HISTORY: Handling history request for user {session.user_id}")
        
        history_type = extracted_data.get("history_type", "all")
        
        return {
            "message": f"Let me retrieve your {history_type} history for you.",
            "question": None,
            "session_id": None,
            "progress": 0,
            "complete": False,
            "action_needed": "retrieve_history",
            "history_type": history_type
        }

    async def _handle_general_conversation(self, session, message: str) -> Dict[str, Any]:
        """Handle general conversation with enhanced symptom detection fallback."""
        logger.info(f"💬 GENERAL: Handling general conversation for user {session.user_id}")
        
        message_lower = message.lower().strip()
        
        # Enhanced symptom detection fallback - check for health-related terms
        health_indicators = [
            "hurt", "pain", "ache", "sore", "feel", "sick", "unwell", 
            "symptoms", "headache", "stomach", "back", "chest", "throat",
            "knee", "shoulder", "arm", "leg", "foot", "hand", "ear", "eye",
            "tooth", "neck", "fever", "nausea", "tired", "fatigue"
        ]
        
        # Check if the message contains health indicators
        contains_health_terms = any(
            re.search(r'\b' + re.escape(term) + r'\b', message_lower) 
            for term in health_indicators
        )
        
        if contains_health_terms:
            logger.info(f"🔍 GENERAL: Detected health terms in message, attempting symptom collection")
            # Force symptom collection even if initial intent detection missed it
            return await self._start_data_collection(session, "symptom", message, {})
        
        # Check if they're asking about capabilities
        if any(word in message_lower for word in ["what can you do", "help", "how do you work", "what do you do"]):
            return {
                "message": "I'm Symptom Savior, your health tracking assistant! I can help you:\n\n• Track symptoms (like headaches, pain, fever)\n• Log medications and treatments\n• Schedule and track doctor appointments\n\nJust tell me what you're experiencing, like 'I have a headache' or 'I'm taking ibuprofen'.",
                "question": None,
                "session_id": None,
                "progress": 0,
                "complete": False
            }
        
        # Check if they're asking about medication
        elif any(word in message_lower for word in ["medicine", "medication", "pill", "drug", "taking"]):
            return {
                "message": "I can help you track medications and treatments. Just tell me what you're taking, like 'I'm taking ibuprofen' or 'I started a new medication'.",
                "question": None,
                "session_id": None,
                "progress": 0,
                "complete": False
            }
        
        # Check if they're asking about appointments
        elif any(word in message_lower for word in ["doctor", "appointment", "visit", "checkup"]):
            return {
                "message": "I can help you track doctor appointments and visits. Just tell me about your appointment, like 'I have a doctor appointment tomorrow' or 'I saw Dr. Smith today'.",
                "question": None,
                "session_id": None,
                "progress": 0,
                "complete": False
            }
        
        # Default helpful response
        else:
            return {
                "message": "I'm here to help you track your health information. You can tell me about symptoms you're experiencing, medications you're taking, or doctor appointments you have. What would you like to track today?",
                "question": None,
                "session_id": None,
                "progress": 0,
                "complete": False
            }

    async def _handle_general_response(self, session, message: str) -> Dict[str, Any]:
        """Handle general conversation."""
        logger.info(f"💬 GENERAL: Handling general response for user {session.user_id}")
        
        return await self._handle_general_conversation(session, message)

    def _determine_question_type(self, question: str) -> str:
        """Determine what type of question is being asked."""
        question_lower = question.lower()
        
        if "severity" in question_lower or "scale" in question_lower:
            return "severity"
        elif "duration" in question_lower or "how long" in question_lower:
            return "duration_hours"
        elif "where" in question_lower or "location" in question_lower:
            return "location"
        elif "name" in question_lower:
            return "name"
        elif "doctor" in question_lower:
            return "doctor_name"
        elif "when" in question_lower or "time" in question_lower:
            return "visit_ts"
        elif "dosage" in question_lower or "frequency" in question_lower:
            return "dosage"
        elif "type" in question_lower:
            return "treatment_type"
        else:
            return "general"

    def reset_session(self, user_id: str):
        """Reset conversation session for user."""
        session = self.session_manager.get_session(user_id)
        if session:
            session.reset()
            logger.info(f"🔄 RESET: Reset session for user {user_id}")

    def end_session(self, user_id: str):
        """End conversation session for user."""
        self.session_manager.end_session(user_id)
        logger.info(f"🏁 END: Ended session for user {user_id}")

# Global conversation engine instance
conversation_engine = ConversationEngine()