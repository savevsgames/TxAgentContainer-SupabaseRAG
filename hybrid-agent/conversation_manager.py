"""
Conversation Manager for TxAgent Agent Awareness Phase 2.

This module manages conversation flow, context, and intelligent response generation
for natural symptom tracking conversations.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json

from nlp_processor import AdvancedNLPProcessor

logger = logging.getLogger("conversation_manager")

class ConversationManager:
    """Manages conversation flow and context for intelligent symptom tracking."""
    
    def __init__(self):
        self.nlp_processor = AdvancedNLPProcessor()
        
        # Response templates for different conversation stages
        self.response_templates = {
            "symptom_logged_complete": [
                "✅ I've successfully logged your {symptom_name} with a severity of {severity}/10. {additional_info}",
                "✅ Your {symptom_name} has been recorded in your symptom history. {additional_info}",
                "✅ I've added your {symptom_name} to your health log. {additional_info}"
            ],
            "symptom_logged_partial": [
                "✅ I've logged your {symptom_name}. {follow_up_question}",
                "✅ Your {symptom_name} has been recorded. {follow_up_question}",
                "✅ I've noted your {symptom_name}. {follow_up_question}"
            ],
            "clarifying_questions": [
                "I'd like to help you track this symptom. {question}",
                "To better understand your symptoms, {question}",
                "Let me gather some more details. {question}"
            ],
            "follow_up_questions": [
                "I've recorded that information. {question}",
                "Thank you for that detail. {question}",
                "Got it. {question}"
            ],
            "symptom_history_summary": [
                "📊 I found {count} symptom entries in your history. {summary}",
                "📊 Your symptom log shows {count} entries. {summary}",
                "📊 Looking at your health history, I see {count} symptoms recorded. {summary}"
            ],
            "no_symptoms_found": [
                "📊 I don't see any symptoms in your history yet. You can start tracking by telling me about any symptoms you're experiencing.",
                "📊 Your symptom log is empty. Feel free to share any symptoms you'd like to track.",
                "📊 No symptoms recorded yet. I'm here to help you start tracking your health."
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
        user_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a conversation turn and determine the appropriate response strategy.
        
        Args:
            query: User's current query
            conversation_history: Previous conversation messages
            user_profile: User's medical profile
            
        Returns:
            Conversation processing result with response strategy
        """
        logger.info(f"🔍 CONVERSATION: Processing turn: {query[:100]}...")
        
        # Analyze conversation flow
        flow_analysis = self.nlp_processor.analyze_conversation_flow(query, conversation_history)
        
        # Extract comprehensive symptom data
        symptom_data = self.nlp_processor.extract_comprehensive_symptom_data(query, conversation_history)
        
        # Determine conversation strategy
        strategy = self._determine_conversation_strategy(flow_analysis, symptom_data, user_profile)
        
        # Generate appropriate response
        response_data = self._generate_contextual_response(strategy, symptom_data, flow_analysis, user_profile)
        
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
        user_profile: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Determine the appropriate conversation strategy."""
        
        strategy = {
            "type": "clarifying_question",
            "action": None,
            "priority": "medium",
            "confidence": 0.5
        }
        
        # Check if we have enough information to log a symptom
        if symptom_data.get("symptom_name") and flow_analysis["information_completeness"] > 0.4:
            strategy["type"] = "symptom_logging"
            strategy["action"] = "log_symptom"
            strategy["confidence"] = 0.8
            
            # Check if it's complete enough for immediate logging
            if flow_analysis["information_completeness"] > 0.7:
                strategy["priority"] = "high"
                strategy["confidence"] = 0.9
            else:
                strategy["type"] = "partial_logging_with_follow_up"
        
        # Check for symptom history requests
        elif any(word in symptom_data.get("description", "").lower() 
                for word in ["history", "log", "previous", "past", "show me"]):
            strategy["type"] = "symptom_history"
            strategy["action"] = "get_symptom_history"
            strategy["confidence"] = 0.9
        
        # Check for emergency indicators
        elif self._detect_emergency_indicators(symptom_data, user_profile):
            strategy["type"] = "emergency_response"
            strategy["priority"] = "critical"
            strategy["confidence"] = 0.95
        
        # Check for general health questions
        elif self._is_general_health_question(symptom_data.get("description", "")):
            strategy["type"] = "health_information"
            strategy["confidence"] = 0.7
        
        return strategy

    def _generate_contextual_response(
        self, 
        strategy: Dict[str, Any], 
        symptom_data: Dict[str, Any], 
        flow_analysis: Dict[str, Any], 
        user_profile: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate contextual response based on strategy and data."""
        
        response_data = {
            "message": "",
            "follow_up_questions": [],
            "medical_advice": "",
            "urgency_level": "normal"
        }
        
        strategy_type = strategy.get("type")
        
        if strategy_type == "symptom_logging":
            response_data = self._generate_symptom_logging_response(symptom_data, user_profile)
        
        elif strategy_type == "partial_logging_with_follow_up":
            response_data = self._generate_partial_logging_response(symptom_data, user_profile)
        
        elif strategy_type == "symptom_history":
            response_data = self._generate_history_response(symptom_data)
        
        elif strategy_type == "emergency_response":
            response_data = self._generate_emergency_response(symptom_data, user_profile)
        
        elif strategy_type == "health_information":
            response_data = self._generate_health_information_response(symptom_data, user_profile)
        
        else:  # clarifying_question
            response_data = self._generate_clarifying_response(symptom_data, flow_analysis)
        
        return response_data

    def _generate_symptom_logging_response(
        self, 
        symptom_data: Dict[str, Any], 
        user_profile: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate response for complete symptom logging."""
        
        symptom_name = symptom_data.get("symptom_name", "symptom")
        severity = symptom_data.get("severity")
        
        # Build confirmation message
        template = self.response_templates["symptom_logged_complete"][0]
        additional_info = ""
        
        if severity:
            additional_info = f"The severity level of {severity}/10 has been noted."
        
        if symptom_data.get("duration_hours"):
            duration_text = self._format_duration(symptom_data["duration_hours"])
            additional_info += f" Duration: {duration_text}."
        
        message = template.format(
            symptom_name=symptom_name,
            severity=severity or "unspecified",
            additional_info=additional_info
        )
        
        # Add contextual medical advice
        medical_advice = self._get_contextual_medical_advice(symptom_data, user_profile)
        
        return {
            "message": message,
            "medical_advice": medical_advice,
            "urgency_level": self._assess_urgency_level(symptom_data, user_profile),
            "follow_up_questions": []
        }

    def _generate_partial_logging_response(
        self, 
        symptom_data: Dict[str, Any], 
        user_profile: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate response for partial symptom logging with follow-up."""
        
        symptom_name = symptom_data.get("symptom_name", "symptom")
        follow_up_questions = symptom_data.get("follow_up_questions", [])
        
        template = self.response_templates["symptom_logged_partial"][0]
        follow_up_question = follow_up_questions[0] if follow_up_questions else "Can you provide more details?"
        
        message = template.format(
            symptom_name=symptom_name,
            follow_up_question=follow_up_question
        )
        
        return {
            "message": message,
            "follow_up_questions": follow_up_questions[:2],  # Limit to 2 questions
            "medical_advice": "",
            "urgency_level": "normal"
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

    def _generate_emergency_response(
        self, 
        symptom_data: Dict[str, Any], 
        user_profile: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate emergency response."""
        
        return {
            "message": "⚠️ Based on your symptoms, this may require immediate medical attention. Please contact emergency services (911) or go to the nearest emergency room.",
            "follow_up_questions": [],
            "medical_advice": "Do not delay seeking emergency medical care.",
            "urgency_level": "critical"
        }

    def _generate_health_information_response(
        self, 
        symptom_data: Dict[str, Any], 
        user_profile: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate health information response."""
        
        medical_advice = self._get_contextual_medical_advice(symptom_data, user_profile)
        
        return {
            "message": "I can provide some general health information based on your question.",
            "follow_up_questions": ["Would you like me to log this as a symptom for tracking?"],
            "medical_advice": medical_advice,
            "urgency_level": "normal"
        }

    def _generate_clarifying_response(
        self, 
        symptom_data: Dict[str, Any], 
        flow_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate clarifying question response."""
        
        follow_up_questions = symptom_data.get("follow_up_questions", [])
        
        if not follow_up_questions:
            follow_up_questions = ["Can you tell me more about what you're experiencing?"]
        
        template = self.response_templates["clarifying_questions"][0]
        message = template.format(question=follow_up_questions[0])
        
        return {
            "message": message,
            "follow_up_questions": follow_up_questions,
            "medical_advice": "",
            "urgency_level": "normal"
        }

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
            return "Please consult with a healthcare professional for personalized medical advice."
        
        advice_templates = self.medical_advice_templates[advice_category]
        
        # Choose appropriate advice based on severity and context
        if severity >= 8:
            advice = advice_templates.get("severe", advice_templates["general"])
        elif self._is_chronic_symptom(symptom_data, user_profile):
            advice = advice_templates.get("chronic", advice_templates["general"])
        else:
            advice = advice_templates["general"]
        
        # Add standard disclaimer
        advice += " This information is for educational purposes only and is not a substitute for professional medical advice."
        
        return advice

    def _detect_emergency_indicators(
        self, 
        symptom_data: Dict[str, Any], 
        user_profile: Optional[Dict[str, Any]]
    ) -> bool:
        """Detect emergency indicators in symptom data."""
        
        emergency_keywords = [
            "chest pain", "difficulty breathing", "severe bleeding", "unconscious",
            "heart attack", "stroke", "severe allergic reaction", "poisoning"
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
            "information about", "learn about", "understand"
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

    def _assess_urgency_level(
        self, 
        symptom_data: Dict[str, Any], 
        user_profile: Optional[Dict[str, Any]]
    ) -> str:
        """Assess urgency level of the symptom."""
        
        severity = symptom_data.get("severity")
        
        # Ensure severity is an integer for comparisons
        if severity is None:
            severity = 0
        
        if self._detect_emergency_indicators(symptom_data, user_profile):
            return "critical"
        elif severity >= 8:
            return "high"
        elif severity >= 6:
            return "medium"
        else:
            return "normal"

    def _format_duration(self, hours: int) -> str:
        """Format duration in a human-readable way."""
        
        if hours < 1:
            return "less than an hour"
        elif hours == 1:
            return "1 hour"
        elif hours < 24:
            return f"{hours} hours"
        elif hours == 24:
            return "1 day"
        elif hours < 168:
            days = hours // 24
            return f"{days} day{'s' if days > 1 else ''}"
        else:
            weeks = hours // 168
            return f"{weeks} week{'s' if weeks > 1 else ''}"

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
        
        # Start with the conversation manager's message if available
        if message:
            enhanced_response = message
        else:
            enhanced_response = base_response
        
        # Add agent action results
        if agent_action_result:
            if agent_action_result.get("success"):
                action = agent_action_result.get("action", "")
                if "logged" in action:
                    enhanced_response = f"✅ I've logged your symptom successfully.\n\n{enhanced_response}"
                elif "history" in action:
                    data = agent_action_result.get("data", {})
                    count = data.get("count", 0)
                    enhanced_response = f"📊 I found {count} symptom entries in your history.\n\n{enhanced_response}"
        
        # Add medical advice if available
        if medical_advice:
            enhanced_response += f"\n\n💡 {medical_advice}"
        
        # Add urgency indicators
        if urgency_level == "critical":
            enhanced_response = f"🚨 URGENT: {enhanced_response}"
        elif urgency_level == "high":
            enhanced_response = f"⚠️ Important: {enhanced_response}"
        
        # Add follow-up questions
        follow_up_questions = response_data.get("follow_up_questions", [])
        if follow_up_questions:
            enhanced_response += f"\n\n❓ {follow_up_questions[0]}"
        
        return enhanced_response