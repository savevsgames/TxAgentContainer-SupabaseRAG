"""
Agent Actions for TxAgent Agent Awareness.

This module handles agent actions like saving and retrieving symptoms,
providing the core functionality for intelligent symptom tracking.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

from core.auth_service import auth_service
from core.logging import request_logger

logger = logging.getLogger("agent_actions")

class AgentActions:
    """Handles agent actions like saving and retrieving symptoms."""
    
    def __init__(self):
        pass

    async def save_symptom(self, request: Request) -> JSONResponse:
        """Save a symptom to the user's profile."""
        try:
            logger.info("🚀 SAVE_SYMPTOM: Starting symptom save request")
            
            # Get authorization header
            authorization = request.headers.get("Authorization")
            if not authorization:
                logger.error("❌ SAVE_SYMPTOM: Authorization header missing")
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Authorization header missing"}
                )
            
            # Extract and validate token
            token = auth_service.extract_token_from_header(authorization)
            user_id, user_payload = auth_service.validate_token_and_get_user(token)
            
            logger.info(f"🔍 SAVE_SYMPTOM: Request from user {user_id}")
            
            # Get authenticated client
            client = auth_service.get_authenticated_client(token)
            
            # Parse request body
            data = await request.json()
            symptom_data = data.get("symptom_data", {})
            
            logger.info(f"🔍 SAVE_SYMPTOM: Symptom data: {symptom_data}")
            
            # Validate symptom data
            if not symptom_data.get("symptom_name"):
                logger.error("❌ SAVE_SYMPTOM: symptom_name is required")
                return JSONResponse(
                    status_code=400,
                    content={"detail": "symptom_name is required"}
                )
            
            # Prepare data for insertion
            insert_data = {
                "user_id": user_id,
                "symptom_name": symptom_data.get("symptom_name"),
                "description": symptom_data.get("description"),
            }
            
            # Add optional fields if present
            if symptom_data.get("severity"):
                insert_data["severity"] = symptom_data.get("severity")
            if symptom_data.get("duration_hours"):
                insert_data["duration_hours"] = symptom_data.get("duration_hours")
            if symptom_data.get("location"):
                insert_data["location"] = symptom_data.get("location")
            if symptom_data.get("triggers"):
                insert_data["triggers"] = symptom_data.get("triggers")
            
            # Add any additional metadata
            metadata = {}
            for key, value in symptom_data.items():
                if key not in ["symptom_name", "severity", "duration_hours", "location", "triggers", "description"]:
                    metadata[key] = value
            
            if metadata:
                insert_data["metadata"] = metadata
            
            logger.info(f"🔍 SAVE_SYMPTOM: Prepared insert data: {insert_data}")
            
            # Insert into database
            result = client.table("user_symptoms").insert(insert_data).execute()
            
            if hasattr(result, 'error') and result.error:
                logger.error(f"❌ SAVE_SYMPTOM: Database error: {result.error}")
                raise Exception(f"Database error: {result.error}")
            
            symptom_id = result.data[0]["id"] if result.data else None
            
            logger.info(f"✅ SAVE_SYMPTOM: Successfully saved symptom {symptom_id}")
            
            # Log the action
            auth_service.log_auth_event("symptom_saved", user_context=user_payload, success=True, details={
                "symptom_id": symptom_id,
                "symptom_name": symptom_data.get("symptom_name"),
                "severity": symptom_data.get("severity"),
                "location": symptom_data.get("location")
            })
            
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": "Symptom logged successfully",
                    "symptom_id": symptom_id,
                    "symptom_name": symptom_data.get("symptom_name"),
                    "data": result.data[0] if result.data else None
                }
            )
        
        except HTTPException as e:
            logger.error(f"❌ SAVE_SYMPTOM: HTTP error: {e.detail}")
            raise
        except Exception as e:
            logger.error(f"❌ SAVE_SYMPTOM: Unexpected error: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"detail": f"Failed to save symptom: {str(e)}"}
            )

    async def get_symptoms(self, request: Request) -> JSONResponse:
        """Get user's symptom history."""
        try:
            logger.info("🚀 GET_SYMPTOMS: Starting symptom retrieval request")
            
            # Get authorization header
            authorization = request.headers.get("Authorization")
            if not authorization:
                logger.error("❌ GET_SYMPTOMS: Authorization header missing")
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Authorization header missing"}
                )
            
            # Extract and validate token
            token = auth_service.extract_token_from_header(authorization)
            user_id, user_payload = auth_service.validate_token_and_get_user(token)
            
            logger.info(f"🔍 GET_SYMPTOMS: Request from user {user_id}")
            
            # Get authenticated client
            client = auth_service.get_authenticated_client(token)
            
            # Get query parameters
            limit = int(request.query_params.get("limit", "10"))
            symptom_name = request.query_params.get("symptom_name")
            days_back = request.query_params.get("days_back")
            
            logger.info(f"🔍 GET_SYMPTOMS: Filters - limit: {limit}, symptom_name: {symptom_name}, days_back: {days_back}")
            
            # Build query
            query = client.table("user_symptoms").select("*")
            
            if symptom_name:
                query = query.eq("symptom_name", symptom_name)
            
            if days_back:
                # Filter by date range
                query = query.gte("created_at", f"now() - interval '{days_back} days'")
            
            # Execute query with ordering and limit
            result = query.order("created_at", {"ascending": False}).limit(limit).execute()
            
            if hasattr(result, 'error') and result.error:
                logger.error(f"❌ GET_SYMPTOMS: Database error: {result.error}")
                raise Exception(f"Database error: {result.error}")
            
            symptoms = result.data or []
            
            logger.info(f"✅ GET_SYMPTOMS: Retrieved {len(symptoms)} symptoms")
            
            # Format symptoms for response
            formatted_symptoms = []
            for symptom in symptoms:
                formatted_symptom = {
                    "id": symptom.get("id"),
                    "symptom_name": symptom.get("symptom_name"),
                    "severity": symptom.get("severity"),
                    "description": symptom.get("description"),
                    "location": symptom.get("location"),
                    "duration_hours": symptom.get("duration_hours"),
                    "triggers": symptom.get("triggers"),
                    "created_at": symptom.get("created_at"),
                    "metadata": symptom.get("metadata", {})
                }
                formatted_symptoms.append(formatted_symptom)
            
            # Log the action
            auth_service.log_auth_event("symptoms_retrieved", user_context=user_payload, success=True, details={
                "count": len(symptoms),
                "symptom_name": symptom_name,
                "days_back": days_back
            })
            
            return JSONResponse(
                status_code=200,
                content={
                    "symptoms": formatted_symptoms,
                    "count": len(symptoms),
                    "filters": {
                        "symptom_name": symptom_name,
                        "days_back": days_back,
                        "limit": limit
                    }
                }
            )
        
        except HTTPException as e:
            logger.error(f"❌ GET_SYMPTOMS: HTTP error: {e.detail}")
            raise
        except Exception as e:
            logger.error(f"❌ GET_SYMPTOMS: Unexpected error: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"detail": f"Failed to retrieve symptoms: {str(e)}"}
            )

    async def get_symptom_summary(self, request: Request) -> JSONResponse:
        """Get a summary of user's symptom patterns."""
        try:
            logger.info("🚀 GET_SYMPTOM_SUMMARY: Starting symptom summary request")
            
            # Get authorization header
            authorization = request.headers.get("Authorization")
            if not authorization:
                logger.error("❌ GET_SYMPTOM_SUMMARY: Authorization header missing")
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Authorization header missing"}
                )
            
            # Extract and validate token
            token = auth_service.extract_token_from_header(authorization)
            user_id, user_payload = auth_service.validate_token_and_get_user(token)
            
            logger.info(f"🔍 GET_SYMPTOM_SUMMARY: Request from user {user_id}")
            
            # Get authenticated client
            client = auth_service.get_authenticated_client(token)
            
            # Get query parameters
            days_back = int(request.query_params.get("days_back", "30"))
            
            # Build query for recent symptoms
            query = client.table("user_symptoms").select("*")
            query = query.gte("created_at", f"now() - interval '{days_back} days'")
            result = query.order("created_at", {"ascending": False}).execute()
            
            if hasattr(result, 'error') and result.error:
                logger.error(f"❌ GET_SYMPTOM_SUMMARY: Database error: {result.error}")
                raise Exception(f"Database error: {result.error}")
            
            symptoms = result.data or []
            
            # Analyze symptoms
            summary = self._analyze_symptoms(symptoms, days_back)
            
            logger.info(f"✅ GET_SYMPTOM_SUMMARY: Generated summary for {len(symptoms)} symptoms")
            
            # Log the action
            auth_service.log_auth_event("symptom_summary_retrieved", user_context=user_payload, success=True, details={
                "total_symptoms": len(symptoms),
                "days_back": days_back,
                "unique_symptoms": len(summary.get("symptom_counts", {}))
            })
            
            return JSONResponse(
                status_code=200,
                content=summary
            )
        
        except HTTPException as e:
            logger.error(f"❌ GET_SYMPTOM_SUMMARY: HTTP error: {e.detail}")
            raise
        except Exception as e:
            logger.error(f"❌ GET_SYMPTOM_SUMMARY: Unexpected error: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"detail": f"Failed to generate symptom summary: {str(e)}"}
            )

    def _analyze_symptoms(self, symptoms: List[Dict[str, Any]], days_back: int) -> Dict[str, Any]:
        """Analyze symptoms and generate summary statistics."""
        if not symptoms:
            return {
                "total_symptoms": 0,
                "days_analyzed": days_back,
                "symptom_counts": {},
                "severity_average": None,
                "most_common_symptom": None,
                "recent_patterns": []
            }
        
        # Count symptoms by name
        symptom_counts = {}
        severity_scores = []
        locations = {}
        
        for symptom in symptoms:
            name = symptom.get("symptom_name", "unknown")
            symptom_counts[name] = symptom_counts.get(name, 0) + 1
            
            if symptom.get("severity"):
                severity_scores.append(symptom["severity"])
            
            location = symptom.get("location")
            if location:
                locations[location] = locations.get(location, 0) + 1
        
        # Calculate statistics
        most_common_symptom = max(symptom_counts.items(), key=lambda x: x[1]) if symptom_counts else None
        severity_average = sum(severity_scores) / len(severity_scores) if severity_scores else None
        most_common_location = max(locations.items(), key=lambda x: x[1]) if locations else None
        
        # Generate patterns
        patterns = []
        if most_common_symptom:
            patterns.append(f"Most frequent: {most_common_symptom[0]} ({most_common_symptom[1]} times)")
        
        if severity_average:
            patterns.append(f"Average severity: {severity_average:.1f}/10")
        
        if most_common_location:
            patterns.append(f"Most affected area: {most_common_location[0]}")
        
        return {
            "total_symptoms": len(symptoms),
            "days_analyzed": days_back,
            "symptom_counts": symptom_counts,
            "severity_average": round(severity_average, 1) if severity_average else None,
            "most_common_symptom": most_common_symptom[0] if most_common_symptom else None,
            "most_common_location": most_common_location[0] if most_common_location else None,
            "recent_patterns": patterns,
            "unique_symptoms": len(symptom_counts)
        }

# Global instance
agent_actions = AgentActions()