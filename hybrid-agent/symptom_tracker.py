"""
Symptom Tracking Loop Manager for TxAgent.

This module handles the conversational loop for symptom tracking,
managing incremental data collection and temporary storage until
a complete symptom entry can be saved. Enhanced with flexibility features.
"""

import logging
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from fastapi import Request
from fastapi.responses import JSONResponse

from core.auth_service import auth_service

logger = logging.getLogger("symptom_tracker")

class SymptomTracker:
    """Manages conversational symptom tracking with incremental data collection and enhanced flexibility."""
    
    def __init__(self):
        # In-memory storage for incomplete symptom entries
        # In production, this could be Redis or a temporary database table
        self.active_sessions = {}
        
        # Required fields for a complete symptom entry
        self.required_fields = ["symptom_name", "severity"]
        
        # Optional but helpful fields
        self.optional_fields = ["duration_hours", "location", "triggers", "quality"]
        
        # Follow-up questions for missing fields
        self.follow_up_questions = {
            "symptom_name": "What specific symptom are you experiencing?",
            "severity": "On a scale of 1-10, how severe is your {symptom_name}?",
            "duration_hours": "How long have you been experiencing this {symptom_name}?",
            "location": "Where exactly do you feel the {symptom_name}?",
            "triggers": "Do you notice anything that triggers or worsens your {symptom_name}?",
            "quality": "How would you describe the {symptom_name}? (e.g., sharp, dull, throbbing)"
        }
        
        # Duration parsing patterns
        self.duration_patterns = {
            r"(\d+)\s*hour": lambda x: int(x),
            r"(\d+)\s*day": lambda x: int(x) * 24,
            r"(\d+)\s*week": lambda x: int(x) * 24 * 7,
            r"all\s+day": lambda x: 24,
            r"few\s+hours": lambda x: 3,
            r"couple\s+hours": lambda x: 2,
            r"since\s+morning": lambda x: 8,
            r"since\s+yesterday": lambda x: 24
        }

    def start_symptom_tracking(self, user_id: str, initial_query: str) -> Dict[str, Any]:
        """Start a new symptom tracking session with intelligent question skipping."""
        session_id = f"symptom_{user_id}_{datetime.now().timestamp()}"
        
        # Initialize session with extracted data from initial query
        initial_data = self._extract_initial_data(initial_query)
        
        self.active_sessions[session_id] = {
            "user_id": user_id,
            "symptom_data": initial_data,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "questions_asked": [],
            "is_complete": False,
            "last_question": None
        }
        
        logger.info(f"🔍 SYMPTOM_TRACKER: Started session {session_id} with initial data: {initial_data}")
        
        # Determine next question (intelligent skipping)
        next_question = self._get_next_question(session_id)
        
        return {
            "session_id": session_id,
            "message": self._generate_acknowledgment(initial_data),
            "next_question": next_question,
            "progress": self._calculate_progress(session_id)
        }

    def update_symptom_data(self, session_id: str, user_response: str) -> Dict[str, Any]:
        """Update symptom data based on user response with intelligent extraction."""
        if session_id not in self.active_sessions:
            return {"error": "Session not found"}
        
        session = self.active_sessions[session_id]
        
        # Extract new data from user response (enhanced to extract multiple fields at once)
        new_data = self._extract_data_from_response(user_response, session["symptom_data"])
        
        # Update session data
        session["symptom_data"].update(new_data)
        session["last_updated"] = datetime.now().isoformat()
        
        logger.info(f"🔍 SYMPTOM_TRACKER: Updated session {session_id} with: {new_data}")
        
        # Check if we have enough data to complete the entry
        if self._is_complete(session_id):
            return self._complete_symptom_entry(session_id)
        else:
            # Ask next question (intelligent skipping)
            next_question = self._get_next_question(session_id)
            session["last_question"] = next_question
            
            return {
                "session_id": session_id,
                "message": "Got it.",
                "next_question": next_question,
                "progress": self._calculate_progress(session_id),
                "current_data": self._format_current_data(session["symptom_data"])
            }

    def _extract_initial_data(self, query: str) -> Dict[str, Any]:
        """Extract initial symptom data from user's query with enhanced extraction."""
        data = {}
        query_lower = query.lower()
        
        # Enhanced symptom keywords list including toothache and other common symptoms
        symptom_keywords = [
            "headache", "migraine", "fever", "cough", "nausea", "dizziness",
            "fatigue", "pain", "ache", "sore throat", "runny nose", "congestion",
            "stomach ache", "back pain", "chest pain", "joint pain", "toothache",
            "earache", "muscle ache", "heartburn", "constipation", "diarrhea",
            "vomiting", "bloating", "cramps", "weakness", "stiffness", "burning",
            "itching", "rash", "swelling", "bruising", "numbness", "tingling"
        ]
        
        for symptom in symptom_keywords:
            if symptom in query_lower:
                data["symptom_name"] = symptom
                break
        
        # Extract severity (numeric scale)
        import re
        severity_match = re.search(r"(\d+)\s*(?:out of|/)\s*(\d+)", query_lower)
        if severity_match:
            value = int(severity_match.group(1))
            max_value = int(severity_match.group(2))
            data["severity"] = min(10, max(1, int((value / max_value) * 10)))
        else:
            # Look for single numbers that might be severity
            single_num = re.search(r"\b([1-9]|10)\b", query_lower)
            if single_num and ("severity" in query_lower or "scale" in query_lower or "out of" in query_lower):
                data["severity"] = int(single_num.group(1))
        
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
            "head", "forehead", "temple", "neck", "throat", "chest", "back",
            "stomach", "abdomen", "arm", "leg", "knee", "shoulder", "wrist",
            "ankle", "foot", "hand", "eye", "ear", "nose", "tooth", "teeth",
            "jaw", "mouth"
        ]
        
        for part in body_parts:
            if part in query_lower:
                data["location"] = part
                break
        
        return data

    def _extract_data_from_response(self, response: str, existing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract data from user's response to a specific question with enhanced multi-field extraction."""
        new_data = {}
        response_lower = response.lower()
        
        # Enhanced extraction - try to get multiple fields from a single response
        
        # If we're missing symptom_name, try to extract it
        if "symptom_name" not in existing_data:
            symptom_keywords = [
                "headache", "migraine", "fever", "cough", "nausea", "dizziness",
                "fatigue", "pain", "ache", "sore throat", "runny nose", "congestion",
                "toothache", "earache", "stomach ache", "back pain", "chest pain"
            ]
            for symptom in symptom_keywords:
                if symptom in response_lower:
                    new_data["symptom_name"] = symptom
                    break
        
        # If we're missing severity, try to extract it
        if "severity" not in existing_data:
            import re
            # Look for numeric ratings
            severity_match = re.search(r"(\d+)\s*(?:out of|/)\s*(\d+)", response_lower)
            if severity_match:
                value = int(severity_match.group(1))
                max_value = int(severity_match.group(2))
                new_data["severity"] = min(10, max(1, int((value / max_value) * 10)))
            else:
                # Look for single numbers
                single_num = re.search(r"\b([1-9]|10)\b", response_lower)
                if single_num:
                    new_data["severity"] = int(single_num.group(1))
        
        # If we're missing duration, try to extract it
        if "duration_hours" not in existing_data:
            for pattern, converter in self.duration_patterns.items():
                match = re.search(pattern, response_lower)
                if match:
                    try:
                        if match.groups():
                            new_data["duration_hours"] = converter(match.group(1))
                        else:
                            new_data["duration_hours"] = converter(None)
                        break
                    except:
                        continue
        
        # If we're missing location, try to extract it
        if "location" not in existing_data:
            body_parts = [
                "head", "forehead", "temple", "neck", "throat", "chest", "back",
                "stomach", "abdomen", "arm", "leg", "knee", "shoulder", "wrist",
                "tooth", "teeth", "jaw", "mouth", "ear", "eye"
            ]
            for part in body_parts:
                if part in response_lower:
                    new_data["location"] = part
                    break
        
        return new_data

    def _get_next_question(self, session_id: str) -> Optional[str]:
        """Get the next question to ask the user with intelligent skipping."""
        session = self.active_sessions[session_id]
        symptom_data = session["symptom_data"]
        questions_asked = session["questions_asked"]
        
        # Check required fields first - skip if already present
        for field in self.required_fields:
            if field not in symptom_data and field not in questions_asked:
                session["questions_asked"].append(field)
                question = self.follow_up_questions[field]
                if "{symptom_name}" in question and "symptom_name" in symptom_data:
                    question = question.format(symptom_name=symptom_data["symptom_name"])
                return question
        
        # Check optional fields (but only ask 1-2 more questions) - skip if already present
        optional_asked = [q for q in questions_asked if q in self.optional_fields]
        if len(optional_asked) < 2:
            for field in self.optional_fields:
                if field not in symptom_data and field not in questions_asked:
                    session["questions_asked"].append(field)
                    question = self.follow_up_questions[field]
                    if "{symptom_name}" in question and "symptom_name" in symptom_data:
                        question = question.format(symptom_name=symptom_data["symptom_name"])
                    return question
        
        return None

    def _is_complete(self, session_id: str) -> bool:
        """Check if we have enough data to complete the symptom entry."""
        session = self.active_sessions[session_id]
        symptom_data = session["symptom_data"]
        
        # Must have all required fields
        for field in self.required_fields:
            if field not in symptom_data:
                return False
        
        # Or if we've asked enough questions (don't go on forever)
        if len(session["questions_asked"]) >= 4:
            return True
        
        return True

    def _complete_symptom_entry(self, session_id: str) -> Dict[str, Any]:
        """Complete the symptom entry and save to database."""
        session = self.active_sessions[session_id]
        symptom_data = session["symptom_data"]
        user_id = session["user_id"]
        
        # Create a clean description
        description = self._create_clean_description(symptom_data)
        
        # Prepare data for database
        db_data = {
            "symptom_name": symptom_data.get("symptom_name", "unknown"),
            "severity": symptom_data.get("severity"),
            "duration_hours": symptom_data.get("duration_hours"),
            "location": symptom_data.get("location"),
            "description": description,
            "triggers": symptom_data.get("triggers", []),
            "metadata": {
                "tracking_session": session_id,
                "questions_asked": len(session["questions_asked"]),
                "completion_method": "conversational_tracking"
            }
        }
        
        # Mark session as complete
        session["is_complete"] = True
        session["final_data"] = db_data
        
        logger.info(f"✅ SYMPTOM_TRACKER: Completed session {session_id} with data: {db_data}")
        
        return {
            "session_id": session_id,
            "status": "complete",
            "message": f"✅ I've successfully logged your {symptom_data.get('symptom_name', 'symptom')}.",
            "summary": self._format_summary(symptom_data),
            "db_data": db_data,
            "confirmation_question": "Does this look correct? You can say 'yes' to save it or tell me what to change."
        }

    def _create_clean_description(self, symptom_data: Dict[str, Any]) -> str:
        """Create a clean, human-readable description."""
        parts = []
        
        symptom_name = symptom_data.get("symptom_name", "symptom")
        
        if symptom_data.get("severity"):
            parts.append(f"severity {symptom_data['severity']}/10")
        
        if symptom_data.get("duration_hours"):
            duration = self._format_duration(symptom_data["duration_hours"])
            parts.append(f"duration {duration}")
        
        if symptom_data.get("location"):
            parts.append(f"location: {symptom_data['location']}")
        
        if symptom_data.get("quality"):
            parts.append(f"quality: {symptom_data['quality']}")
        
        if parts:
            return f"{symptom_name.title()} - {', '.join(parts)}"
        else:
            return symptom_name.title()

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
        else:
            days = hours // 24
            return f"{days} day{'s' if days > 1 else ''}"

    def _format_summary(self, symptom_data: Dict[str, Any]) -> str:
        """Format a summary of the collected data."""
        summary_parts = []
        
        if symptom_data.get("symptom_name"):
            summary_parts.append(f"**Symptom**: {symptom_data['symptom_name'].title()}")
        
        if symptom_data.get("severity"):
            summary_parts.append(f"**Severity**: {symptom_data['severity']}/10")
        
        if symptom_data.get("duration_hours"):
            duration = self._format_duration(symptom_data["duration_hours"])
            summary_parts.append(f"**Duration**: {duration}")
        
        if symptom_data.get("location"):
            summary_parts.append(f"**Location**: {symptom_data['location']}")
        
        return "\n".join(summary_parts)

    def _calculate_progress(self, session_id: str) -> Dict[str, Any]:
        """Calculate completion progress."""
        session = self.active_sessions[session_id]
        symptom_data = session["symptom_data"]
        
        total_fields = len(self.required_fields) + 2  # 2 most important optional fields
        filled_fields = len([f for f in self.required_fields + ["duration_hours", "location"] if f in symptom_data])
        
        return {
            "filled_fields": filled_fields,
            "total_fields": total_fields,
            "percentage": int((filled_fields / total_fields) * 100)
        }

    def _generate_acknowledgment(self, initial_data: Dict[str, Any]) -> str:
        """Generate an acknowledgment message based on initial data."""
        if "symptom_name" in initial_data:
            return f"I understand you're experiencing {initial_data['symptom_name']}."
        else:
            return "I'd like to help you track your symptom."

    def _format_current_data(self, symptom_data: Dict[str, Any]) -> str:
        """Format current data for user review."""
        if not symptom_data:
            return "No data collected yet."
        
        parts = []
        if symptom_data.get("symptom_name"):
            parts.append(f"Symptom: {symptom_data['symptom_name']}")
        if symptom_data.get("severity"):
            parts.append(f"Severity: {symptom_data['severity']}/10")
        if symptom_data.get("duration_hours"):
            duration = self._format_duration(symptom_data["duration_hours"])
            parts.append(f"Duration: {duration}")
        if symptom_data.get("location"):
            parts.append(f"Location: {symptom_data['location']}")
        
        return " | ".join(parts) if parts else "Partial data collected."

    async def save_to_database(self, session_id: str, jwt_token: str) -> Dict[str, Any]:
        """Save the completed symptom entry to the database."""
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
            result = client.table("user_symptoms").insert({
                "user_id": user_id,
                "symptom_name": db_data["symptom_name"],
                "severity": db_data["severity"],
                "duration_hours": db_data["duration_hours"],
                "location": db_data["location"],
                "description": db_data["description"],
                "triggers": db_data["triggers"],
                "metadata": db_data["metadata"]
            }).execute()
            
            if hasattr(result, 'error') and result.error:
                logger.error(f"❌ SYMPTOM_TRACKER: Database error: {result.error}")
                return {"error": f"Database error: {result.error}"}
            
            symptom_id = result.data[0]["id"] if result.data else None
            
            # Clean up session
            del self.active_sessions[session_id]
            
            logger.info(f"✅ SYMPTOM_TRACKER: Saved symptom {symptom_id} and cleaned up session {session_id}")
            
            return {
                "success": True,
                "symptom_id": symptom_id,
                "message": "Symptom successfully saved to your health log!",
                "data": result.data[0] if result.data else None
            }
            
        except Exception as e:
            logger.error(f"❌ SYMPTOM_TRACKER: Error saving to database: {str(e)}")
            return {"error": f"Failed to save symptom: {str(e)}"}

    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a tracking session."""
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        return {
            "session_id": session_id,
            "is_complete": session.get("is_complete", False),
            "progress": self._calculate_progress(session_id),
            "current_data": self._format_current_data(session["symptom_data"]),
            "questions_asked": len(session["questions_asked"]),
            "last_question": session.get("last_question")
        }

    def cancel_session(self, session_id: str) -> Dict[str, Any]:
        """Cancel a tracking session."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info(f"✅ SYMPTOM_TRACKER: Cancelled session {session_id}")
            return {"success": True}
        return {"success": False, "error": "Session not found"}

    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a formatted summary of the current session."""
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        symptom_data = session["symptom_data"]
        
        summary = self._format_summary(symptom_data)
        progress = self._calculate_progress(session_id)
        next_question = self._get_next_question(session_id)
        
        return {
            "summary": summary if summary else "No symptom data collected yet.",
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
        session["symptom_data"][field_name] = new_value
        session["last_updated"] = datetime.now().isoformat()
        
        logger.info(f"✅ SYMPTOM_TRACKER: Updated {field_name} to {new_value} in session {session_id}")
        
        return {
            "success": True,
            "message": f"Updated {field_name} to {new_value}",
            "current_data": self._format_current_data(session["symptom_data"])
        }

# Global instance
symptom_tracker = SymptomTracker()