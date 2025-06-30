"""
Conversation Manager for TxAgent Agent Awareness Phase 2.

This module manages conversation flow, context, and intelligent response generation
for natural symptom tracking conversations with improved bedside manner.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json

from nlp_processor import AdvancedNLPProcessor
from symptom_tracker import symptom_tracker

logger = logging.getLogger("conversation_manager")

class ConversationManager:
    """Manages conversation flow and context for intelligent symptom tracking with improved bedside manner."""
    
    def __init__(self):
        self.nlp_processor = AdvancedNLPProcessor()
        
        # Response templates for different conversation stages
        self.response_templates = {
            "greeting": [
                "Hello! I'm here to help you with any health-related questions or to assist with tracking your symptoms. How can I help you today?",
                "Hi there! I can help you track symptoms, answer health questions, or provide medical information. What would you like to discuss?",
                "Hello! How can I assist you with your health today?"
            ],
            "general_health_info": [
                "That's a great question about {topic}. Let me provide some helpful information.",
                "I'd be happy to help explain {topic} for you.",
                "Here's some information about {topic} that might be helpful."
            ],
            "symptom_tracking_start": [
                "I'd like to help you track your symptom. Let me ask you a few questions to get the details right.",
                "I can help you log that symptom. I'll need to gather some information first.",
                "Let me help you track this symptom properly."
            ],
            "emergency_response": [
                "🚨 URGENT: Based on your symptoms, this may require immediate medical attention. Please contact emergency services (911) or go to the nearest emergency room immediately.",
                "🚨 This sounds like it could be a medical emergency. Please seek immediate medical attention by calling 911 or going to the nearest emergency room."
            ]
        }
        
        # Context-aware medical advice templates
        self.medical_advice_templates = {
            "headache": {
                "general": "For headaches, staying hydrated, getting adequate rest, and managing stress can be helpful.",
                "severe": "Severe headaches (8+/10) may require medical attention, especially if they're sudden or different from usual.",
                "chronic": "Frequent headaches may benefit from identifying triggers and consulting with a healthcare provider."
            },
            "fever": {
                "general": "For fever, rest, hydration, and monitoring temperature are important.",
                "high": "High fever (over 101°F/38.3°C) or fever lasting more than 3 days should be evaluated by a healthcare provider.",
                "with_symptoms": "Fever with severe symptoms like difficulty breathing or persistent vomiting needs immediate medical attention."
            },
            "pain": {
                "general": "For pain management, rest, appropriate positioning, and over-the-counter pain relievers may help.",
                "severe": "Severe pain (8+/10) or pain that interferes with daily activities should be evaluated by a healthcare provider.",
                "chronic": "Persistent pain lasting more than a few days may require medical evaluation."
            }
        }

    def process_conversation_turn(
        self, 
        query: str, 
        conversation_history: List[Dict[str, str]], 
        user_profile: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a conversation turn and determine the appropriate response strategy.
        
        Args:
            query: User's current query
            conversation_history: Previous conversation messages
            user_profile: User's medical profile
            user_id: User ID for session management
            
        Returns:
            Conversation processing result with response strategy
        """
        logger.info(f"🔍 CONVERSATION: Processing turn: {query[:100]}...")
        
        # Analyze conversation flow
        flow_analysis = self.nlp_processor.analyze_conversation_flow(query, conversation_history)
        
        # Extract comprehensive symptom data
        symptom_data = self.nlp_processor.extract_comprehensive_symptom_data(query, conversation_history)
        
        # Determine conversation strategy with improved logic
        strategy = self._determine_conversation_strategy(flow_analysis, symptom_data, user_profile, query)
        
        # Generate appropriate response based on strategy
        if strategy.get("type") == "symptom_tracking_loop":
            # Use the new symptom tracking loop
            response_data = self._handle_symptom_tracking_loop(query, symptom_data, user_id, strategy)
        else:
            # Use existing response generation
            response_data = self._generate_contextual_response(strategy, symptom_data, flow_analysis, user_profile, query)
        
        result = {
            "strategy": strategy,
            "symptom_data": symptom_data,
            "flow_analysis": flow_analysis,
            "response_data": response_data,
            "should_log_symptom": strategy.get("action") == "log_symptom",
            "follow_up_needed": len(symptom_data.get("missing_details", [])) > 0
        }
        
        logger.info(f"✅ CONVERSATION: Strategy determined: {strategy.get('type', 'unknown')}")
        return result

    def _determine_conversation_strategy(
        self, 
        flow_analysis: Dict[str, Any], 
        symptom_data: Dict[str, Any], 
        user_profile: Optional[Dict[str, Any]],
        query: str
    ) -> Dict[str, Any]:
        """Determine the appropriate conversation strategy with improved bedside manner."""
        
        strategy = {
            "type": "general_conversation",  # Default to general conversation
            "action": None,
            "priority": "normal",
            "confidence": 0.5
        }
        
        query_lower = query.lower()
        
        # 1. GREETING DETECTION
        if self._is_greeting(query_lower):
            strategy["type"] = "greeting"
            strategy["confidence"] = 0.9
            return strategy
        
        # 2. EMERGENCY DETECTION (Highest Priority)
        if self._detect_emergency_indicators(symptom_data, user_profile):
            strategy["type"] = "emergency_response"
            strategy["action"] = "alert_emergency"
            strategy["priority"] = "critical"
            strategy["confidence"] = 0.95
            return strategy
        
        # 3. SYMPTOM TRACKING INTENT (New conversational loop)
        if self._is_symptom_tracking_intent(query_lower, symptom_data):
            strategy["type"] = "symptom_tracking_loop"
            strategy["action"] = "start_tracking_loop"
            strategy["confidence"] = 0.9
            strategy["priority"] = "high"
            return strategy
        
        # 4. SYMPTOM HISTORY REQUESTS
        if self._is_symptom_history_request(symptom_data.get("description", "")):
            strategy["type"] = "symptom_history"
            strategy["action"] = "get_symptom_history"
            strategy["confidence"] = 0.9
            strategy["priority"] = "high"
            return strategy
        
        # 5. GENERAL HEALTH INFORMATION
        if self._is_general_health_question(query_lower):
            strategy["type"] = "health_information"
            strategy["confidence"] = 0.8
            strategy["priority"] = "normal"
            return strategy
        
        # 6. GENERAL CONVERSATION (Default)
        strategy["type"] = "general_conversation"
        strategy["confidence"] = 0.6
        strategy["priority"] = "normal"
        
        return strategy

    def _is_greeting(self, query_lower: str) -> bool:
        """Check if this is a greeting."""
        greetings = [
            "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
            "how are you", "what's up", "greetings"
        ]
        return any(greeting in query_lower for greeting in greetings)

    def _is_symptom_tracking_intent(self, query_lower: str, symptom_data: Dict[str, Any]) -> bool:
        """Check if user wants to track a symptom."""
        tracking_indicators = [
            "log", "track", "record", "save", "add", "i have", "i'm having",
            "experiencing", "feeling", "symptom", "pain", "hurt", "ache"
        ]
        
        # Must have either explicit tracking language OR a symptom name
        has_tracking_language = any(indicator in query_lower for indicator in tracking_indicators[:7])
        has_symptom_mention = any(indicator in query_lower for indicator in tracking_indicators[7:])
        has_symptom_name = symptom_data.get("symptom_name") is not None
        
        return has_tracking_language or (has_symptom_mention and has_symptom_name)

    def _handle_symptom_tracking_loop(
        self, 
        query: str, 
        symptom_data: Dict[str, Any], 
        user_id: str,
        strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle the new symptom tracking conversational loop."""
        
        # Check if this is continuing an existing session
        # For now, always start a new session - in production, you'd check for active sessions
        
        # Start new tracking session
        tracking_result = symptom_tracker.start_symptom_tracking(user_id, query)
        
        message = tracking_result["message"]
        if tracking_result.get("next_question"):
            message += f"\n\n❓ {tracking_result['next_question']}"
        
        return {
            "message": message,
            "tracking_session_id": tracking_result["session_id"],
            "progress": tracking_result["progress"],
            "follow_up_questions": [tracking_result.get("next_question")] if tracking_result.get("next_question") else [],
            "medical_advice": "",
            "urgency_level": "normal"
        }

    def _generate_contextual_response(
        self, 
        strategy: Dict[str, Any], 
        symptom_data: Dict[str, Any], 
        flow_analysis: Dict[str, Any], 
        user_profile: Optional[Dict[str, Any]],
        original_query: str
    ) -> Dict[str, Any]:
        """Generate contextual response based on strategy and data."""
        
        response_data = {
            "message": "",
            "follow_up_questions": [],
            "medical_advice": "",
            "urgency_level": "normal"
        }
        
        strategy_type = strategy.get("type")
        
        if strategy_type == "greeting":
            response_data = self._generate_greeting_response()
        
        elif strategy_type == "emergency_response":
            response_data = self._generate_emergency_response(symptom_data, user_profile)
        
        elif strategy_type == "symptom_history":
            response_data = self._generate_history_response(symptom_data)
        
        elif strategy_type == "health_information":
            response_data = self._generate_health_information_response(symptom_data, user_profile, original_query)
        
        else:  # general_conversation
            response_data = self._generate_general_conversation_response(original_query, flow_analysis)
        
        return response_data

    def _generate_greeting_response(self) -> Dict[str, Any]:
        """Generate a friendly greeting response."""
        return {
            "message": self.response_templates["greeting"][0],
            "follow_up_questions": [],
            "medical_advice": "",
            "urgency_level": "normal"
        }

    def _generate_general_conversation_response(
        self, 
        original_query: str, 
        flow_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate response for general conversation without medical action."""
        
        query_lower = original_query.lower()
        
        # Handle "how are you" type questions
        if any(phrase in query_lower for phrase in ["how are you", "how's it going", "what's up"]):
            message = "I'm here and ready to help! I can assist with health questions, symptom tracking, or provide medical information. What would you like to discuss?"
        
        # Handle general questions about the service
        elif any(phrase in query_lower for phrase in ["what can you do", "help me", "what do you do"]):
            message = "I can help you in several ways:\n\n• Answer general health questions\n• Track and log your symptoms\n• Provide information from your medical documents\n• Help you understand medical conditions\n\nWhat would you like to start with?"
        
        # Default friendly response
        else:
            message = "I'm here to help with your health-related questions or symptom tracking. What can I assist you with?"
        
        return {
            "message": message,
            "follow_up_questions": [],
            "medical_advice": "",
            "urgency_level": "normal"
        }

    def _generate_emergency_response(
        self, 
        symptom_data: Dict[str, Any], 
        user_profile: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate emergency response."""
        
        return {
            "message": self.response_templates["emergency_response"][0],
            "follow_up_questions": [],
            "medical_advice": "Do not delay seeking emergency medical care. These symptoms can indicate a serious medical condition that needs prompt evaluation.",
            "urgency_level": "critical"
        }

    def _generate_history_response(self, symptom_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate response for symptom history requests."""
        
        return {
            "message": "Let me retrieve your symptom history for you.",
            "follow_up_questions": [],
            "medical_advice": "",
            "urgency_level": "normal",
            "action_needed": "retrieve_history"
        }

    def _generate_health_information_response(
        self, 
        symptom_data: Dict[str, Any], 
        user_profile: Optional[Dict[str, Any]],
        original_query: str
    ) -> Dict[str, Any]:
        """Generate health information response."""
        
        # Extract topic from query for more personalized response
        topic = "that topic"
        query_lower = original_query.lower()
        
        # Try to identify the health topic
        health_topics = ["cold", "flu", "fever", "headache", "pain", "medication", "treatment", "symptoms"]
        for topic_word in health_topics:
            if topic_word in query_lower:
                topic = topic_word
                break
        
        template = self.response_templates["general_health_info"][0]
        message = template.format(topic=topic)
        
        medical_advice = self._get_contextual_medical_advice(symptom_data, user_profile)
        
        return {
            "message": message,
            "follow_up_questions": ["Are you experiencing any symptoms yourself, or is this just general information you're looking for?"],
            "medical_advice": medical_advice,
            "urgency_level": "normal"
        }

    def _is_symptom_history_request(self, description: str) -> bool:
        """Check if this is a symptom history request."""
        history_indicators = [
            "show me my", "my history", "my symptoms", "what symptoms", "symptom log",
            "previous symptoms", "past symptoms", "history of", "logged symptoms"
        ]
        return any(indicator in description.lower() for indicator in history_indicators)

    def _get_contextual_medical_advice(
        self, 
        symptom_data: Dict[str, Any], 
        user_profile: Optional[Dict[str, Any]]
    ) -> str:
        """Get contextual medical advice based on symptom and user profile."""
        
        symptom_name = symptom_data.get("symptom_name", "").lower()
        severity = symptom_data.get("severity")
        
        # Ensure severity is an integer for comparisons
        if severity is None:
            severity = 0
        
        # Find matching advice template
        advice_category = None
        for category in self.medical_advice_templates:
            if category in symptom_name:
                advice_category = category
                break
        
        if not advice_category:
            return "💡 This information is for educational purposes only and is not a substitute for professional medical advice."
        
        advice_templates = self.medical_advice_templates[advice_category]
        
        # Choose appropriate advice based on severity and context
        if severity >= 8:
            advice = advice_templates.get("severe", advice_templates["general"])
        elif self._is_chronic_symptom(symptom_data, user_profile):
            advice = advice_templates.get("chronic", advice_templates["general"])
        else:
            advice = advice_templates["general"]
        
        # Add standard disclaimer
        advice = f"💡 {advice} This information is for educational purposes only and is not a substitute for professional medical advice."
        
        return advice

    def _detect_emergency_indicators(
        self, 
        symptom_data: Dict[str, Any], 
        user_profile: Optional[Dict[str, Any]]
    ) -> bool:
        """Detect emergency indicators in symptom data."""
        
        emergency_keywords = [
            "chest pain", "difficulty breathing", "severe bleeding", "unconscious",
            "heart attack", "stroke", "severe allergic reaction", "poisoning",
            "can't breathe", "trouble breathing", "choking"
        ]
        
        description = symptom_data.get("description", "").lower()
        severity = symptom_data.get("severity")
        
        # Ensure severity is an integer for comparisons
        if severity is None:
            severity = 0
        
        # Check for emergency keywords
        if any(keyword in description for keyword in emergency_keywords):
            return True
        
        # Check for very high severity with concerning symptoms
        if severity >= 9:
            concerning_symptoms = ["chest pain", "breathing", "heart", "severe pain"]
            if any(symptom in description for symptom in concerning_symptoms):
                return True
        
        return False

    def _is_general_health_question(self, description: str) -> bool:
        """Check if this is a general health question rather than symptom logging."""
        
        question_indicators = [
            "what is", "how do", "why does", "can you explain", "tell me about",
            "information about", "learn about", "understand", "difference between"
        ]
        
        return any(indicator in description.lower() for indicator in question_indicators)

    def _is_chronic_symptom(
        self, 
        symptom_data: Dict[str, Any], 
        user_profile: Optional[Dict[str, Any]]
    ) -> bool:
        """Check if this appears to be a chronic symptom."""
        
        duration_hours = symptom_data.get("duration_hours", 0)
        frequency = symptom_data.get("frequency", "")
        
        # Check for chronic indicators
        if duration_hours > 168:  # More than a week
            return True
        
        if any(word in frequency.lower() for word in ["daily", "every day", "chronic", "ongoing"]):
            return True
        
        # Check user profile for chronic conditions
        if user_profile and user_profile.get("conditions"):
            chronic_conditions = ["chronic pain", "migraine", "arthritis", "fibromyalgia"]
            user_conditions = [cond.lower() for cond in user_profile["conditions"]]
            if any(condition in " ".join(user_conditions) for condition in chronic_conditions):
                return True
        
        return False

    def enhance_response_with_context(
        self, 
        base_response: str, 
        conversation_result: Dict[str, Any], 
        agent_action_result: Optional[Dict[str, Any]] = None
    ) -> str:
        """Enhance the base response with conversation context and agent actions."""
        
        response_data = conversation_result.get("response_data", {})
        message = response_data.get("message", "")
        medical_advice = response_data.get("medical_advice", "")
        urgency_level = response_data.get("urgency_level", "normal")
        
        # Start with the conversation manager's message if available, otherwise use base response
        if message:
            enhanced_response = message
        else:
            enhanced_response = base_response
        
        # Add medical advice if available
        if medical_advice:
            enhanced_response += f"\n\n{medical_advice}"
        
        # Add urgency indicators
        if urgency_level == "critical":
            enhanced_response = f"🚨 URGENT: {enhanced_response}"
        elif urgency_level == "high":
            enhanced_response = f"⚠️ Important: {enhanced_response}"
        
        return enhanced_response

    def continue_symptom_tracking(
        self, 
        session_id: str, 
        user_response: str, 
        user_id: str
    ) -> Dict[str, Any]:
        """Continue an existing symptom tracking session."""
        
        # Update the tracking session with user's response
        tracking_result = symptom_tracker.update_symptom_data(session_id, user_response)
        
        if tracking_result.get("error"):
            return {
                "message": "I'm sorry, I lost track of our conversation. Let's start over with your symptom.",
                "follow_up_questions": [],
                "medical_advice": "",
                "urgency_level": "normal"
            }
        
        if tracking_result.get("status") == "complete":
            # Session is complete, show summary and ask for confirmation
            message = tracking_result["message"]
            if tracking_result.get("summary"):
                message += f"\n\n{tracking_result['summary']}"
            if tracking_result.get("confirmation_question"):
                message += f"\n\n❓ {tracking_result['confirmation_question']}"
            
            return {
                "message": message,
                "tracking_session_id": session_id,
                "status": "awaiting_confirmation",
                "db_data": tracking_result.get("db_data"),
                "follow_up_questions": [],
                "medical_advice": "",
                "urgency_level": "normal"
            }
        else:
            # Continue with next question
            message = tracking_result.get("message", "Got it.")
            if tracking_result.get("next_question"):
                message += f"\n\n❓ {tracking_result['next_question']}"
            
            return {
                "message": message,
                "tracking_session_id": session_id,
                "progress": tracking_result.get("progress"),
                "current_data": tracking_result.get("current_data"),
                "follow_up_questions": [],
                "medical_advice": "",
                "urgency_level": "normal"
            }