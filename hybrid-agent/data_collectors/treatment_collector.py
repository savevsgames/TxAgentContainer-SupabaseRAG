"""
Treatment Data Collector for TxAgent Agent Overhaul.

This module handles the conversational flow for collecting
complete treatment/medication data through natural dialogue.
"""

import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger("treatment_collector")

class TreatmentCollector:
    """Handles treatment data collection through conversational flow."""
    
    def __init__(self):
        # Required fields for a complete treatment entry
        self.required_fields = ["name", "treatment_type"]
        
        # Optional but helpful fields (limit to 2 questions max)
        self.optional_fields = ["dosage", "duration"]
        
        # Treatment types
        self.treatment_types = [
            "medication", "therapy", "exercise", "diet", "supplement", 
            "procedure", "home_remedy", "lifestyle_change"
        ]
        
        # Question templates
        self.questions = {
            "name": "What is the name of the treatment or medication?",
            "treatment_type": "What type of treatment is this? (medication, therapy, exercise, etc.)",
            "dosage": "What is the dosage or frequency for {name}?",
            "duration": "How long will you be taking/doing {name}?"
        }

    def start_collection(self, initial_query: str, existing_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Start treatment collection process."""
        logger.info(f"🚀 TREATMENT_COLLECTOR: Starting collection with query: {initial_query}")
        
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
        
        logger.info(f"✅ TREATMENT_COLLECTOR: Started collection: {result}")
        return result

    def process_response(self, response: str, current_data: Dict[str, Any], questions_asked: List[str]) -> Dict[str, Any]:
        """Process user response and update data."""
        logger.info(f"🔄 TREATMENT_COLLECTOR: Processing response: {response}")
        
        # Extract new data from response
        new_data = self._extract_from_response(response, current_data, questions_asked)
        
        # Update data
        updated_data = {**current_data, **new_data}
        
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
            
            logger.info(f"✅ TREATMENT_COLLECTOR: Processed response: {result}")
            return result

    def _extract_from_query(self, query: str) -> Dict[str, Any]:
        """Extract treatment data from initial query."""
        data = {}
        query_lower = query.lower()
        
        # Common medication names
        medication_keywords = [
            "ibuprofen", "advil", "motrin", "tylenol", "acetaminophen", "aspirin",
            "aleve", "naproxen", "benadryl", "claritin", "zyrtec",
            "lisinopril", "metformin", "atorvastatin", "omeprazole"
        ]
        
        # Check for specific medications
        for med in medication_keywords:
            if med in query_lower:
                data["name"] = med
                data["treatment_type"] = "medication"
                break
        
        # If no specific medication found, look for treatment type
        if "name" not in data:
            for treatment_type in self.treatment_types:
                if treatment_type in query_lower:
                    data["treatment_type"] = treatment_type
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
        duration_patterns = [
            r"for\s+(\d+)\s*(?:day|week|month)s?",
            r"(\d+)\s*(?:day|week|month)s?",
            r"ongoing",
            r"as\s+needed"
        ]
        
        for pattern in duration_patterns:
            match = re.search(pattern, query_lower)
            if match:
                data["duration"] = match.group(0)
                break
        
        logger.info(f"🔍 EXTRACT_QUERY: Extracted from '{query}': {data}")
        return data

    def _extract_from_response(self, response: str, current_data: Dict[str, Any], questions_asked: List[str]) -> Dict[str, Any]:
        """Extract data from user response to specific question."""
        new_data = {}
        response_lower = response.lower().strip()
        
        # Determine what we're likely asking about
        missing_fields = [field for field in self.required_fields + self.optional_fields 
                         if field not in current_data]
        
        # If we're missing name
        if "name" in missing_fields:
            # Use response as treatment name if reasonable
            if len(response.strip()) > 2 and len(response.strip()) < 50:
                new_data["name"] = response.strip().lower()
        
        # If we're missing treatment_type
        if "treatment_type" in missing_fields:
            for treatment_type in self.treatment_types:
                if treatment_type in response_lower:
                    new_data["treatment_type"] = treatment_type
                    break
            
            # Default to medication if not specified
            if "treatment_type" not in new_data:
                new_data["treatment_type"] = "medication"
        
        # If we're missing dosage
        if "dosage" in missing_fields:
            dosage_patterns = [
                r"(\d+)\s*mg",
                r"(\d+)\s*(?:tablet|pill|capsule)s?",
                r"(\d+)\s*times?\s+(?:a\s+)?day",
                r"once\s+(?:a\s+)?day",
                r"twice\s+(?:a\s+)?day"
            ]
            
            for pattern in dosage_patterns:
                match = re.search(pattern, response_lower)
                if match:
                    new_data["dosage"] = match.group(0)
                    break
            
            # If no pattern matched, use the response as-is if reasonable
            if "dosage" not in new_data and len(response.strip()) > 1:
                new_data["dosage"] = response.strip()
        
        # If we're missing duration
        if "duration" in missing_fields:
            duration_patterns = [
                r"(\d+)\s*(?:day|week|month)s?",
                r"for\s+(\d+)\s*(?:day|week|month)s?",
                r"ongoing",
                r"as\s+needed"
            ]
            
            for pattern in duration_patterns:
                match = re.search(pattern, response_lower)
                if match:
                    new_data["duration"] = match.group(0)
                    break
            
            # If no pattern matched, use response as-is if reasonable
            if "duration" not in new_data and len(response.strip()) > 1:
                new_data["duration"] = response.strip()
        
        logger.info(f"🔍 EXTRACT_RESPONSE: From '{response}': {new_data}")
        return new_data

    def _get_next_question(self, data: Dict[str, Any], questions_asked: List[str]) -> Optional[str]:
        """Get the next question to ask."""
        # Check required fields first
        for field in self.required_fields:
            if field not in data and field not in questions_asked:
                question = self.questions[field]
                if "{name}" in question and "name" in data:
                    question = question.format(name=data["name"])
                return question
        
        # Check optional fields (max 2 questions)
        optional_asked = [q for q in questions_asked if q in self.optional_fields]
        if len(optional_asked) < 2:
            for field in self.optional_fields:
                if field not in data and field not in questions_asked:
                    question = self.questions[field]
                    if "{name}" in question and "name" in data:
                        question = question.format(name=data["name"])
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
        if "name" in data:
            return f"I understand you want to track {data['name']}."
        else:
            return "I'd like to help you track your treatment or medication."

    def _generate_completion(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate completion message and summary."""
        summary_parts = []
        
        if data.get("name"):
            summary_parts.append(f"**Treatment**: {data['name'].title()}")
        
        if data.get("treatment_type"):
            summary_parts.append(f"**Type**: {data['treatment_type'].title()}")
        
        if data.get("dosage"):
            summary_parts.append(f"**Dosage**: {data['dosage']}")
        
        if data.get("duration"):
            summary_parts.append(f"**Duration**: {data['duration']}")
        
        summary = "\n".join(summary_parts)
        
        return {
            "message": f"✅ I've logged your {data.get('name', 'treatment')}.",
            "summary": summary,
            "question": "Does this look correct? Say 'yes' to save it or tell me what to change.",
            "data": data,
            "progress": 100,
            "complete": True
        }

    def prepare_for_database(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for database insertion."""
        return {
            "name": data.get("name", "unknown"),
            "treatment_type": data.get("treatment_type", "medication"),
            "dosage": data.get("dosage"),
            "duration": data.get("duration"),
            "description": self._create_description(data),
            "doctor_recommended": False,  # Not collected in simple flow
            "completed": False,
            "notes": f"Added via conversational tracking on {datetime.now().strftime('%Y-%m-%d')}"
        }

    def _create_description(self, data: Dict[str, Any]) -> str:
        """Create a description from collected data."""
        parts = []
        
        name = data.get("name", "treatment")
        treatment_type = data.get("treatment_type", "")
        
        if treatment_type:
            parts.append(f"Type: {treatment_type}")
        
        if data.get("dosage"):
            parts.append(f"Dosage: {data['dosage']}")
        
        if data.get("duration"):
            parts.append(f"Duration: {data['duration']}")
        
        if parts:
            return f"{name.title()} - {', '.join(parts)}"
        else:
            return name.title()

# Global instance
treatment_collector = TreatmentCollector()