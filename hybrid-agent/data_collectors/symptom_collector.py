"""
Symptom Data Collector for TxAgent Agent Overhaul.

This module handles the conversational flow for collecting
complete symptom data through natural dialogue.
"""

import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger("symptom_collector")

class SymptomCollector:
    """Handles symptom data collection through conversational flow."""
    
    def __init__(self):
        # Required fields for a complete symptom entry
        self.required_fields = ["symptom_name", "severity"]
        
        # Optional but helpful fields (limit to 2 questions max)
        self.optional_fields = ["duration_hours", "location"]
        
        # Question templates
        self.questions = {
            "symptom_name": "What specific symptom are you experiencing?",
            "severity": "On a scale of 1-10, how severe is your {symptom_name}?",
            "duration_hours": "How long have you been experiencing this {symptom_name}?",
            "location": "Where exactly do you feel the {symptom_name}?"
        }
        
        # Duration conversion patterns
        self.duration_patterns = {
            r"(\d+)\s*hour": lambda x: int(x),
            r"(\d+)\s*day": lambda x: int(x) * 24,
            r"(\d+)\s*week": lambda x: int(x) * 24 * 7,
            r"all\s+day": lambda x: 24,
            r"few\s+hours": lambda x: 3,
            r"since\s+morning": lambda x: 8,
            r"since\s+yesterday": lambda x: 24
        }

    def start_collection(self, initial_query: str, existing_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Start symptom collection process."""
        logger.info(f"🚀 SYMPTOM_COLLECTOR: Starting collection with query: {initial_query}")
        
        # Start with any existing data or extract from initial query
        data = existing_data or {}
        extracted = self._extract_from_query(initial_query)
        data.update(extracted)
        
        # Generate acknowledgment
        acknowledgment = self._generate_acknowledgment(data)
        
        # Determine next question
        next_question = self._get_next_question(data, [])
        
        result = {
            "message": acknowledgment,
            "question": next_question,
            "data": data,
            "progress": self._calculate_progress(data),
            "complete": False
        }
        
        logger.info(f"✅ SYMPTOM_COLLECTOR: Started collection: {result}")
        return result

    def process_response(self, response: str, current_data: Dict[str, Any], questions_asked: List[str]) -> Dict[str, Any]:
        """Process user response and update data."""
        logger.info(f"🔄 SYMPTOM_COLLECTOR: Processing response: {response}")
        logger.info(f"🔄 SYMPTOM_COLLECTOR: Current data: {current_data}")
        logger.info(f"🔄 SYMPTOM_COLLECTOR: Questions asked: {questions_asked}")
        
        # Extract new data from response - now extracts ALL possible fields
        new_data = self._extract_from_response(response, current_data, questions_asked)
        
        # Update data
        updated_data = {**current_data, **new_data}
        
        logger.info(f"🔄 SYMPTOM_COLLECTOR: Updated data: {updated_data}")
        
        # Check if complete
        if self._is_complete(updated_data):
            return self._generate_completion(updated_data)
        else:
            # Get next question
            next_question = self._get_next_question(updated_data, questions_asked)
            
            result = {
                "message": "Got it.",
                "question": next_question,
                "data": updated_data,
                "progress": self._calculate_progress(updated_data),
                "complete": False
            }
            
            logger.info(f"✅ SYMPTOM_COLLECTOR: Processed response: {result}")
            return result

    def _extract_from_query(self, query: str) -> Dict[str, Any]:
        """Extract symptom data from initial query."""
        data = {}
        query_lower = query.lower()
        
        # Extract symptom name using comprehensive list
        symptom_keywords = [
            "headache", "migraine", "pain", "ache", "hurt", "sore", "fever",
            "nausea", "dizziness", "fatigue", "toothache", "earache", "backache",
            "sore throat", "runny nose", "cough", "stomach ache", "chest pain",
            "back pain", "joint pain", "muscle pain", "neck pain", "knee pain",
            "sore knee", "sore back", "sore neck", "sore shoulder"
        ]
        
        for symptom in symptom_keywords:
            if ' ' in symptom:
                # Multi-word phrase
                pattern = re.escape(symptom)
            else:
                # Single word with boundaries
                pattern = r'\b' + re.escape(symptom) + r'\b'
            
            if re.search(pattern, query_lower):
                data["symptom_name"] = symptom
                break
        
        # Extract severity
        severity_patterns = [
            r"(\d+)\s*(?:out of|/)\s*(\d+)",
            r"severity\s*(?:of\s*)?(\d+)",
            r"(\d+)\s*(?:scale|/10)",
            r"\b(\d+)\b"  # Any single digit number
        ]
        
        for pattern in severity_patterns:
            match = re.search(pattern, query_lower)
            if match:
                if len(match.groups()) == 2:
                    value = int(match.group(1))
                    max_value = int(match.group(2))
                    data["severity"] = min(10, max(1, int((value / max_value) * 10)))
                else:
                    severity_value = int(match.group(1))
                    if 1 <= severity_value <= 10:
                        data["severity"] = severity_value
                break
        
        # Extract duration
        for pattern, converter in self.duration_patterns.items():
            match = re.search(pattern, query_lower)
            if match:
                try:
                    if match.groups():
                        data["duration_hours"] = converter(match.group(1))
                    else:
                        data["duration_hours"] = converter(None)
                    break
                except:
                    continue
        
        # Extract location
        body_parts = [
            "head", "forehead", "neck", "throat", "chest", "back", "stomach",
            "arm", "leg", "knee", "shoulder", "tooth", "teeth", "ear", "eye"
        ]
        
        for part in body_parts:
            pattern = r'\b' + re.escape(part) + r'\b'
            if re.search(pattern, query_lower):
                data["location"] = part
                break
        
        logger.info(f"🔍 EXTRACT_QUERY: Extracted from '{query}': {data}")
        return data

    def _extract_from_response(self, response: str, current_data: Dict[str, Any], questions_asked: List[str]) -> Dict[str, Any]:
        """Extract data from user response - now extracts ALL possible fields."""
        new_data = {}
        response_lower = response.lower().strip()
        
        logger.info(f"🔍 EXTRACT_RESPONSE: Analyzing response: '{response}'")
        
        # ALWAYS try to extract severity if we see a number
        severity_patterns = [
            r"(\d+)\s*(?:out of|/)\s*(\d+)",  # "6 out of 10" or "6/10"
            r"severity\s*(?:of\s*)?(\d+)",     # "severity 6" or "severity of 6"
            r"(\d+)\s*(?:scale|/10)",          # "6 scale" or "6/10"
            r"\b(\d+)\b"                       # Any single digit number
        ]
        
        for pattern in severity_patterns:
            match = re.search(pattern, response_lower)
            if match:
                if len(match.groups()) == 2:
                    # Scale format like "6/10"
                    value = int(match.group(1))
                    max_value = int(match.group(2))
                    severity = min(10, max(1, int((value / max_value) * 10)))
                else:
                    # Single number
                    severity = int(match.group(1))
                    if 1 <= severity <= 10:
                        new_data["severity"] = severity
                        logger.info(f"🔍 EXTRACT_RESPONSE: Found severity: {severity}")
                        break
        
        # ALWAYS try to extract duration
        for pattern, converter in self.duration_patterns.items():
            match = re.search(pattern, response_lower)
            if match:
                try:
                    if match.groups():
                        duration = converter(match.group(1))
                        new_data["duration_hours"] = duration
                        logger.info(f"🔍 EXTRACT_RESPONSE: Found duration: {duration} hours")
                    else:
                        duration = converter(None)
                        new_data["duration_hours"] = duration
                        logger.info(f"🔍 EXTRACT_RESPONSE: Found duration: {duration} hours")
                    break
                except:
                    continue
        
        # ALWAYS try to extract location
        body_parts = [
            "head", "forehead", "neck", "throat", "chest", "back", "stomach",
            "arm", "leg", "knee", "shoulder", "tooth", "teeth", "ear", "eye"
        ]
        
        for part in body_parts:
            pattern = r'\b' + re.escape(part) + r'\b'
            if re.search(pattern, response_lower):
                new_data["location"] = part
                logger.info(f"🔍 EXTRACT_RESPONSE: Found location: {part}")
                break
        
        # ALWAYS try to extract symptom name if missing
        if "symptom_name" not in current_data:
            symptom_keywords = [
                "headache", "migraine", "pain", "ache", "hurt", "sore", "fever",
                "nausea", "dizziness", "fatigue", "toothache", "earache", "backache",
                "sore throat", "runny nose", "cough", "stomach ache", "chest pain",
                "back pain", "joint pain", "muscle pain", "neck pain", "knee pain",
                "sore knee", "sore back", "sore neck", "sore shoulder"
            ]
            
            for symptom in symptom_keywords:
                if ' ' in symptom:
                    pattern = re.escape(symptom)
                else:
                    pattern = r'\b' + re.escape(symptom) + r'\b'
                
                if re.search(pattern, response_lower):
                    new_data["symptom_name"] = symptom
                    logger.info(f"🔍 EXTRACT_RESPONSE: Found symptom: {symptom}")
                    break
            
            # If no specific symptom found, use the response as symptom name if reasonable
            if "symptom_name" not in new_data and len(response.strip()) > 2 and len(response.strip()) < 30:
                new_data["symptom_name"] = response.strip().lower()
                logger.info(f"🔍 EXTRACT_RESPONSE: Using response as symptom: {response.strip().lower()}")
        
        logger.info(f"🔍 EXTRACT_RESPONSE: Final extracted data: {new_data}")
        return new_data

    def _get_next_question(self, data: Dict[str, Any], questions_asked: List[str]) -> Optional[str]:
        """Get the next question to ask."""
        # Check required fields first
        for field in self.required_fields:
            if field not in data and field not in questions_asked:
                question = self.questions[field]
                if "{symptom_name}" in question and "symptom_name" in data:
                    question = question.format(symptom_name=data["symptom_name"])
                return question
        
        # Check optional fields (max 2 questions)
        optional_asked = [q for q in questions_asked if q in self.optional_fields]
        if len(optional_asked) < 2:
            for field in self.optional_fields:
                if field not in data and field not in questions_asked:
                    question = self.questions[field]
                    if "{symptom_name}" in question and "symptom_name" in data:
                        question = question.format(symptom_name=data["symptom_name"])
                    return question
        
        return None

    def _is_complete(self, data: Dict[str, Any]) -> bool:
        """Check if we have enough data to complete."""
        return all(field in data for field in self.required_fields)

    def _calculate_progress(self, data: Dict[str, Any]) -> int:
        """Calculate completion progress."""
        total_fields = len(self.required_fields) + 2  # 2 optional fields
        filled_fields = len([f for f in self.required_fields + self.optional_fields[:2] if f in data])
        return int((filled_fields / total_fields) * 100)

    def _generate_acknowledgment(self, data: Dict[str, Any]) -> str:
        """Generate acknowledgment message."""
        if "symptom_name" in data:
            return f"I understand you're experiencing {data['symptom_name']}."
        else:
            return "I'd like to help you track your symptom."

    def _generate_completion(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate completion message and summary."""
        summary_parts = []
        
        if data.get("symptom_name"):
            summary_parts.append(f"**Symptom**: {data['symptom_name'].title()}")
        
        if data.get("severity"):
            summary_parts.append(f"**Severity**: {data['severity']}/10")
        
        if data.get("duration_hours"):
            duration = self._format_duration(data["duration_hours"])
            summary_parts.append(f"**Duration**: {duration}")
        
        if data.get("location"):
            summary_parts.append(f"**Location**: {data['location']}")
        
        summary = "\n".join(summary_parts)
        
        return {
            "message": f"✅ I've logged your {data.get('symptom_name', 'symptom')}.",
            "summary": summary,
            "question": "Does this look correct? Say 'yes' to save it or tell me what to change.",
            "data": data,
            "progress": 100,
            "complete": True
        }

    def _format_duration(self, hours: int) -> str:
        """Format duration in human-readable way."""
        if hours < 1:
            return "less than an hour"
        elif hours == 1:
            return "1 hour"
        elif hours < 24:
            return f"{hours} hours"
        elif hours == 24:
            return "1 day"
        else:
            days = hours // 24
            return f"{days} day{'s' if days > 1 else ''}"

    def prepare_for_database(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for database insertion."""
        return {
            "symptom_name": data.get("symptom_name", "unknown"),
            "severity": data.get("severity"),
            "duration_hours": data.get("duration_hours"),
            "location": data.get("location"),
            "description": self._create_description(data),
            "triggers": [],  # Not collected in this simple flow
            "metadata": {
                "collection_method": "conversational",
                "collected_at": datetime.now().isoformat()
            }
        }

    def _create_description(self, data: Dict[str, Any]) -> str:
        """Create a description from collected data."""
        parts = []
        
        symptom_name = data.get("symptom_name", "symptom")
        
        if data.get("severity"):
            parts.append(f"severity {data['severity']}/10")
        
        if data.get("duration_hours"):
            duration = self._format_duration(data["duration_hours"])
            parts.append(f"duration {duration}")
        
        if data.get("location"):
            parts.append(f"location: {data['location']}")
        
        if parts:
            return f"{symptom_name.title()} - {', '.join(parts)}"
        else:
            return symptom_name.title()

# Global instance
symptom_collector = SymptomCollector()