"""
Database Manager for TxAgent Agent Overhaul.

This module handles all database operations for health tracking data
with clean, focused methods for each data type.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from core.auth_service import auth_service

logger = logging.getLogger("database_manager")

class DatabaseManager:
    """Handles database operations for health tracking data."""
    
    def __init__(self):
        pass

    async def save_symptom(self, user_id: str, data: Dict[str, Any], jwt_token: str) -> Dict[str, Any]:
        """Save symptom data to database."""
        logger.info(f"💾 SAVE_SYMPTOM: Saving symptom for user {user_id}")
        
        try:
            # Get authenticated client
            client = auth_service.get_authenticated_client(jwt_token)
            
            # Insert symptom data
            result = client.table("user_symptoms").insert({
                "user_id": user_id,
                "symptom_name": data.get("symptom_name"),
                "severity": data.get("severity"),
                "duration_hours": data.get("duration_hours"),
                "location": data.get("location"),
                "description": data.get("description"),
                "triggers": data.get("triggers", []),
                "metadata": data.get("metadata", {})
            }).execute()
            
            if hasattr(result, 'error') and result.error:
                logger.error(f"❌ SAVE_SYMPTOM: Database error: {result.error}")
                return {"success": False, "error": f"Database error: {result.error}"}
            
            symptom_id = result.data[0]["id"] if result.data else None
            
            logger.info(f"✅ SAVE_SYMPTOM: Successfully saved symptom {symptom_id}")
            
            return {
                "success": True,
                "id": symptom_id,
                "message": "Symptom successfully saved to your health log!",
                "data": result.data[0] if result.data else None
            }
            
        except Exception as e:
            logger.error(f"❌ SAVE_SYMPTOM: Error saving symptom: {str(e)}")
            return {"success": False, "error": f"Failed to save symptom: {str(e)}"}

    async def save_treatment(self, user_id: str, data: Dict[str, Any], jwt_token: str) -> Dict[str, Any]:
        """Save treatment data to database."""
        logger.info(f"💾 SAVE_TREATMENT: Saving treatment for user {user_id}")
        
        try:
            # Get authenticated client
            client = auth_service.get_authenticated_client(jwt_token)
            
            # Insert treatment data
            result = client.table("treatments").insert({
                "user_id": user_id,
                "name": data.get("name"),
                "treatment_type": data.get("treatment_type"),
                "dosage": data.get("dosage"),
                "duration": data.get("duration"),
                "description": data.get("description"),
                "doctor_recommended": data.get("doctor_recommended", False),
                "completed": data.get("completed", False),
                "notes": data.get("notes")
            }).execute()
            
            if hasattr(result, 'error') and result.error:
                logger.error(f"❌ SAVE_TREATMENT: Database error: {result.error}")
                return {"success": False, "error": f"Database error: {result.error}"}
            
            treatment_id = result.data[0]["id"] if result.data else None
            
            logger.info(f"✅ SAVE_TREATMENT: Successfully saved treatment {treatment_id}")
            
            return {
                "success": True,
                "id": treatment_id,
                "message": "Treatment successfully saved to your health log!",
                "data": result.data[0] if result.data else None
            }
            
        except Exception as e:
            logger.error(f"❌ SAVE_TREATMENT: Error saving treatment: {str(e)}")
            return {"success": False, "error": f"Failed to save treatment: {str(e)}"}

    async def save_appointment(self, user_id: str, data: Dict[str, Any], jwt_token: str) -> Dict[str, Any]:
        """Save appointment data to database."""
        logger.info(f"💾 SAVE_APPOINTMENT: Saving appointment for user {user_id}")
        
        try:
            # Get authenticated client
            client = auth_service.get_authenticated_client(jwt_token)
            
            # Insert appointment data
            result = client.table("doctor_visits").insert({
                "user_id": user_id,
                "visit_ts": data.get("visit_ts"),
                "doctor_name": data.get("doctor_name"),
                "location": data.get("location"),
                "contact_phone": data.get("contact_phone"),
                "contact_email": data.get("contact_email"),
                "visit_prep": data.get("visit_prep"),
                "visit_summary": data.get("visit_summary"),
                "follow_up_required": data.get("follow_up_required", False)
            }).execute()
            
            if hasattr(result, 'error') and result.error:
                logger.error(f"❌ SAVE_APPOINTMENT: Database error: {result.error}")
                return {"success": False, "error": f"Database error: {result.error}"}
            
            appointment_id = result.data[0]["id"] if result.data else None
            
            logger.info(f"✅ SAVE_APPOINTMENT: Successfully saved appointment {appointment_id}")
            
            return {
                "success": True,
                "id": appointment_id,
                "message": "Appointment successfully saved to your health log!",
                "data": result.data[0] if result.data else None
            }
            
        except Exception as e:
            logger.error(f"❌ SAVE_APPOINTMENT: Error saving appointment: {str(e)}")
            return {"success": False, "error": f"Failed to save appointment: {str(e)}"}

    async def get_user_history(self, user_id: str, history_type: str, jwt_token: str, limit: int = 10) -> Dict[str, Any]:
        """Get user's health history."""
        logger.info(f"📚 GET_HISTORY: Getting {history_type} history for user {user_id}")
        
        try:
            # Get authenticated client
            client = auth_service.get_authenticated_client(jwt_token)
            
            results = {}
            
            if history_type in ["all", "symptoms"]:
                symptom_result = client.table("user_symptoms").select("*").order("created_at", {"ascending": False}).limit(limit).execute()
                results["symptoms"] = symptom_result.data if symptom_result.data else []
            
            if history_type in ["all", "treatments"]:
                treatment_result = client.table("treatments").select("*").order("created_at", {"ascending": False}).limit(limit).execute()
                results["treatments"] = treatment_result.data if treatment_result.data else []
            
            if history_type in ["all", "appointments"]:
                appointment_result = client.table("doctor_visits").select("*").order("created_at", {"ascending": False}).limit(limit).execute()
                results["appointments"] = appointment_result.data if appointment_result.data else []
            
            logger.info(f"✅ GET_HISTORY: Retrieved {history_type} history")
            
            return {
                "success": True,
                "data": results,
                "history_type": history_type
            }
            
        except Exception as e:
            logger.error(f"❌ GET_HISTORY: Error retrieving history: {str(e)}")
            return {"success": False, "error": f"Failed to retrieve history: {str(e)}"}

# Global database manager instance
database_manager = DatabaseManager()