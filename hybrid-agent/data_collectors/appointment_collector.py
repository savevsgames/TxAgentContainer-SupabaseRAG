"""
Appointment Data Collector for TxAgent Agent Overhaul.

This module handles the conversational flow for collecting
complete appointment data through natural dialogue.
"""

import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger("appointment_collector")

class AppointmentCollector:
    """Handles appointment data collection through conversational flow."""
    
    def __init__(self):
        # Required fields for a complete appointment entry
        self.required_fields = ["doctor_name", "visit_ts"]
        
        # Optional but helpful fields (limit to 2 questions max)
        self.optional_fields = ["location", "visit_summary"]
        
        # Question templates
        self.questions = {
            "doctor_name": "What is the name of the doctor or healthcare provider?",
            "visit_ts": "When is your appointment? (Please include date and time)",
            "location": "Where is the appointment? (clinic name, hospital, etc.)",
            "visit_summary": "What is this appointment for? (checkup, follow-up, specific concern, etc.)"
        }

    def start_collection(self, initial_query: str, existing_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Start appointment collection process."""
        logger.info(f"🚀 APPOINTMENT_COLLECTOR: Starting collection with query: {initial_query}")
        
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
        
        logger.info(f"✅ APPOINTMENT_COLLECTOR: Started collection: {result}")
        return result

    def process_response(self, response: str, current_data: Dict[str, Any], questions_asked: List[str]) -> Dict[str, Any]:
        """Process user response and update data."""
        logger.info(f"🔄 APPOINTMENT_COLLECTOR: Processing response: {response}")
        logger.info(f"🔄 APPOINTMENT_COLLECTOR: Current data: {current_data}")
        
        # Extract new data from response - now extracts ALL possible fields
        new_data = self._extract_from_response(response, current_data, questions_asked)
        
        # Update data
        updated_data = {**current_data, **new_data}
        
        logger.info(f"🔄 APPOINTMENT_COLLECTOR: Updated data: {updated_data}")
        
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
            
            logger.info(f"✅ APPOINTMENT_COLLECTOR: Processed response: {result}")
            return result

    def _extract_from_query(self, query: str) -> Dict[str, Any]:
        """Extract appointment data from initial query."""
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
                if len(name) > 2:
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
                data["appointment_time_text"] = time_ref
                break
        
        # Extract appointment type
        appointment_types = [
            "checkup", "follow-up", "consultation", "exam", "physical",
            "surgery", "procedure", "screening"
        ]
        
        for apt_type in appointment_types:
            pattern = r'\b' + re.escape(apt_type) + r'\b'
            if re.search(pattern, query_lower):
                data["visit_summary"] = f"{apt_type.title()} appointment"
                break
        
        # Extract location indicators
        location_indicators = ["at", "clinic", "hospital", "medical center"]
        for indicator in location_indicators:
            pattern = r'\b' + re.escape(indicator) + r'\b'
            if re.search(pattern, query_lower):
                # Try to extract location name
                words = query.split()
                for i, word in enumerate(words):
                    if word.lower() == indicator and i + 1 < len(words):
                        potential_location = " ".join(words[i+1:i+3])
                        if len(potential_location) > 3:
                            data["location"] = potential_location
                            break
        
        logger.info(f"🔍 EXTRACT_QUERY: Extracted from '{query}': {data}")
        return data

    def _extract_from_response(self, response: str, current_data: Dict[str, Any], questions_asked: List[str]) -> Dict[str, Any]:
        """Extract data from user response - now extracts ALL possible fields."""
        new_data = {}
        response_lower = response.lower().strip()
        
        logger.info(f"🔍 EXTRACT_RESPONSE: Analyzing response: '{response}'")
        
        # ALWAYS try to extract doctor name
        doctor_patterns = [
            r"dr\.?\s+([a-z]+)",
            r"doctor\s+([a-z]+)",
            r"^([a-z]+)$"  # Single name response
        ]
        
        for pattern in doctor_patterns:
            match = re.search(pattern, response_lower)
            if match:
                name = match.group(1).title()
                if len(name) > 2:
                    new_data["doctor_name"] = f"Dr. {name}" if not response.startswith("Dr") else name.title()
                    logger.info(f"🔍 EXTRACT_RESPONSE: Found doctor: {new_data['doctor_name']}")
                    break
        
        # ALWAYS try to extract visit time
        parsed_dt = self._parse_datetime(response)
        if parsed_dt:
            new_data["visit_ts"] = parsed_dt.isoformat()
            logger.info(f"🔍 EXTRACT_RESPONSE: Found visit time: {parsed_dt}")
        else:
            # Store text for later parsing
            time_references = [
                "tomorrow", "today", "next week", "monday", "tuesday", "wednesday",
                "thursday", "friday", "saturday", "sunday"
            ]
            
            for time_ref in time_references:
                pattern = r'\b' + re.escape(time_ref) + r'\b'
                if re.search(pattern, response_lower):
                    new_data["appointment_time_text"] = response.strip()
                    logger.info(f"🔍 EXTRACT_RESPONSE: Found time reference: {response.strip()}")
                    break
        
        # ALWAYS try to extract location
        if len(response.strip()) > 2 and "location" not in current_data:
            # Check if this looks like a location
            location_indicators = ["clinic", "hospital", "medical", "center", "office", "building"]
            if any(word in response_lower for word in location_indicators) or len(response.strip()) < 50:
                new_data["location"] = response.strip()
                logger.info(f"🔍 EXTRACT_RESPONSE: Found location: {response.strip()}")
        
        # ALWAYS try to extract visit summary
        if len(response.strip()) > 2 and "visit_summary" not in current_data:
            appointment_types = [
                "checkup", "follow-up", "consultation", "exam", "physical",
                "surgery", "procedure", "screening"
            ]
            
            for apt_type in appointment_types:
                pattern = r'\b' + re.escape(apt_type) + r'\b'
                if re.search(pattern, response_lower):
                    new_data["visit_summary"] = response.strip()
                    logger.info(f"🔍 EXTRACT_RESPONSE: Found visit summary: {response.strip()}")
                    break
            
            # If no specific type found, use response if it looks like a purpose
            if "visit_summary" not in new_data and len(response.strip()) < 100:
                new_data["visit_summary"] = response.strip()
                logger.info(f"🔍 EXTRACT_RESPONSE: Using response as visit summary: {response.strip()}")
        
        logger.info(f"🔍 EXTRACT_RESPONSE: Final extracted data: {new_data}")
        return new_data

    def _parse_datetime(self, text: str) -> Optional[datetime]:
        """Parse datetime from text input."""
        text_lower = text.lower().strip()
        now = datetime.now()
        
        # Handle relative dates
        if "tomorrow" in text_lower:
            base_date = now + timedelta(days=1)
        elif "today" in text_lower:
            base_date = now
        elif "next week" in text_lower:
            base_date = now + timedelta(days=7)
        elif any(day in text_lower for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
            # Find next occurrence of that day
            days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            for i, day in enumerate(days):
                if day in text_lower:
                    days_ahead = i - now.weekday()
                    if days_ahead <= 0:  # Target day already happened this week
                        days_ahead += 7
                    base_date = now + timedelta(days=days_ahead)
                    break
        else:
            base_date = now
        
        # Extract time if present
        time_pattern = r"(\d{1,2}):?(\d{2})?\s*(am|pm)?"
        time_match = re.search(time_pattern, text_lower)
        
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
            ampm = time_match.group(3)
            
            if ampm == "pm" and hour != 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0
            
            return base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # Default to 9 AM if no time specified
        if text_lower in ["tomorrow", "today", "next week"] or any(day in text_lower for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
            return base_date.replace(hour=9, minute=0, second=0, microsecond=0)
        
        return None

    def _get_next_question(self, data: Dict[str, Any], questions_asked: List[str]) -> Optional[str]:
        """Get the next question to ask."""
        # Check required fields first
        for field in self.required_fields:
            if field not in data and field not in questions_asked:
                # Special handling for visit_ts - check for appointment_time_text too
                if field == "visit_ts" and "appointment_time_text" in data:
                    continue
                return self.questions[field]
        
        # Check optional fields (max 2 questions)
        optional_asked = [q for q in questions_asked if q in self.optional_fields]
        if len(optional_asked) < 2:
            for field in self.optional_fields:
                if field not in data and field not in questions_asked:
                    return self.questions[field]
        
        return None

    def _is_complete(self, data: Dict[str, Any]) -> bool:
        """Check if we have enough data to complete."""
        has_doctor = "doctor_name" in data
        has_time = "visit_ts" in data or "appointment_time_text" in data
        return has_doctor and has_time

    def _calculate_progress(self, data: Dict[str, Any]) -> int:
        """Calculate completion progress."""
        total_fields = len(self.required_fields) + 2  # 2 optional fields
        filled_fields = 0
        
        # Count required fields
        if "doctor_name" in data:
            filled_fields += 1
        if "visit_ts" in data or "appointment_time_text" in data:
            filled_fields += 1
        
        # Count optional fields
        if "location" in data:
            filled_fields += 1
        if "visit_summary" in data:
            filled_fields += 1
        
        return int((filled_fields / total_fields) * 100)

    def _generate_acknowledgment(self, data: Dict[str, Any]) -> str:
        """Generate acknowledgment message."""
        if "doctor_name" in data:
            return f"I understand you have an appointment with {data['doctor_name']}."
        elif "visit_summary" in data:
            return f"I understand you want to track a {data['visit_summary']}."
        else:
            return "I'd like to help you track your appointment."

    def _generate_completion(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate completion message and summary."""
        summary_parts = []
        
        if data.get("doctor_name"):
            summary_parts.append(f"**Doctor**: {data['doctor_name']}")
        
        # Format appointment time
        if data.get("visit_ts"):
            try:
                dt = datetime.fromisoformat(data["visit_ts"])
                formatted_date = dt.strftime("%A, %B %d, %Y at %I:%M %p")
                summary_parts.append(f"**Date & Time**: {formatted_date}")
            except:
                summary_parts.append(f"**Date & Time**: {data['visit_ts']}")
        elif data.get("appointment_time_text"):
            summary_parts.append(f"**Date & Time**: {data['appointment_time_text']}")
        
        if data.get("location"):
            summary_parts.append(f"**Location**: {data['location']}")
        
        if data.get("visit_summary"):
            summary_parts.append(f"**Purpose**: {data['visit_summary']}")
        
        summary = "\n".join(summary_parts)
        
        return {
            "message": f"✅ I've logged your appointment with {data.get('doctor_name', 'your doctor')}.",
            "summary": summary,
            "question": "Does this look correct? Say 'yes' to save it or tell me what to change.",
            "data": data,
            "progress": 100,
            "complete": True
        }

    def prepare_for_database(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for database insertion."""
        # Parse visit timestamp
        visit_ts = None
        if "visit_ts" in data:
            visit_ts = data["visit_ts"]
        elif "appointment_time_text" in data:
            parsed_dt = self._parse_datetime(data["appointment_time_text"])
            if parsed_dt:
                visit_ts = parsed_dt.isoformat()
            else:
                # Default to tomorrow at 9 AM
                visit_ts = (datetime.now() + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0).isoformat()
        
        return {
            "visit_ts": visit_ts,
            "doctor_name": data.get("doctor_name", "Unknown Doctor"),
            "location": data.get("location"),
            "contact_phone": None,  # Not collected in simple flow
            "contact_email": None,  # Not collected in simple flow
            "visit_prep": None,     # Not collected in simple flow
            "visit_summary": data.get("visit_summary"),
            "follow_up_required": False
        }

# Global instance
appointment_collector = AppointmentCollector()