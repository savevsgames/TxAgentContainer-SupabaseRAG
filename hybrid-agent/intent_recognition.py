"""
Intent Recognition System for TxAgent Agent Awareness.

This module provides intelligent intent detection for user queries,
specifically focusing on symptom logging and management intents.
"""

import re
import logging
from typing import Tuple, Optional, Dict, Any, List

logger = logging.getLogger("intent_recognition")

class IntentRecognizer:
    """Recognizes user intents for symptom logging and management."""
    
    def __init__(self):
        # Patterns for symptom logging intent
        self.symptom_logging_patterns = [
            r"log (a|my|this) symptom",
            r"record (a|my|this) symptom", 
            r"save (a|my|this) symptom",
            r"track (a|my|this) symptom",
            r"i('ve| have) been experiencing",
            r"i('m| am) having (a|an)",
            r"i('ve| have) had (a|an)",
            r"i('m| am) feeling",
            r"my (head|stomach|back|chest|throat) (hurts|aches|is sore)",
            r"i have (a|an) (headache|stomachache|backache|fever|cough|rash)",
            r"i('m| am) experiencing (pain|discomfort|nausea|dizziness)",
            r"can you log",
            r"please record",
            r"add to my symptoms",
            r"note that i",
            r"i('m| am) suffering from",
            r"i feel (sick|unwell|terrible|awful)",
            r"i('ve| have) got (a|an)",
        ]
        
        # Patterns for symptom history requests
        self.history_patterns = [
            r"show (me )?my symptom history",
            r"what symptoms have i logged",
            r"my (previous|past) symptoms",
            r"symptom (log|history|record)",
            r"when did i last have",
            r"how often do i get",
            r"my (headache|pain|fever) history",
            r"list my symptoms",
            r"view my symptom log",
            r"symptom tracking",
            r"my health log",
        ]
        
        # Common symptom names for extraction
        self.symptom_names = [
            "headache", "migraine", "fever", "cough", "sore throat", "nausea",
            "dizziness", "fatigue", "back pain", "chest pain", "stomach ache",
            "rash", "shortness of breath", "joint pain", "muscle ache",
            "insomnia", "anxiety", "depression", "heartburn", "constipation",
            "diarrhea", "vomiting", "runny nose", "congestion", "sneezing",
            "bloating", "cramps", "swelling", "bruising", "numbness",
            "tingling", "weakness", "stiffness", "burning", "itching",
            "cold", "flu", "allergy", "asthma", "vertigo", "tinnitus"
        ]
        
        # Severity indicators
        self.severity_patterns = {
            r"(very )?mild|slight|minor|barely noticeable": 2,
            r"moderate|medium|average|okay": 5,
            r"severe|intense|terrible|awful|bad": 8,
            r"worst|excruciating|agonizing|unbearable|extreme": 10,
            r"(\d+) out of (\d+)": "extract_numeric",
            r"(\d+)/(\d+)": "extract_numeric",
            r"scale of (\d+)": "extract_scale"
        }
        
        # Duration patterns
        self.duration_patterns = {
            r"(\d+) hours?": "hours",
            r"(\d+) days?": "days", 
            r"(\d+) weeks?": "weeks",
            r"all day": 24,
            r"few hours": 3,
            r"couple hours": 2,
            r"since (morning|yesterday|last night)": "relative",
            r"for the past (\d+) (hour|day|week)s?": "extract_duration",
            r"about (\d+) (hour|day)s?": "extract_duration"
        }
        
        # Body location patterns
        self.location_patterns = [
            "head", "forehead", "temple", "neck", "throat", "chest", "back",
            "stomach", "abdomen", "arm", "leg", "knee", "shoulder", "wrist",
            "ankle", "foot", "hand", "finger", "toe", "eye", "ear", "nose",
            "jaw", "hip", "elbow", "spine", "ribs", "pelvis", "groin"
        ]

    def detect_intent(self, query: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Tuple[str, float, Dict[str, Any]]:
        """
        Detect user intent from query and conversation history.
        
        Args:
            query: User's current query
            conversation_history: Previous conversation messages
            
        Returns:
            Tuple of (intent_type, confidence, extracted_data)
        """
        query_lower = query.lower()
        
        logger.info(f"🔍 INTENT: Analyzing query: {query[:100]}...")
        
        # Check for symptom logging intent
        for pattern in self.symptom_logging_patterns:
            if re.search(pattern, query_lower):
                logger.info(f"🔍 INTENT: Detected symptom logging intent with pattern: {pattern}")
                extracted_data = self._extract_symptom_data(query, conversation_history)
                confidence = 0.9 if extracted_data.get("symptom_name") else 0.7
                return "log_symptom", confidence, extracted_data
        
        # Check for symptom history intent
        for pattern in self.history_patterns:
            if re.search(pattern, query_lower):
                logger.info(f"🔍 INTENT: Detected symptom history intent with pattern: {pattern}")
                extracted_data = self._extract_history_request(query)
                return "get_symptom_history", 0.8, extracted_data
        
        # Check for implicit symptom mentions (lower confidence)
        symptom_name = self._extract_symptom_name(query_lower)
        if symptom_name and self._has_symptom_context(query_lower):
            logger.info(f"🔍 INTENT: Detected implicit symptom mention: {symptom_name}")
            extracted_data = self._extract_symptom_data(query, conversation_history)
            return "log_symptom", 0.6, extracted_data
        
        # No specific intent detected
        logger.info("🔍 INTENT: No specific intent detected - general chat")
        return "general_chat", 0.0, {}

    def _has_symptom_context(self, query_lower: str) -> bool:
        """Check if query has context suggesting symptom logging."""
        symptom_context_words = [
            "pain", "hurt", "ache", "feel", "experiencing", "having",
            "suffering", "sick", "unwell", "problem", "issue", "trouble"
        ]
        return any(word in query_lower for word in symptom_context_words)

    def _extract_symptom_data(self, query: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Extract symptom details from the query and conversation history."""
        query_lower = query.lower()
        extracted = {}
        
        logger.info(f"🔍 SYMPTOM_EXTRACT: Extracting from: {query[:100]}...")
        
        # Extract symptom name
        symptom_name = self._extract_symptom_name(query_lower)
        if symptom_name:
            extracted["symptom_name"] = symptom_name
            logger.info(f"🔍 SYMPTOM_EXTRACT: Found symptom: {symptom_name}")
        
        # Extract severity
        severity = self._extract_severity(query_lower)
        if severity:
            extracted["severity"] = severity
            logger.info(f"🔍 SYMPTOM_EXTRACT: Found severity: {severity}")
        
        # Extract duration
        duration = self._extract_duration(query_lower)
        if duration:
            extracted["duration_hours"] = duration
            logger.info(f"🔍 SYMPTOM_EXTRACT: Found duration: {duration} hours")
        
        # Extract location/body part
        location = self._extract_location(query_lower)
        if location:
            extracted["location"] = location
            logger.info(f"🔍 SYMPTOM_EXTRACT: Found location: {location}")
        
        # Store original description
        extracted["description"] = query
        
        logger.info(f"🔍 SYMPTOM_EXTRACT: Final extracted data: {extracted}")
        return extracted

    def _extract_symptom_name(self, query_lower: str) -> Optional[str]:
        """Extract symptom name from query."""
        # First check exact matches with known symptoms
        for symptom in self.symptom_names:
            if symptom in query_lower:
                logger.info(f"🔍 SYMPTOM_NAME: Found exact match: {symptom}")
                return symptom
        
        # Try to extract from common patterns
        patterns = [
            r"i have (a|an) ([a-z ]+)",
            r"experiencing ([a-z ]+)",
            r"feeling ([a-z ]+)",
            r"my ([a-z ]+) (hurts|aches|is sore)",
            r"suffering from ([a-z ]+)",
            r"i('ve| have) got (a|an) ([a-z ]+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                # Get the last group which should be the symptom
                potential_symptom = match.groups()[-1].strip()
                
                # Basic validation - should be 1-3 words and not too generic
                words = potential_symptom.split()
                if 1 <= len(words) <= 3 and potential_symptom not in ["pain", "problem", "issue", "thing"]:
                    logger.info(f"🔍 SYMPTOM_NAME: Extracted from pattern: {potential_symptom}")
                    return potential_symptom
        
        logger.info("🔍 SYMPTOM_NAME: No symptom name found")
        return None

    def _extract_severity(self, query_lower: str) -> Optional[int]:
        """Extract severity rating from query."""
        for pattern, value in self.severity_patterns.items():
            match = re.search(pattern, query_lower)
            if match:
                if value == "extract_numeric":
                    # Extract numeric rating like "7 out of 10" or "8/10"
                    numbers = [int(x) for x in match.groups() if x.isdigit()]
                    if len(numbers) == 2:
                        severity = min(10, max(1, int((numbers[0] / numbers[1]) * 10)))
                        logger.info(f"🔍 SEVERITY: Extracted numeric: {severity}")
                        return severity
                elif value == "extract_scale":
                    # Extract from "scale of X" pattern
                    scale_value = int(match.group(1))
                    severity = min(10, max(1, scale_value))
                    logger.info(f"🔍 SEVERITY: Extracted scale: {severity}")
                    return severity
                elif isinstance(value, int):
                    logger.info(f"🔍 SEVERITY: Matched pattern: {value}")
                    return value
        
        logger.info("🔍 SEVERITY: No severity found")
        return None

    def _extract_duration(self, query_lower: str) -> Optional[int]:
        """Extract duration in hours from query."""
        for pattern, unit in self.duration_patterns.items():
            match = re.search(pattern, query_lower)
            if match:
                if unit == "hours":
                    duration = int(match.group(1))
                    logger.info(f"🔍 DURATION: Found {duration} hours")
                    return duration
                elif unit == "days":
                    duration = int(match.group(1)) * 24
                    logger.info(f"🔍 DURATION: Found {duration} hours (from days)")
                    return duration
                elif unit == "weeks":
                    duration = int(match.group(1)) * 24 * 7
                    logger.info(f"🔍 DURATION: Found {duration} hours (from weeks)")
                    return duration
                elif unit == "extract_duration":
                    number = int(match.group(1))
                    time_unit = match.group(2)
                    if time_unit.startswith("hour"):
                        duration = number
                    elif time_unit.startswith("day"):
                        duration = number * 24
                    else:
                        duration = number
                    logger.info(f"🔍 DURATION: Extracted {duration} hours")
                    return duration
                elif isinstance(unit, int):
                    logger.info(f"🔍 DURATION: Fixed duration: {unit} hours")
                    return unit
        
        logger.info("🔍 DURATION: No duration found")
        return None

    def _extract_location(self, query_lower: str) -> Optional[str]:
        """Extract body location from query."""
        for location in self.location_patterns:
            if location in query_lower:
                logger.info(f"🔍 LOCATION: Found location: {location}")
                return location
        
        logger.info("🔍 LOCATION: No location found")
        return None

    def _extract_history_request(self, query: str) -> Dict[str, Any]:
        """Extract details from symptom history request."""
        query_lower = query.lower()
        extracted = {}
        
        logger.info(f"🔍 HISTORY_REQUEST: Analyzing: {query[:100]}...")
        
        # Check if asking for specific symptom history
        symptom_name = self._extract_symptom_name(query_lower)
        if symptom_name:
            extracted["symptom_name"] = symptom_name
            logger.info(f"🔍 HISTORY_REQUEST: Specific symptom: {symptom_name}")
        
        # Check for time range
        if "last week" in query_lower:
            extracted["days_back"] = 7
            logger.info("🔍 HISTORY_REQUEST: Time range: last week")
        elif "last month" in query_lower:
            extracted["days_back"] = 30
            logger.info("🔍 HISTORY_REQUEST: Time range: last month")
        elif "recent" in query_lower:
            extracted["days_back"] = 14
            logger.info("🔍 HISTORY_REQUEST: Time range: recent (14 days)")
        
        logger.info(f"🔍 HISTORY_REQUEST: Final extracted: {extracted}")
        return extracted