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
            # Pain-related (single words)
            "headache", "migraine", "pain", "ache", "hurt", "hurting", "sore", "tender",
            "toothache", "earache", "backache", "stomach ache", "stomachache",
            "back pain", "chest pain", "joint pain", "muscle pain", "neck pain",
            
            # Pain-related (two-word variations)
            "ear ache", "tooth ache", "stomach ache", "head ache",
            
            # Natural phrases people use
            "i have a headache", "i have a sore", "i've got a", "i'm having",
            "my head hurts", "my back hurts", "my stomach hurts", "my throat hurts",
            "my ear hurts", "my tooth hurts", "my neck hurts", "my chest hurts",
            "my knee hurts", "my shoulder hurts", "my arm hurts", "my leg hurts",
            
            # Possessive forms
            "my headache", "my migraine", "my back pain", "my chest pain",
            "my sore throat", "my ear ache", "my tooth ache", "my stomach ache",
            "my sore knee", "my sore back", "my sore neck", "my sore shoulder",
            
            # Specific symptoms
            "fever", "nausea", "dizziness", "fatigue", "tired", "exhausted",
            "sore throat", "runny nose", "stuffy nose", "congestion", "cough",
            "sneezing", "itchy", "rash", "swelling", "bloating", "cramps",
            "heartburn", "constipation", "diarrhea", "vomiting", "nosebleed",
            
            # Body parts with issues (single words)
            "sore knee", "sore back", "sore neck", "sore shoulder", "sore wrist",
            "sore ankle", "sore foot", "sore hand", "sore arm", "sore leg",
            
            # Body parts with issues (possessive)
            "my sore knee", "my sore back", "my sore neck", "my sore shoulder",
            "my sore wrist", "my sore ankle", "my sore foot", "my sore hand",
            "my sore arm", "my sore leg", "my sore throat",
            
            # General health states
            "sick", "unwell", "ill", "feeling bad", "not feeling well",
            "under the weather", "coming down with", "symptoms",
            "i feel sick", "i'm sick", "i don't feel well", "feeling unwell",
            
            # Common symptom descriptions
            "it hurts", "hurts when", "painful", "throbbing", "burning",
            "sharp pain", "dull pain", "stabbing pain", "shooting pain",
            
            # Symptom onset phrases
            "started hurting", "began hurting", "hurts since", "pain started",
            "feeling pain", "experiencing pain", "having pain"
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
            "supplement", "vitamin", "antibiotic", "inhaler", "cream", "ointment",
            
            # Natural phrases for treatments
            "i'm taking", "i take", "i started", "prescribed me", "doctor gave me",
            "on medication", "taking medicine", "using", "applying"
        ]
        
        # Appointment keywords
        self.appointment_keywords = [
            "appointment", "visit", "checkup", "check-up", "doctor", "dr.",
            "physician", "nurse", "dentist", "specialist", "clinic", "hospital",
            "scheduled", "schedule", "book", "booking", "see", "seeing",
            "meeting", "consultation", "exam", "examination", "surgery",
            "procedure", "follow-up", "followup",
            
            # Natural phrases for appointments
            "i have an appointment", "seeing the doctor", "going to see",
            "doctor visit", "medical appointment", "scheduled to see"
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
            "what have i", "track record", "show my", "list my"
        ]

    def detect_intent(self, query: str) -> Dict[str, Any]:
        """
        Detect user intent using reliable keyword matching with regex word boundaries.
        
        Args:
            query: User's input text
            
        Returns:
            Dictionary with intent type, confidence, and extracted data
        """
        query_lower = query.lower().strip()
        
        logger.info(f"🔍 INTENT_DETECTOR: Analyzing query: '{query}'")
        
        # Check for greetings first (but only if it's a short query)
        if len(query_lower.split()) <= 3 and self._matches_keywords_regex(query_lower, self.greeting_keywords):
            logger.info("🔍 INTENT_DETECTOR: Detected greeting")
            return {
                "intent": "greeting",
                "confidence": 0.95,
                "extracted_data": {}
            }
        
        # Check for history requests
        if self._matches_keywords_regex(query_lower, self.history_keywords):
            logger.info("🔍 INTENT_DETECTOR: Detected history request")
            return {
                "intent": "history",
                "confidence": 0.9,
                "extracted_data": self._extract_history_type(query_lower)
            }
        
        # Check for symptoms (highest priority for health tracking)
        if self._matches_keywords_regex(query_lower, self.symptom_keywords):
            logger.info("🔍 INTENT_DETECTOR: Detected symptom tracking intent")
            extracted_data = self._extract_symptom_data(query)
            return {
                "intent": "symptom",
                "confidence": 0.9,
                "extracted_data": extracted_data
            }
        
        # Check for treatments/medications
        if self._matches_keywords_regex(query_lower, self.treatment_keywords):
            logger.info("🔍 INTENT_DETECTOR: Detected treatment tracking intent")
            extracted_data = self._extract_treatment_data(query)
            return {
                "intent": "treatment",
                "confidence": 0.9,
                "extracted_data": extracted_data
            }
        
        # Check for appointments
        if self._matches_keywords_regex(query_lower, self.appointment_keywords):
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

    def _matches_keywords_regex(self, query_lower: str, keywords: List[str]) -> bool:
        """Check if query matches any of the provided keywords using regex word boundaries."""
        for keyword in keywords:
            # Use word boundaries for exact matches, but handle multi-word phrases
            if ' ' in keyword:
                # For multi-word phrases, use the phrase as-is
                pattern = re.escape(keyword)
            else:
                # For single words, use word boundaries
                pattern = r'\b' + re.escape(keyword) + r'\b'
            
            if re.search(pattern, query_lower):
                logger.info(f"🔍 KEYWORD_MATCH: Found '{keyword}' in query")
                return True
        return False

    def _matches_keywords(self, query_lower: str, keywords: List[str]) -> bool:
        """Legacy method - kept for backward compatibility."""
        return self._matches_keywords_regex(query_lower, keywords)

    def _extract_symptom_data(self, query: str) -> Dict[str, Any]:
        """Extract symptom-specific data from the query."""
        data = {}
        query_lower = query.lower()
        
        # Extract symptom name - prioritize longer, more specific matches first
        symptom_matches = []
        for keyword in self.symptom_keywords:
            if ' ' in keyword:
                # Multi-word phrase
                pattern = re.escape(keyword)
            else:
                # Single word with boundaries
                pattern = r'\b' + re.escape(keyword) + r'\b'
            
            if re.search(pattern, query_lower):
                symptom_matches.append((keyword, len(keyword)))
        
        # Sort by length (longer matches are more specific)
        if symptom_matches:
            symptom_matches.sort(key=lambda x: x[1], reverse=True)
            best_match = symptom_matches[0][0]
            
            # Clean up the symptom name
            if best_match.startswith("my "):
                best_match = best_match[3:]  # Remove "my "
            if best_match.startswith("i have a "):
                best_match = best_match[9:]  # Remove "i have a "
            if best_match.startswith("i've got a "):
                best_match = best_match[11:]  # Remove "i've got a "
            if " hurts" in best_match:
                best_match = best_match.replace(" hurts", "")
            
            data["symptom_name"] = best_match
        
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
            pattern = r'\b' + re.escape(part) + r'\b'
            if re.search(pattern, query_lower):
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
            if ' ' in keyword:
                pattern = re.escape(keyword)
            else:
                pattern = r'\b' + re.escape(keyword) + r'\b'
            
            if re.search(pattern, query_lower):
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
            pattern = r'\b' + re.escape(time_ref) + r'\b'
            if re.search(pattern, query_lower):
                data["appointment_time"] = time_ref
                break
        
        # Extract appointment type
        appointment_types = [
            "checkup", "follow-up", "consultation", "exam", "physical",
            "surgery", "procedure", "screening"
        ]
        
        for apt_type in appointment_types:
            pattern = r'\b' + re.escape(apt_type) + r'\b'
            if re.search(pattern, query_lower):
                data["appointment_type"] = apt_type
                break
        
        logger.info(f"🔍 APPOINTMENT_EXTRACT: Extracted data: {data}")
        return data

    def _extract_history_type(self, query_lower: str) -> Dict[str, Any]:
        """Extract what type of history the user is requesting."""
        data = {}
        
        if re.search(r'\bsymptom', query_lower):
            data["history_type"] = "symptoms"
        elif re.search(r'\b(medication|treatment)', query_lower):
            data["history_type"] = "treatments"
        elif re.search(r'\b(appointment|visit)', query_lower):
            data["history_type"] = "appointments"
        else:
            data["history_type"] = "all"
        
        return data

# Global instance
simple_intent_detector = SimpleIntentDetector()