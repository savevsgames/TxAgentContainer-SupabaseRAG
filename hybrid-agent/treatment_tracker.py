"""
Treatment Tracking Loop Manager for TxAgent.

This module handles the conversational loop for treatment tracking,
managing incremental data collection and temporary storage until
a complete treatment entry can be saved.
"""

import logging
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import re

from core.auth_service import auth_service

logger = logging.getLogger("treatment_tracker")

class TreatmentTracker:
    """Manages conversational treatment tracking with incremental data collection."""
    
    def __init__(self):
        # In-memory storage for incomplete treatment entries
        self.active_sessions = {}
        
        # Required fields for a complete treatment entry
        self.required_fields = ["name", "treatment_type"]
        
        # Optional but helpful fields
        self.optional_fields = ["dosage", "duration", "doctor_recommended", "description"]
        
        # Treatment types
        self.treatment_types = [
            "medication", "therapy", "exercise", "diet", "supplement", 
            "procedure", "surgery", "home_remedy", "lifestyle_change"
        ]
        
        # Follow-up questions for missing fields
        self.follow_up_questions = {
            "name": "What is the name of the treatment or medication?",
            "treatment_type": "What type of treatment is this? (medication, therapy, exercise, etc.)",
            "dosage": "What is the dosage or frequency for {name}?",
            "duration": "How long will you be taking/doing {name}?",
            "doctor_recommended": "Was this {name} recommended by a doctor?",
            "description": "Can you tell me more details about {name}?"
        }

    def start_treatment_tracking(self, user_id: str, initial_query: str) -> Dict[str, Any]:
        """Start a new treatment tracking session."""
        session_id = f"treatment_{user_id}_{datetime.now().timestamp()}"
        
        # Initialize session with extracted data from initial query
        initial_data = self._extract_initial_data(initial_query)
        
        self.active_sessions[session_id] = {
            "user_id": user_id,
            "treatment_data": initial_data,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "questions_asked": [],
            "is_complete": False
        }
        
        logger.info(f"🔍 TREATMENT_TRACKER: Started session {session_id} with initial data: {initial_data}")
        
        # Determine next question
        next_question = self._get_next_question(session_id)
        
        return {
            "session_id": session_id,
            "message": self._generate_acknowledgment(initial_data),
            "next_question": next_question,
            "progress": self._calculate_progress(session_id)
        }

    def update_treatment_data(self, session_id: str, user_response: str) -> Dict[str, Any]:
        """Update treatment data based on user response."""
        if session_id not in self.active_sessions:
            return {"error": "Session not found"}
        
        session = self.active_sessions[session_id]
        
        # Extract new data from user response
        new_data = self._extract_data_from_response(user_response, session["treatment_data"])
        
        # Update session data
        session["treatment_data"].update(new_data)
        session["last_updated"] = datetime.now().isoformat()
        
        logger.info(f"🔍 TREATMENT_TRACKER: Updated session {session_id} with: {new_data}")
        
        # Check if we have enough data to complete the entry
        if self._is_complete(session_id):
            return self._complete_treatment_entry(session_id)
        else:
            # Ask next question
            next_question = self._get_next_question(session_id)
            return {
                "session_id": session_id,
                "message": "Got it.",
                "next_question": next_question,
                "progress": self._calculate_progress(session_id),
                "current_data": self._format_current_data(session["treatment_data"])
            }

    def _extract_initial_data(self, query: str) -> Dict[str, Any]:
        """Extract initial treatment data from user's query."""
        data = {}
        query_lower = query.lower()
        
        # Extract treatment type
        for treatment_type in self.treatment_types:
            if treatment_type in query_lower:
                data["treatment_type"] = treatment_type
                break
        
        # Common medication names
        medication_keywords = [
            "ibuprofen", "acetaminophen", "aspirin", "tylenol", "advil", "motrin",
            "lisinopril", "metformin", "atorvastatin", "amlodipine", "omeprazole",
            "levothyroxine", "metoprolol", "losartan", "hydrochlorothiazide"
        ]
        
        for med in medication_keywords:
            if med in query_lower:
                data["name"] = med
                data["treatment_type"] = "medication"
                break
        
        # Extract dosage patterns
        dosage_patterns = [
            r"(\d+)\s*mg",
            r"(\d+)\s*times?\s+(?:a\s+)?day",
            r"(\d+)\s*(?:tablet|pill|capsule)s?",
            r"once\s+(?:a\s+)?day",
            r"twice\s+(?:a\s+)?day",
            r"three\s+times\s+(?:a\s+)?day"
        ]
        
        for pattern in dosage_patterns:
            match = re.search(pattern, query_lower)
            if match:
                data["dosage"] = match.group(0)
                break
        
        # Check for doctor recommendation indicators
        doctor_indicators = ["doctor", "prescribed", "physician", "recommended by", "dr."]
        if any(indicator in query_lower for indicator in doctor_indicators):
            data["doctor_recommended"] = True
        
        return data

    def _extract_data_from_response(self, response: str, existing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract data from user's response to a specific question."""
        new_data = {}
        response_lower = response.lower()
        
        # If we're missing name, try to extract it
        if "name" not in existing_data:
            # Look for medication names or treatment names
            words = response.split()
            for word in words:
                if len(word) > 3 and word.isalpha():
                    new_data["name"] = word.lower()
                    break
        
        # If we're missing treatment_type, try to extract it
        if "treatment_type" not in existing_data:
            for treatment_type in self.treatment_types:
                if treatment_type in response_lower:
                    new_data["treatment_type"] = treatment_type
                    break
        
        # Extract dosage if missing
        if "dosage" not in existing_data:
            dosage_patterns = [
                r"(\d+)\s*mg",
                r"(\d+)\s*times?\s+(?:a\s+)?day",
                r"(\d+)\s*(?:tablet|pill|capsule)s?",
                r"once\s+(?:a\s+)?day",
                r"twice\s+(?:a\s+)?day"
            ]
            
            for pattern in dosage_patterns:
                match = re.search(pattern, response_lower)
                if match:
                    new_data["dosage"] = match.group(0)
                    break
        
        # Extract duration if missing
        if "duration" not in existing_data:
            duration_patterns = [
                r"(\d+)\s*(?:day|week|month)s?",
                r"for\s+(\d+)\s*(?:day|week|month)s?",
                r"ongoing",
                r"indefinitely",
                r"as\s+needed"
            ]
            
            for pattern in duration_patterns:
                match = re.search(pattern, response_lower)
                if match:
                    new_data["duration"] = match.group(0)
                    break
        
        # Extract doctor recommendation
        if "doctor_recommended" not in existing_data:
            yes_indicators = ["yes", "doctor", "prescribed", "physician", "recommended"]
            no_indicators = ["no", "self", "over the counter", "otc"]
            
            if any(indicator in response_lower for indicator in yes_indicators):
                new_data["doctor_recommended"] = True
            elif any(indicator in response_lower for indicator in no_indicators):
                new_data["doctor_recommended"] = False
        
        return new_data

    def _get_next_question(self, session_id: str) -> Optional[str]:
        """Get the next question to ask the user."""
        session = self.active_sessions[session_id]
        treatment_data = session["treatment_data"]
        questions_asked = session["questions_asked"]
        
        # Check required fields first
        for field in self.required_fields:
            if field not in treatment_data and field not in questions_asked:
                session["questions_asked"].append(field)
                question = self.follow_up_questions[field]
                if "{name}" in question and "name" in treatment_data:
                    question = question.format(name=treatment_data["name"])
                return question
        
        # Check optional fields (but only ask 1-2 more questions)
        optional_asked = [q for q in questions_asked if q in self.optional_fields]
        if len(optional_asked) < 2:
            for field in self.optional_fields:
                if field not in treatment_data and field not in questions_asked:
                    session["questions_asked"].append(field)
                    question = self.follow_up_questions[field]
                    if "{name}" in question and "name" in treatment_data:
                        question = question.format(name=treatment_data["name"])
                    return question
        
        return None

    def _is_complete(self, session_id: str) -> bool:
        """Check if we have enough data to complete the treatment entry."""
        session = self.active_sessions[session_id]
        treatment_data = session["treatment_data"]
        
        # Must have all required fields
        for field in self.required_fields:
            if field not in treatment_data:
                return False
        
        # Or if we've asked enough questions
        if len(session["questions_asked"]) >= 4:
            return True
        
        return True

    def _complete_treatment_entry(self, session_id: str) -> Dict[str, Any]:
        """Complete the treatment entry and prepare for database save."""
        session = self.active_sessions[session_id]
        treatment_data = session["treatment_data"]
        user_id = session["user_id"]
        
        # Create a clean description
        description = self._create_clean_description(treatment_data)
        
        # Prepare data for database
        db_data = {
            "name": treatment_data.get("name", "unknown"),
            "treatment_type": treatment_data.get("treatment_type", "medication"),
            "dosage": treatment_data.get("dosage"),
            "duration": treatment_data.get("duration"),
            "description": description,
            "doctor_recommended": treatment_data.get("doctor_recommended", False),
            "completed": False,  # New treatments are not completed by default
            "is_current": True,  # New treatments are current by default
            "notes": f"Added via conversational tracking on {datetime.now().strftime('%Y-%m-%d')}"
        }
        
        # Mark session as complete
        session["is_complete"] = True
        session["final_data"] = db_data
        
        logger.info(f"✅ TREATMENT_TRACKER: Completed session {session_id} with data: {db_data}")
        
        return {
            "session_id": session_id,
            "status": "complete",
            "message": f"✅ I've successfully logged your {treatment_data.get('name', 'treatment')}.",
            "summary": self._format_summary(treatment_data),
            "db_data": db_data,
            "confirmation_question": "Does this look correct? You can say 'yes' to save it or tell me what to change."
        }

    def _create_clean_description(self, treatment_data: Dict[str, Any]) -> str:
        """Create a clean, human-readable description."""
        parts = []
        
        name = treatment_data.get("name", "treatment")
        treatment_type = treatment_data.get("treatment_type", "")
        
        if treatment_type:
            parts.append(f"Type: {treatment_type}")
        
        if treatment_data.get("dosage"):
            parts.append(f"Dosage: {treatment_data['dosage']}")
        
        if treatment_data.get("duration"):
            parts.append(f"Duration: {treatment_data['duration']}")
        
        if treatment_data.get("doctor_recommended"):
            parts.append("Doctor recommended")
        
        if parts:
            return f"{name.title()} - {', '.join(parts)}"
        else:
            return name.title()

    def _format_summary(self, treatment_data: Dict[str, Any]) -> str:
        """Format a summary of the collected data."""
        summary_parts = []
        
        if treatment_data.get("name"):
            summary_parts.append(f"**Treatment**: {treatment_data['name'].title()}")
        
        if treatment_data.get("treatment_type"):
            summary_parts.append(f"**Type**: {treatment_data['treatment_type'].title()}")
        
        if treatment_data.get("dosage"):
            summary_parts.append(f"**Dosage**: {treatment_data['dosage']}")
        
        if treatment_data.get("duration"):
            summary_parts.append(f"**Duration**: {treatment_data['duration']}")
        
        if treatment_data.get("doctor_recommended"):
            summary_parts.append(f"**Doctor Recommended**: {'Yes' if treatment_data['doctor_recommended'] else 'No'}")
        
        return "\n".join(summary_parts)

    def _calculate_progress(self, session_id: str) -> Dict[str, Any]:
        """Calculate completion progress."""
        session = self.active_sessions[session_id]
        treatment_data = session["treatment_data"]
        
        total_fields = len(self.required_fields) + 2  # 2 most important optional fields
        filled_fields = len([f for f in self.required_fields + ["dosage", "duration"] if f in treatment_data])
        
        return {
            "filled_fields": filled_fields,
            "total_fields": total_fields,
            "percentage": int((filled_fields / total_fields) * 100)
        }

    def _generate_acknowledgment(self, initial_data: Dict[str, Any]) -> str:
        """Generate an acknowledgment message based on initial data."""
        if "name" in initial_data:
            return f"I understand you want to track {initial_data['name']}."
        else:
            return "I'd like to help you track your treatment or medication."

    def _format_current_data(self, treatment_data: Dict[str, Any]) -> str:
        """Format current data for user review."""
        if not treatment_data:
            return "No data collected yet."
        
        parts = []
        if treatment_data.get("name"):
            parts.append(f"Treatment: {treatment_data['name']}")
        if treatment_data.get("treatment_type"):
            parts.append(f"Type: {treatment_data['treatment_type']}")
        if treatment_data.get("dosage"):
            parts.append(f"Dosage: {treatment_data['dosage']}")
        if treatment_data.get("duration"):
            parts.append(f"Duration: {treatment_data['duration']}")
        
        return " | ".join(parts) if parts else "Partial data collected."

    async def save_to_database(self, session_id: str, jwt_token: str) -> Dict[str, Any]:
        """Save the completed treatment entry to the database."""
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
            result = client.table("treatments").insert({
                "user_id": user_id,
                "name": db_data["name"],
                "treatment_type": db_data["treatment_type"],
                "dosage": db_data["dosage"],
                "duration": db_data["duration"],
                "description": db_data["description"],
                "doctor_recommended": db_data["doctor_recommended"],
                "completed": db_data["completed"],
                "notes": db_data["notes"]
            }).execute()
            
            if hasattr(result, 'error') and result.error:
                logger.error(f"❌ TREATMENT_TRACKER: Database error: {result.error}")
                return {"error": f"Database error: {result.error}"}
            
            treatment_id = result.data[0]["id"] if result.data else None
            
            # Clean up session
            del self.active_sessions[session_id]
            
            logger.info(f"✅ TREATMENT_TRACKER: Saved treatment {treatment_id} and cleaned up session {session_id}")
            
            return {
                "success": True,
                "treatment_id": treatment_id,
                "message": "Treatment successfully saved to your health log!",
                "data": result.data[0] if result.data else None
            }
            
        except Exception as e:
            logger.error(f"❌ TREATMENT_TRACKER: Error saving to database: {str(e)}")
            return {"error": f"Failed to save treatment: {str(e)}"}

    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a tracking session."""
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        return {
            "session_id": session_id,
            "is_complete": session.get("is_complete", False),
            "progress": self._calculate_progress(session_id),
            "current_data": self._format_current_data(session["treatment_data"]),
            "questions_asked": len(session["questions_asked"])
        }

# Global instance
treatment_tracker = TreatmentTracker()