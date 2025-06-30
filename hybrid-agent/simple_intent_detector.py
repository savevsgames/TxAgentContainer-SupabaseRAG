"""
Simple Intent Detector for TxAgent Agent Overhaul.

This module provides reliable, straightforward intent detection using
comprehensive keyword matching instead of complex NLP processing.
Designed to catch basic health tracking intents with high accuracy.
"""

import logging
from typing import Dict, Any, Optional, List
import re

logger = logging.getLogger("simple_intent_detector")

class SimpleIntentDetector:
    """Reliable intent detection using comprehensive keyword matching."""
    
    def __init__(self):
        # Comprehensive symptom keywords - covers common health complaints
        self.symptom_keywords = [
            # Pain-related
            "headache", "migraine", "pain", "ache", "hurt", "hurting", "sore", "tender",
            "toothache", "earache", "backache", "stomach ache", "stomachache",
            "back pain", "chest pain", "joint pain", "muscle pain", "neck pain",
            
            # Specific symptoms
            "fever", "nausea", "dizziness", "fatigue", "tired", "exhausted",
            "sore throat", "runny nose", "stuffy nose", "congestion", "cough",
            "sneezing", "itchy", "rash", "swelling", "bloating", "cramps",
            "heartburn", "constipation", "diarrhea", "vomiting", "nosebleed",
            
            # Body parts with issues
            "sore knee", "sore back", "sore neck", "sore shoulder", "sore wrist",
            "sore ankle", "sore foot", "sore hand", "sore arm", "sore leg",
            
            # General health states
            "sick", "unwell", "ill", "feeling bad", "not feeling well",
            "under the weather", "coming down with", "symptoms"
        ]
        
        # Treatment/medication keywords
        self.treatment_keywords = [
            # Medications
            "medication", "medicine", "pill", "tablet", "capsule", "drug",
            "prescription", "prescribed", "taking", "started taking",
            
            # Common medications
            "ibuprofen", "advil", "motrin", "tylenol", "acetaminophen", "aspirin",
            "aleve", "naproxen", "benadryl", "claritin", "zyrtec",
            "lisinopril", "metformin", "atorvastatin", "omeprazole", "prilosec",
            
            # Treatment types
            "treatment", "therapy", "physical therapy", "exercise", "diet",
            "supplement", "vitamin", "antibiotic", "inhaler", "cream", "ointment"
        ]
        
        # Appointment keywords
        self.appointment_keywords = [
            "appointment", "visit", "checkup", "check-up", "doctor", "dr.",
            "physician", "nurse", "dentist", "specialist", "clinic", "hospital",
            "scheduled", "schedule", "book", "booking", "see", "seeing",
            "meeting", "consultation", "exam", "examination", "surgery",
            "procedure", "follow-up", "followup"
        ]
        
        # Greeting keywords
        self.greeting_keywords = [
            "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
            "how are you", "what's up", "greetings", "howdy"
        ]
        
        # History request keywords
        self.history_keywords = [
            "history", "show me", "list", "previous", "past", "logged",
            "recorded", "my symptoms", "my medications", "my appointments",
            "what have i", "track record"
        ]

    def detect_intent(self, query: str) -> Dict[str, Any]:
        """
        Detect user intent using reliable keyword matching.
        
        Args:
            query: User's input text
            
        Returns:
            Dictionary with intent type, confidence, and extracted data
        """
        query_lower = query.lower().strip()
        
        logger.info(f"🔍 INTENT_DETECTOR: Analyzing query: '{query}'")
        
        # Check for greetings first (but only if it's a short query)
        if len(query_lower.split()) <= 3 and self._matches_keywords(query_lower, self.greeting_keywords):
            logger.info("🔍 INTENT_DETECTOR: Detected greeting")
            return {
                "intent": "greeting",
                "confidence": 0.95,
                "extracted_data": {}
            }
        
        # Check for history requests
        if self._matches_keywords(query_lower, self.history_keywords):
            logger.info("🔍 INTENT_DETECTOR: Detected history request")
            return {
                "intent": "history",
                "confidence": 0.9,
                "extracted_data": self._extract_history_type(query_lower)
            }
        
        # Check for symptoms (highest priority for health tracking)
        if self._matches_keywords(query_lower, self.symptom_keywords):
            logger.info("🔍 INTENT_DETECTOR: Detected symptom tracking intent")
            extracted_data = self._extract_symptom_data(query)
            return {
                "intent": "symptom",
                "confidence": 0.9,
                "extracted_data": extracted_data
            }
        
        # Check for treatments/medications
        if self._matches_keywords(query_lower, self.treatment_keywords):
            logger.info("🔍 INTENT_DETECTOR: Detected treatment tracking intent")
            extracted_data = self._extract_treatment_data(query)
            return {
                "intent": "treatment",
                "confidence": 0.9,
                "extracted_data": extracted_data
            }
        
        # Check for appointments
        if self._matches_keywords(query_lower, self.appointment_keywords):
            logger.info("🔍 INTENT_DETECTOR: Detected appointment tracking intent")
            extracted_data = self._extract_appointment_data(query)
            return {
                "intent": "appointment",
                "confidence": 0.9,
                "extracted_data": extracted_data
            }
        
        # Default to general conversation
        logger.info("🔍 INTENT_DETECTOR: No specific intent detected - general conversation")
        return {
            "intent": "general",
            "confidence": 0.5,
            "extracted_data": {}
        }

    def _matches_keywords(self, query_lower: str, keywords: List[str]) -> bool:
        """Check if query matches any of the provided keywords."""
        return any(keyword in query_lower for keyword in keywords)

    def _extract_symptom_data(self, query: str) -> Dict[str, Any]:
        """Extract symptom-specific data from the query."""
        data = {}
        query_lower = query.lower()
        
        # Extract symptom name
        for keyword in self.symptom_keywords:
            if keyword in query_lower:
                data["symptom_name"] = keyword
                break
        
        # Extract severity (numeric scale)
        severity_patterns = [
            r"(\d+)\s*(?:out of|/)\s*(\d+)",  # "7 out of 10" or "8/10"
            r"(\d+)\s*(?:scale|severity)",     # "7 scale" or "8 severity"
            r"severity\s*(?:of\s*)?(\d+)",     # "severity 7" or "severity of 8"
        ]
        
        for pattern in severity_patterns:
            match = re.search(pattern, query_lower)
            if match:
                if len(match.groups()) == 2:
                    # Scale format like "7/10"
                    value = int(match.group(1))
                    max_value = int(match.group(2))
                    data["severity"] = min(10, max(1, int((value / max_value) * 10)))
                else:
                    # Single number
                    data["severity"] = min(10, max(1, int(match.group(1))))
                break
        
        # Extract duration
        duration_patterns = [
            r"(\d+)\s*hour",
            r"(\d+)\s*day",
            r"(\d+)\s*week",
            r"since\s+(morning|yesterday|last\s+night)",
            r"for\s+(\d+)\s*(hour|day|week)",
            r"all\s+day",
            r"few\s+hours"
        ]
        
        for pattern in duration_patterns:
            match = re.search(pattern, query_lower)
            if match:
                data["duration_text"] = match.group(0)
                break
        
        # Extract location/body part
        body_parts = [
            "head", "forehead", "temple", "neck", "throat", "chest", "back",
            "stomach", "abdomen", "arm", "leg", "knee", "shoulder", "wrist",
            "ankle", "foot", "hand", "eye", "ear", "nose", "tooth", "teeth",
            "jaw", "mouth", "finger", "toe"
        ]
        
        for part in body_parts:
            if part in query_lower:
                data["location"] = part
                break
        
        logger.info(f"🔍 SYMPTOM_EXTRACT: Extracted data: {data}")
        return data

    def _extract_treatment_data(self, query: str) -> Dict[str, Any]:
        """Extract treatment-specific data from the query."""
        data = {}
        query_lower = query.lower()
        
        # Extract treatment name
        for keyword in self.treatment_keywords:
            if keyword in query_lower:
                data["treatment_name"] = keyword
                break
        
        # Extract dosage patterns
        dosage_patterns = [
            r"(\d+)\s*mg",
            r"(\d+)\s*(?:tablet|pill|capsule)s?",
            r"(\d+)\s*times?\s+(?:a\s+)?day",
            r"once\s+(?:a\s+)?day",
            r"twice\s+(?:a\s+)?day"
        ]
        
        for pattern in dosage_patterns:
            match = re.search(pattern, query_lower)
            if match:
                data["dosage"] = match.group(0)
                break
        
        # Extract duration
        if "for" in query_lower:
            duration_match = re.search(r"for\s+(\d+)\s*(day|week|month)s?", query_lower)
            if duration_match:
                data["duration"] = duration_match.group(0)
        
        logger.info(f"🔍 TREATMENT_EXTRACT: Extracted data: {data}")
        return data

    def _extract_appointment_data(self, query: str) -> Dict[str, Any]:
        """Extract appointment-specific data from the query."""
        data = {}
        query_lower = query.lower()
        
        # Extract doctor name
        doctor_patterns = [
            r"dr\.?\s+([a-z]+)",
            r"doctor\s+([a-z]+)",
            r"with\s+([a-z]+)"
        ]
        
        for pattern in doctor_patterns:
            match = re.search(pattern, query_lower)
            if match:
                name = match.group(1).title()
                data["doctor_name"] = f"Dr. {name}"
                break
        
        # Extract time references
        time_references = [
            "tomorrow", "today", "next week", "monday", "tuesday", "wednesday",
            "thursday", "friday", "saturday", "sunday"
        ]
        
        for time_ref in time_references:
            if time_ref in query_lower:
                data["appointment_time"] = time_ref
                break
        
        # Extract appointment type
        appointment_types = [
            "checkup", "follow-up", "consultation", "exam", "physical",
            "surgery", "procedure", "screening"
        ]
        
        for apt_type in appointment_types:
            if apt_type in query_lower:
                data["appointment_type"] = apt_type
                break
        
        logger.info(f"🔍 APPOINTMENT_EXTRACT: Extracted data: {data}")
        return data

    def _extract_history_type(self, query_lower: str) -> Dict[str, Any]:
        """Extract what type of history the user is requesting."""
        data = {}
        
        if "symptom" in query_lower:
            data["history_type"] = "symptoms"
        elif "medication" in query_lower or "treatment" in query_lower:
            data["history_type"] = "treatments"
        elif "appointment" in query_lower or "visit" in query_lower:
            data["history_type"] = "appointments"
        else:
            data["history_type"] = "all"
        
        return data

# Global instance
simple_intent_detector = SimpleIntentDetector()