"""
Appointment Tracking Loop Manager for TxAgent.

This module handles the conversational loop for appointment tracking,
managing incremental data collection and temporary storage until
a complete appointment entry can be saved. Enhanced with flexibility features.
"""

import logging
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import re

from core.auth_service import auth_service

logger = logging.getLogger("appointment_tracker")

class AppointmentTracker:
    """Manages conversational appointment tracking with incremental data collection and enhanced flexibility."""
    
    def __init__(self):
        # In-memory storage for incomplete appointment entries
        self.active_sessions = {}
        
        # Required fields for a complete appointment entry
        self.required_fields = ["visit_ts", "doctor_name"]
        
        # Optional but helpful fields
        self.optional_fields = ["location", "contact_phone", "visit_prep", "visit_summary"]
        
        # Follow-up questions for missing fields
        self.follow_up_questions = {
            "visit_ts": "When is your appointment? (Please include date and time)",
            "doctor_name": "What is the name of the doctor or healthcare provider?",
            "location": "Where is the appointment? (clinic name, hospital, etc.)",
            "contact_phone": "Do you have a contact phone number for the appointment?",
            "visit_prep": "Is there anything you need to prepare for this appointment?",
            "visit_summary": "What is this appointment for? (checkup, follow-up, specific concern, etc.)"
        }
        
        # Common doctor specialties
        self.doctor_specialties = [
            "cardiologist", "dermatologist", "neurologist", "orthopedist", "psychiatrist",
            "gynecologist", "urologist", "oncologist", "endocrinologist", "gastroenterologist",
            "pulmonologist", "rheumatologist", "ophthalmologist", "ent", "radiologist"
        ]

    def start_appointment_tracking(self, user_id: str, initial_query: str) -> Dict[str, Any]:
        """Start a new appointment tracking session with intelligent question skipping."""
        session_id = f"appointment_{user_id}_{datetime.now().timestamp()}"
        
        # Initialize session with extracted data from initial query
        initial_data = self._extract_initial_data(initial_query)
        
        self.active_sessions[session_id] = {
            "user_id": user_id,
            "appointment_data": initial_data,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "questions_asked": [],
            "is_complete": False,
            "last_question": None
        }
        
        logger.info(f"🔍 APPOINTMENT_TRACKER: Started session {session_id} with initial data: {initial_data}")
        
        # Determine next question (intelligent skipping)
        next_question = self._get_next_question(session_id)
        
        return {
            "session_id": session_id,
            "message": self._generate_acknowledgment(initial_data),
            "next_question": next_question,
            "progress": self._calculate_progress(session_id)
        }

    def update_appointment_data(self, session_id: str, user_response: str) -> Dict[str, Any]:
        """Update appointment data based on user response with intelligent extraction."""
        if session_id not in self.active_sessions:
            return {"error": "Session not found"}
        
        session = self.active_sessions[session_id]
        
        # Extract new data from user response (enhanced to extract multiple fields at once)
        new_data = self._extract_data_from_response(user_response, session["appointment_data"])
        
        # Update session data
        session["appointment_data"].update(new_data)
        session["last_updated"] = datetime.now().isoformat()
        
        logger.info(f"🔍 APPOINTMENT_TRACKER: Updated session {session_id} with: {new_data}")
        
        # Check if we have enough data to complete the entry
        if self._is_complete(session_id):
            return self._complete_appointment_entry(session_id)
        else:
            # Ask next question (intelligent skipping)
            next_question = self._get_next_question(session_id)
            session["last_question"] = next_question
            
            return {
                "session_id": session_id,
                "message": "Got it.",
                "next_question": next_question,
                "progress": self._calculate_progress(session_id),
                "current_data": self._format_current_data(session["appointment_data"])
            }

    def _extract_initial_data(self, query: str) -> Dict[str, Any]:
        """Extract initial appointment data from user's query with enhanced extraction."""
        data = {}
        query_lower = query.lower()
        
        # Extract doctor name patterns
        doctor_patterns = [
            r"dr\.?\s+([a-z]+)",
            r"doctor\s+([a-z]+)",
            r"with\s+([a-z]+)",
            r"see\s+([a-z]+)"
        ]
        
        for pattern in doctor_patterns:
            match = re.search(pattern, query_lower)
            if match:
                potential_name = match.group(1).title()
                if len(potential_name) > 2:
                    data["doctor_name"] = f"Dr. {potential_name}"
                    break
        
        # Extract date/time patterns
        date_patterns = [
            r"tomorrow",
            r"next\s+week",
            r"monday|tuesday|wednesday|thursday|friday|saturday|sunday",
            r"(\d{1,2})/(\d{1,2})",
            r"(\d{1,2})\s*(?:am|pm)",
            r"at\s+(\d{1,2}):?(\d{2})?\s*(?:am|pm)?"
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, query_lower)
            if match:
                data["visit_ts_text"] = match.group(0)
                # We'll parse this more thoroughly later
                break
        
        # Extract location/clinic names
        location_indicators = ["at", "clinic", "hospital", "medical center", "office"]
        for indicator in location_indicators:
            if indicator in query_lower:
                # Try to extract the location name
                words = query.split()
                for i, word in enumerate(words):
                    if word.lower() == indicator and i + 1 < len(words):
                        potential_location = " ".join(words[i+1:i+3])
                        if len(potential_location) > 3:
                            data["location"] = potential_location
                            break
        
        # Extract appointment purpose
        purpose_indicators = [
            "checkup", "follow-up", "consultation", "exam", "screening",
            "physical", "annual", "routine", "surgery", "procedure"
        ]
        
        for purpose in purpose_indicators:
            if purpose in query_lower:
                data["visit_summary"] = f"{purpose.title()} appointment"
                break
        
        return data

    def _extract_data_from_response(self, response: str, existing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract data from user's response to a specific question with enhanced multi-field extraction."""
        new_data = {}
        response_lower = response.lower()
        
        # Enhanced extraction - try to get multiple fields from a single response
        
        # If we're missing doctor_name, try to extract it
        if "doctor_name" not in existing_data:
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
                        break
        
        # If we're missing visit_ts, try to extract it
        if "visit_ts" not in existing_data:
            # Parse common date/time formats
            date_time = self._parse_datetime(response)
            if date_time:
                new_data["visit_ts"] = date_time.isoformat()
            else:
                # Store the text for manual parsing later
                new_data["visit_ts_text"] = response
        
        # Extract location if missing
        if "location" not in existing_data:
            # Clean up the response as a location
            if len(response.strip()) > 2:
                new_data["location"] = response.strip()
        
        # Extract phone number if missing
        if "contact_phone" not in existing_data:
            phone_pattern = r"(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})"
            match = re.search(phone_pattern, response)
            if match:
                new_data["contact_phone"] = match.group(1)
        
        # Extract visit preparation if missing
        if "visit_prep" not in existing_data and len(response.strip()) > 5:
            new_data["visit_prep"] = response.strip()
        
        # Extract visit summary if missing
        if "visit_summary" not in existing_data and len(response.strip()) > 5:
            new_data["visit_summary"] = response.strip()
        
        return new_data

    def _parse_datetime(self, text: str) -> Optional[datetime]:
        """Parse datetime from text input."""
        text_lower = text.lower().strip()
        now = datetime.now()
        
        # Handle relative dates
        if "tomorrow" in text_lower:
            base_date = now + timedelta(days=1)
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
        
        # If no time specified, default to 9 AM
        if text_lower in ["tomorrow", "next week"] or any(day in text_lower for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
            return base_date.replace(hour=9, minute=0, second=0, microsecond=0)
        
        return None

    def _get_next_question(self, session_id: str) -> Optional[str]:
        """Get the next question to ask the user with intelligent skipping."""
        session = self.active_sessions[session_id]
        appointment_data = session["appointment_data"]
        questions_asked = session["questions_asked"]
        
        # Check required fields first - skip if already present
        for field in self.required_fields:
            if field not in appointment_data and field not in questions_asked:
                # Special handling for visit_ts - check for visit_ts_text too
                if field == "visit_ts" and "visit_ts_text" in appointment_data:
                    continue
                session["questions_asked"].append(field)
                return self.follow_up_questions[field]
        
        # Check optional fields (but only ask 1-2 more questions) - skip if already present
        optional_asked = [q for q in questions_asked if q in self.optional_fields]
        if len(optional_asked) < 2:
            for field in self.optional_fields:
                if field not in appointment_data and field not in questions_asked:
                    session["questions_asked"].append(field)
                    return self.follow_up_questions[field]
        
        return None

    def _is_complete(self, session_id: str) -> bool:
        """Check if we have enough data to complete the appointment entry."""
        session = self.active_sessions[session_id]
        appointment_data = session["appointment_data"]
        
        # Must have all required fields (or their text equivalents)
        has_datetime = "visit_ts" in appointment_data or "visit_ts_text" in appointment_data
        has_doctor = "doctor_name" in appointment_data
        
        if not (has_datetime and has_doctor):
            return False
        
        # Or if we've asked enough questions
        if len(session["questions_asked"]) >= 4:
            return True
        
        return True

    def _complete_appointment_entry(self, session_id: str) -> Dict[str, Any]:
        """Complete the appointment entry and prepare for database save."""
        session = self.active_sessions[session_id]
        appointment_data = session["appointment_data"]
        user_id = session["user_id"]
        
        # Parse visit timestamp
        visit_ts = None
        if "visit_ts" in appointment_data:
            visit_ts = appointment_data["visit_ts"]
        elif "visit_ts_text" in appointment_data:
            parsed_dt = self._parse_datetime(appointment_data["visit_ts_text"])
            if parsed_dt:
                visit_ts = parsed_dt.isoformat()
            else:
                # Default to tomorrow at 9 AM if we can't parse
                visit_ts = (datetime.now() + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0).isoformat()
        
        # Prepare data for database
        db_data = {
            "visit_ts": visit_ts,
            "doctor_name": appointment_data.get("doctor_name", "Unknown Doctor"),
            "location": appointment_data.get("location"),
            "contact_phone": appointment_data.get("contact_phone"),
            "contact_email": None,  # Not collected in this flow
            "visit_prep": appointment_data.get("visit_prep"),
            "visit_summary": appointment_data.get("visit_summary"),
            "follow_up_required": False  # Default to false
        }
        
        # Mark session as complete
        session["is_complete"] = True
        session["final_data"] = db_data
        
        logger.info(f"✅ APPOINTMENT_TRACKER: Completed session {session_id} with data: {db_data}")
        
        return {
            "session_id": session_id,
            "status": "complete",
            "message": f"✅ I've successfully logged your appointment with {appointment_data.get('doctor_name', 'your doctor')}.",
            "summary": self._format_summary(appointment_data, visit_ts),
            "db_data": db_data,
            "confirmation_question": "Does this look correct? You can say 'yes' to save it or tell me what to change."
        }

    def _format_summary(self, appointment_data: Dict[str, Any], visit_ts: str) -> str:
        """Format a summary of the collected data."""
        summary_parts = []
        
        if appointment_data.get("doctor_name"):
            summary_parts.append(f"**Doctor**: {appointment_data['doctor_name']}")
        
        if visit_ts:
            try:
                dt = datetime.fromisoformat(visit_ts.replace('Z', '+00:00'))
                formatted_date = dt.strftime("%A, %B %d, %Y at %I:%M %p")
                summary_parts.append(f"**Date & Time**: {formatted_date}")
            except:
                summary_parts.append(f"**Date & Time**: {visit_ts}")
        
        if appointment_data.get("location"):
            summary_parts.append(f"**Location**: {appointment_data['location']}")
        
        if appointment_data.get("visit_summary"):
            summary_parts.append(f"**Purpose**: {appointment_data['visit_summary']}")
        
        if appointment_data.get("contact_phone"):
            summary_parts.append(f"**Contact**: {appointment_data['contact_phone']}")
        
        return "\n".join(summary_parts)

    def _calculate_progress(self, session_id: str) -> Dict[str, Any]:
        """Calculate completion progress."""
        session = self.active_sessions[session_id]
        appointment_data = session["appointment_data"]
        
        total_fields = len(self.required_fields) + 2  # 2 most important optional fields
        filled_fields = 0
        
        # Count required fields
        if "visit_ts" in appointment_data or "visit_ts_text" in appointment_data:
            filled_fields += 1
        if "doctor_name" in appointment_data:
            filled_fields += 1
        
        # Count important optional fields
        if "location" in appointment_data:
            filled_fields += 1
        if "visit_summary" in appointment_data:
            filled_fields += 1
        
        return {
            "filled_fields": filled_fields,
            "total_fields": total_fields,
            "percentage": int((filled_fields / total_fields) * 100)
        }

    def _generate_acknowledgment(self, initial_data: Dict[str, Any]) -> str:
        """Generate an acknowledgment message based on initial data."""
        if "doctor_name" in initial_data:
            return f"I understand you have an appointment with {initial_data['doctor_name']}."
        elif "visit_summary" in initial_data:
            return f"I understand you want to track a {initial_data['visit_summary']}."
        else:
            return "I'd like to help you track your appointment."

    def _format_current_data(self, appointment_data: Dict[str, Any]) -> str:
        """Format current data for user review."""
        if not appointment_data:
            return "No data collected yet."
        
        parts = []
        if appointment_data.get("doctor_name"):
            parts.append(f"Doctor: {appointment_data['doctor_name']}")
        if appointment_data.get("visit_ts_text"):
            parts.append(f"When: {appointment_data['visit_ts_text']}")
        if appointment_data.get("location"):
            parts.append(f"Where: {appointment_data['location']}")
        if appointment_data.get("visit_summary"):
            parts.append(f"Purpose: {appointment_data['visit_summary']}")
        
        return " | ".join(parts) if parts else "Partial data collected."

    async def save_to_database(self, session_id: str, jwt_token: str) -> Dict[str, Any]:
        """Save the completed appointment entry to the database."""
        if session_id not in self.active_sessions:
            return {"error": "Session not found"}
        
        session = self.active_sessions[session_id]
        if not session.get("is_complete"):
            return {"error": "Session not complete"}
        
        db_data = session["final_data"]
        user_id = session["user_id"]
        
        try:
            # Get authenticated client
            client = auth_service.get_authenticated_client(jwt_token)
            
            # Insert into database
            result = client.table("doctor_visits").insert({
                "user_id": user_id,
                "visit_ts": db_data["visit_ts"],
                "doctor_name": db_data["doctor_name"],
                "location": db_data["location"],
                "contact_phone": db_data["contact_phone"],
                "contact_email": db_data["contact_email"],
                "visit_prep": db_data["visit_prep"],
                "visit_summary": db_data["visit_summary"],
                "follow_up_required": db_data["follow_up_required"]
            }).execute()
            
            if hasattr(result, 'error') and result.error:
                logger.error(f"❌ APPOINTMENT_TRACKER: Database error: {result.error}")
                return {"error": f"Database error: {result.error}"}
            
            appointment_id = result.data[0]["id"] if result.data else None
            
            # Clean up session
            del self.active_sessions[session_id]
            
            logger.info(f"✅ APPOINTMENT_TRACKER: Saved appointment {appointment_id} and cleaned up session {session_id}")
            
            return {
                "success": True,
                "appointment_id": appointment_id,
                "message": "Appointment successfully saved to your health log!",
                "data": result.data[0] if result.data else None
            }
            
        except Exception as e:
            logger.error(f"❌ APPOINTMENT_TRACKER: Error saving to database: {str(e)}")
            return {"error": f"Failed to save appointment: {str(e)}"}

    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a tracking session."""
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        return {
            "session_id": session_id,
            "is_complete": session.get("is_complete", False),
            "progress": self._calculate_progress(session_id),
            "current_data": self._format_current_data(session["appointment_data"]),
            "questions_asked": len(session["questions_asked"]),
            "last_question": session.get("last_question")
        }

    def cancel_session(self, session_id: str) -> Dict[str, Any]:
        """Cancel a tracking session."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info(f"✅ APPOINTMENT_TRACKER: Cancelled session {session_id}")
            return {"success": True}
        return {"success": False, "error": "Session not found"}

    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a formatted summary of the current session."""
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        appointment_data = session["appointment_data"]
        
        summary = self._format_summary(appointment_data, appointment_data.get("visit_ts"))
        progress = self._calculate_progress(session_id)
        next_question = self._get_next_question(session_id)
        
        return {
            "summary": summary if summary else "No appointment data collected yet.",
            "progress": progress,
            "next_question": next_question
        }

    def edit_field(self, session_id: str, field_name: str, new_value: Any) -> Dict[str, Any]:
        """Edit a specific field in the session data."""
        if session_id not in self.active_sessions:
            return {"success": False, "error": "Session not found"}
        
        session = self.active_sessions[session_id]
        
        # Validate field name
        valid_fields = self.required_fields + self.optional_fields
        if field_name not in valid_fields:
            return {"success": False, "error": f"Invalid field: {field_name}"}
        
        # Update the field
        session["appointment_data"][field_name] = new_value
        session["last_updated"] = datetime.now().isoformat()
        
        logger.info(f"✅ APPOINTMENT_TRACKER: Updated {field_name} to {new_value} in session {session_id}")
        
        return {
            "success": True,
            "message": f"Updated {field_name} to {new_value}",
            "current_data": self._format_current_data(session["appointment_data"])
        }

# Global instance
appointment_tracker = AppointmentTracker()