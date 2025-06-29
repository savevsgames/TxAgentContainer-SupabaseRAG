"""
Advanced NLP Processing for TxAgent Agent Awareness Phase 2.

This module provides sophisticated natural language processing capabilities
for better symptom extraction, context understanding, and conversation flow.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json

logger = logging.getLogger("nlp_processor")

class AdvancedNLPProcessor:
    """Advanced NLP processor for enhanced symptom understanding and conversation flow."""
    
    def __init__(self):
        # Enhanced symptom patterns with context
        self.symptom_contexts = {
            "pain": {
                "types": ["sharp", "dull", "throbbing", "burning", "stabbing", "aching", "cramping"],
                "intensifiers": ["severe", "mild", "intense", "excruciating", "slight", "terrible"],
                "locations": ["head", "back", "chest", "stomach", "neck", "shoulder", "knee", "joint"]
            },
            "digestive": {
                "symptoms": ["nausea", "vomiting", "diarrhea", "constipation", "bloating", "heartburn"],
                "triggers": ["eating", "food", "meal", "spicy", "dairy", "gluten"],
                "timing": ["after eating", "before meals", "morning", "evening"]
            },
            "respiratory": {
                "symptoms": ["cough", "shortness of breath", "wheezing", "congestion"],
                "qualities": ["dry", "wet", "productive", "persistent", "occasional"],
                "triggers": ["exercise", "cold air", "allergens", "dust"]
            },
            "neurological": {
                "symptoms": ["headache", "migraine", "dizziness", "vertigo", "numbness", "tingling"],
                "patterns": ["cluster", "tension", "sinus", "chronic", "episodic"],
                "triggers": ["stress", "light", "sound", "weather", "hormones"]
            }
        }
        
        # Temporal expressions for better duration/timing extraction
        self.temporal_patterns = {
            "duration": {
                r"for (\d+) (minute|hour|day|week|month)s?": "extract_duration",
                r"(\d+) (minute|hour|day|week|month)s? ago": "extract_onset",
                r"since (yesterday|this morning|last night|last week)": "relative_onset",
                r"all (day|night|week)": "duration_all",
                r"on and off": "intermittent",
                r"constantly|continuously|non-stop": "continuous"
            },
            "frequency": {
                r"every (day|few days|week|month)": "frequency",
                r"(\d+) times? (a|per) (day|week|month)": "frequency_numeric",
                r"rarely|occasionally|sometimes|often|frequently|always": "frequency_qualitative"
            }
        }
        
        # Severity indicators with context
        self.severity_contexts = {
            "numeric": {
                r"(\d+) out of (\d+)": "scale",
                r"(\d+)/(\d+)": "scale",
                r"scale of (\d+)": "single_scale"
            },
            "qualitative": {
                "unbearable|excruciating|worst ever|10": 10,
                "severe|terrible|awful|intense|9": 9,
                "very bad|really bad|8": 8,
                "bad|significant|7": 7,
                "moderate|medium|noticeable|6": 6,
                "mild to moderate|5": 5,
                "mild|slight|minor|4": 4,
                "very mild|barely noticeable|3": 3,
                "minimal|tiny|2": 2,
                "hardly there|1": 1
            },
            "comparative": {
                r"worse than (yesterday|last time|usual)": "worsening",
                r"better than (yesterday|last time|before)": "improving",
                r"same as (yesterday|last time|usual)": "stable"
            }
        }
        
        # Follow-up question templates
        self.follow_up_questions = {
            "missing_severity": [
                "How would you rate the severity on a scale of 1-10?",
                "Is this mild, moderate, or severe?",
                "How intense is the {symptom}?"
            ],
            "missing_duration": [
                "How long have you been experiencing this?",
                "When did the {symptom} start?",
                "How long has this been going on?"
            ],
            "missing_location": [
                "Where exactly do you feel the {symptom}?",
                "Can you point to where it hurts?",
                "Which part of your {body_area} is affected?"
            ],
            "missing_triggers": [
                "Do you notice anything that triggers the {symptom}?",
                "What seems to make it worse?",
                "Have you noticed any patterns?"
            ],
            "missing_quality": [
                "How would you describe the {symptom}?",
                "What does the {symptom} feel like?",
                "Can you describe the sensation?"
            ]
        }

    def extract_comprehensive_symptom_data(self, query: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Extract comprehensive symptom data using advanced NLP techniques.
        
        Args:
            query: User's current query
            conversation_history: Previous conversation messages
            
        Returns:
            Comprehensive symptom data with confidence scores
        """
        logger.info(f"🔍 NLP: Starting comprehensive extraction for: {query[:100]}...")
        
        extracted = {
            "symptom_name": None,
            "severity": None,
            "duration_hours": None,
            "location": None,
            "quality": None,
            "triggers": [],
            "frequency": None,
            "onset": None,
            "description": query,
            "confidence_scores": {},
            "missing_details": [],
            "follow_up_questions": []
        }
        
        query_lower = query.lower()
        
        # Extract symptom name with context
        symptom_data = self._extract_symptom_with_context(query_lower)
        if symptom_data:
            extracted.update(symptom_data)
        
        # Extract temporal information
        temporal_data = self._extract_temporal_information(query_lower)
        if temporal_data:
            extracted.update(temporal_data)
        
        # Extract severity with context
        severity_data = self._extract_severity_with_context(query_lower)
        if severity_data:
            extracted.update(severity_data)
        
        # Extract quality descriptors
        quality_data = self._extract_quality_descriptors(query_lower)
        if quality_data:
            extracted.update(quality_data)
        
        # Extract triggers and patterns
        trigger_data = self._extract_triggers_and_patterns(query_lower)
        if trigger_data:
            extracted.update(trigger_data)
        
        # Analyze conversation history for context
        if conversation_history:
            history_context = self._analyze_conversation_history(conversation_history)
            extracted = self._merge_with_history_context(extracted, history_context)
        
        # Identify missing details and generate follow-up questions
        extracted["missing_details"] = self._identify_missing_details(extracted)
        extracted["follow_up_questions"] = self._generate_follow_up_questions(extracted)
        
        logger.info(f"🔍 NLP: Comprehensive extraction complete: {len(extracted)} fields")
        return extracted

    def _extract_symptom_with_context(self, query_lower: str) -> Optional[Dict[str, Any]]:
        """Extract symptom name with contextual information."""
        result = {}
        
        # Check for specific symptom categories
        for category, data in self.symptom_contexts.items():
            if category == "pain":
                # Look for pain with descriptors
                pain_pattern = r"(sharp|dull|throbbing|burning|stabbing|aching|cramping)?\s*(pain|ache|aching|hurt|hurting)"
                match = re.search(pain_pattern, query_lower)
                if match:
                    pain_type = match.group(1) if match.group(1) else "pain"
                    result["symptom_name"] = f"{pain_type} pain" if pain_type != "pain" else "pain"
                    result["quality"] = pain_type if pain_type != "pain" else None
                    result["confidence_scores"] = {"symptom_name": 0.9}
                    return result
            
            elif "symptoms" in data:
                for symptom in data["symptoms"]:
                    if symptom in query_lower:
                        result["symptom_name"] = symptom
                        result["confidence_scores"] = {"symptom_name": 0.95}
                        
                        # Look for quality descriptors
                        if "qualities" in data:
                            for quality in data["qualities"]:
                                if quality in query_lower:
                                    result["quality"] = quality
                                    break
                        
                        return result
        
        # Fallback to basic extraction
        basic_symptoms = [
            "headache", "migraine", "fever", "cough", "nausea", "dizziness",
            "fatigue", "rash", "swelling", "bruising", "numbness", "tingling"
        ]
        
        for symptom in basic_symptoms:
            if symptom in query_lower:
                result["symptom_name"] = symptom
                result["confidence_scores"] = {"symptom_name": 0.8}
                return result
        
        return None

    def _extract_temporal_information(self, query_lower: str) -> Dict[str, Any]:
        """Extract temporal information (duration, onset, frequency)."""
        result = {}
        
        # Extract duration
        for pattern, extraction_type in self.temporal_patterns["duration"].items():
            match = re.search(pattern, query_lower)
            if match:
                if extraction_type == "extract_duration":
                    number = int(match.group(1))
                    unit = match.group(2)
                    hours = self._convert_to_hours(number, unit)
                    result["duration_hours"] = hours
                    result["confidence_scores"] = result.get("confidence_scores", {})
                    result["confidence_scores"]["duration"] = 0.9
                elif extraction_type == "extract_onset":
                    number = int(match.group(1))
                    unit = match.group(2)
                    result["onset"] = f"{number} {unit}s ago"
                    result["confidence_scores"] = result.get("confidence_scores", {})
                    result["confidence_scores"]["onset"] = 0.9
                elif extraction_type == "relative_onset":
                    time_ref = match.group(1)
                    result["onset"] = time_ref
                    result["confidence_scores"] = result.get("confidence_scores", {})
                    result["confidence_scores"]["onset"] = 0.8
                elif extraction_type == "duration_all":
                    period = match.group(1)
                    if period == "day":
                        result["duration_hours"] = 24
                    elif period == "night":
                        result["duration_hours"] = 8
                    elif period == "week":
                        result["duration_hours"] = 168
                elif extraction_type in ["intermittent", "continuous"]:
                    result["frequency"] = extraction_type
        
        # Extract frequency
        for pattern, extraction_type in self.temporal_patterns["frequency"].items():
            match = re.search(pattern, query_lower)
            if match:
                if extraction_type == "frequency":
                    period = match.group(1)
                    result["frequency"] = f"every {period}"
                elif extraction_type == "frequency_numeric":
                    times = match.group(1)
                    period = match.group(3)
                    result["frequency"] = f"{times} times per {period}"
                elif extraction_type == "frequency_qualitative":
                    result["frequency"] = match.group(0)
        
        return result

    def _extract_severity_with_context(self, query_lower: str) -> Dict[str, Any]:
        """Extract severity with contextual understanding."""
        result = {}
        
        # Check numeric scales
        for pattern, scale_type in self.severity_contexts["numeric"].items():
            match = re.search(pattern, query_lower)
            if match:
                if scale_type == "scale":
                    value = int(match.group(1))
                    max_value = int(match.group(2))
                    severity = min(10, max(1, int((value / max_value) * 10)))
                    result["severity"] = severity
                    result["confidence_scores"] = result.get("confidence_scores", {})
                    result["confidence_scores"]["severity"] = 0.95
                elif scale_type == "single_scale":
                    severity = min(10, max(1, int(match.group(1))))
                    result["severity"] = severity
                    result["confidence_scores"] = result.get("confidence_scores", {})
                    result["confidence_scores"]["severity"] = 0.9
                return result
        
        # Check qualitative descriptors
        for pattern, severity in self.severity_contexts["qualitative"].items():
            if re.search(pattern, query_lower):
                result["severity"] = severity
                result["confidence_scores"] = result.get("confidence_scores", {})
                result["confidence_scores"]["severity"] = 0.8
                return result
        
        # Check comparative descriptors
        for pattern, comparison in self.severity_contexts["comparative"].items():
            match = re.search(pattern, query_lower)
            if match:
                result["severity_trend"] = comparison
                result["confidence_scores"] = result.get("confidence_scores", {})
                result["confidence_scores"]["severity_trend"] = 0.7
        
        return result

    def _extract_quality_descriptors(self, query_lower: str) -> Dict[str, Any]:
        """Extract quality descriptors for symptoms."""
        result = {}
        
        quality_patterns = {
            "pain_qualities": ["sharp", "dull", "throbbing", "burning", "stabbing", "aching", "cramping", "shooting"],
            "texture_qualities": ["rough", "smooth", "bumpy", "raised", "flat"],
            "temperature_qualities": ["hot", "cold", "warm", "cool", "burning", "freezing"],
            "movement_qualities": ["pulsing", "throbbing", "twitching", "spasming"],
            "intensity_qualities": ["constant", "intermittent", "waves", "comes and goes"]
        }
        
        found_qualities = []
        for category, qualities in quality_patterns.items():
            for quality in qualities:
                if quality in query_lower:
                    found_qualities.append(quality)
        
        if found_qualities:
            result["quality"] = ", ".join(found_qualities)
            result["confidence_scores"] = result.get("confidence_scores", {})
            result["confidence_scores"]["quality"] = 0.8
        
        return result

    def _extract_triggers_and_patterns(self, query_lower: str) -> Dict[str, Any]:
        """Extract triggers and patterns."""
        result = {}
        
        trigger_patterns = {
            "activities": ["walking", "sitting", "standing", "lying down", "exercise", "movement"],
            "environmental": ["cold", "heat", "humidity", "weather", "air conditioning"],
            "dietary": ["eating", "drinking", "food", "spicy", "dairy", "caffeine", "alcohol"],
            "emotional": ["stress", "anxiety", "worry", "excitement", "anger"],
            "temporal": ["morning", "evening", "night", "after meals", "before bed"],
            "physical": ["touching", "pressure", "light", "sound", "noise"]
        }
        
        found_triggers = []
        for category, triggers in trigger_patterns.items():
            for trigger in triggers:
                if trigger in query_lower:
                    found_triggers.append(trigger)
        
        if found_triggers:
            result["triggers"] = found_triggers
            result["confidence_scores"] = result.get("confidence_scores", {})
            result["confidence_scores"]["triggers"] = 0.7
        
        return result

    def _analyze_conversation_history(self, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Analyze conversation history for additional context."""
        context = {
            "mentioned_symptoms": [],
            "mentioned_medications": [],
            "mentioned_conditions": [],
            "conversation_theme": None
        }
        
        # Combine all user messages
        user_messages = [msg["content"] for msg in conversation_history if msg.get("role") == "user"]
        combined_text = " ".join(user_messages).lower()
        
        # Look for previously mentioned symptoms
        common_symptoms = ["headache", "pain", "nausea", "fever", "cough", "dizziness"]
        for symptom in common_symptoms:
            if symptom in combined_text:
                context["mentioned_symptoms"].append(symptom)
        
        # Look for medications
        medication_keywords = ["taking", "medication", "medicine", "pill", "prescription"]
        if any(keyword in combined_text for keyword in medication_keywords):
            context["conversation_theme"] = "medication_related"
        
        return context

    def _merge_with_history_context(self, extracted: Dict[str, Any], history_context: Dict[str, Any]) -> Dict[str, Any]:
        """Merge extracted data with conversation history context."""
        # If no symptom name found but history mentions symptoms
        if not extracted.get("symptom_name") and history_context.get("mentioned_symptoms"):
            # Use the most recently mentioned symptom
            extracted["symptom_name"] = history_context["mentioned_symptoms"][-1]
            extracted["confidence_scores"] = extracted.get("confidence_scores", {})
            extracted["confidence_scores"]["symptom_name"] = 0.6  # Lower confidence from history
        
        # Add conversation theme
        if history_context.get("conversation_theme"):
            extracted["conversation_context"] = history_context["conversation_theme"]
        
        return extracted

    def _identify_missing_details(self, extracted: Dict[str, Any]) -> List[str]:
        """Identify what details are missing for complete symptom logging."""
        missing = []
        
        if not extracted.get("symptom_name"):
            missing.append("symptom_name")
        if not extracted.get("severity"):
            missing.append("severity")
        if not extracted.get("duration_hours") and not extracted.get("onset"):
            missing.append("duration")
        if not extracted.get("location") and extracted.get("symptom_name") in ["pain", "ache", "hurt"]:
            missing.append("location")
        
        return missing

    def _generate_follow_up_questions(self, extracted: Dict[str, Any]) -> List[str]:
        """Generate appropriate follow-up questions for missing details."""
        questions = []
        missing = extracted.get("missing_details", [])
        symptom_name = extracted.get("symptom_name", "symptom")
        
        for missing_detail in missing[:2]:  # Limit to 2 questions to avoid overwhelming
            if missing_detail in self.follow_up_questions:
                question_templates = self.follow_up_questions[missing_detail]
                question = question_templates[0].format(symptom=symptom_name, body_area="body")
                questions.append(question)
        
        return questions

    def _convert_to_hours(self, number: int, unit: str) -> int:
        """Convert time units to hours."""
        if unit.startswith("minute"):
            return max(1, number // 60)  # Minimum 1 hour
        elif unit.startswith("hour"):
            return number
        elif unit.startswith("day"):
            return number * 24
        elif unit.startswith("week"):
            return number * 24 * 7
        elif unit.startswith("month"):
            return number * 24 * 30
        return number

    def analyze_conversation_flow(self, query: str, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Analyze conversation flow and determine appropriate response strategy."""
        flow_analysis = {
            "conversation_stage": "initial",
            "user_intent_clarity": "unclear",  # Explicitly initialize
            "information_completeness": 0.0,
            "suggested_response_type": "clarifying_question",
            "conversation_context": {},
            "query": query  # Add original query for easier access
        }
        
        # Determine conversation stage
        if not conversation_history or len(conversation_history) < 2:
            flow_analysis["conversation_stage"] = "initial"
        elif len(conversation_history) < 6:
            flow_analysis["conversation_stage"] = "information_gathering"
        else:
            flow_analysis["conversation_stage"] = "detailed_discussion"
        
        # Analyze user intent clarity
        query_lower = query.lower()
        intent_indicators = ["log", "record", "track", "save", "experiencing", "having", "feeling"]
        if any(indicator in query_lower for indicator in intent_indicators):
            flow_analysis["user_intent_clarity"] = "clear"
        elif any(symptom in query_lower for symptom in ["pain", "hurt", "ache", "sick", "unwell"]):
            flow_analysis["user_intent_clarity"] = "implicit"
        # else: remains "unclear" as initialized
        
        # Calculate information completeness
        extracted = self.extract_comprehensive_symptom_data(query, conversation_history)
        total_fields = 6  # symptom_name, severity, duration, location, quality, triggers
        filled_fields = sum(1 for field in ["symptom_name", "severity", "duration_hours", "location", "quality", "triggers"] 
                          if extracted.get(field))
        flow_analysis["information_completeness"] = filled_fields / total_fields
        
        # Determine response type
        if flow_analysis["information_completeness"] > 0.7:
            flow_analysis["suggested_response_type"] = "confirmation_and_logging"
        elif flow_analysis["information_completeness"] > 0.3:
            flow_analysis["suggested_response_type"] = "targeted_follow_up"
        else:
            flow_analysis["suggested_response_type"] = "clarifying_question"
        
        return flow_analysis