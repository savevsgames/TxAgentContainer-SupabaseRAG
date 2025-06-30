import os
import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("llm")

class LLMHandler:
    """Handles LLM interactions for chat responses with user context support."""
    
    def __init__(self):
        """Initialize the LLM handler."""
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
        
    def _format_user_profile(self, user_profile: Dict[str, Any]) -> str:
        """
        Format user profile data into a clear, concise string for the LLM.
        
        Args:
            user_profile: Dictionary containing user's medical profile
            
        Returns:
            Formatted string representation of the user profile
        """
        if not user_profile:
            return ""
        
        profile_parts = []
        
        # Basic demographics
        if user_profile.get("age"):
            profile_parts.append(f"Age: {user_profile['age']}")
        if user_profile.get("gender"):
            profile_parts.append(f"Gender: {user_profile['gender']}")
        
        # Medical conditions
        conditions = user_profile.get("conditions", [])
        if conditions:
            if isinstance(conditions, list):
                profile_parts.append(f"Medical conditions: {', '.join(conditions)}")
            else:
                profile_parts.append(f"Medical conditions: {conditions}")
        
        # Current medications
        medications = user_profile.get("medications", [])
        if medications:
            if isinstance(medications, list):
                profile_parts.append(f"Current medications: {', '.join(medications)}")
            else:
                profile_parts.append(f"Current medications: {medications}")
        
        # Allergies
        allergies = user_profile.get("allergies", [])
        if allergies:
            if isinstance(allergies, list):
                profile_parts.append(f"Known allergies: {', '.join(allergies)}")
            else:
                profile_parts.append(f"Known allergies: {allergies}")
        
        # Recent symptoms
        symptoms = user_profile.get("symptoms", [])
        if symptoms:
            if isinstance(symptoms, list):
                profile_parts.append(f"Recent symptoms: {', '.join(symptoms)}")
            else:
                profile_parts.append(f"Recent symptoms: {symptoms}")
        
        # Family history
        family_history = user_profile.get("family_history", [])
        if family_history:
            if isinstance(family_history, list):
                profile_parts.append(f"Family history: {', '.join(family_history)}")
            else:
                profile_parts.append(f"Family history: {family_history}")
        
        # Additional relevant information
        for key, value in user_profile.items():
            if key not in ["age", "gender", "conditions", "medications", "allergies", "symptoms", "family_history"] and value:
                profile_parts.append(f"{key.replace('_', ' ').title()}: {value}")
        
        return "; ".join(profile_parts) if profile_parts else ""
        
    def _format_conversation_history(self, conversation_history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Format conversation history into OpenAI message format.
        
        Args:
            conversation_history: List of conversation messages
            
        Returns:
            List of formatted messages for OpenAI API
        """
        if not conversation_history:
            return []
        
        formatted_messages = []
        
        for message in conversation_history:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            # Ensure role is valid for OpenAI API
            if role not in ["user", "assistant", "system"]:
                role = "user"
            
            if content:
                formatted_messages.append({
                    "role": role,
                    "content": content
                })
        
        return formatted_messages
        
    def _build_prompt(
        self, 
        query: str, 
        context: List[Dict[str, Any]], 
        user_profile: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """
        Build comprehensive prompt from query, context, user profile, and conversation history.
        
        Args:
            query: User's current question
            context: Retrieved document context
            user_profile: User's medical profile
            conversation_history: Previous conversation messages
            
        Returns:
            List of messages formatted for OpenAI API
        """
        messages = []
        
        # Build system message with enhanced instructions for Symptom Savior
        system_content = """You are Symptom Savior, a professional and empathetic medical AI assistant. Your primary role is to provide helpful, accurate medical information based on the provided context and user profile.

Key Guidelines:
- Be concise and human-like in your responses
- Avoid lengthy explanations unless specifically requested
- Never mention "medical documents" or "sources" directly
- Do not use bullet points unless the user specifically asks for a list
- Provide natural, conversational responses
- Focus on being helpful without being verbose
- Act like a knowledgeable healthcare professional having a conversation

Response Style:
- Keep responses under 150 words unless more detail is specifically requested
- Use a warm, professional tone similar to a caring nurse or doctor
- Avoid medical jargon when simpler terms will do
- Be direct and clear in your communication"""
        
        # Add user profile to system message if available
        if user_profile:
            profile_str = self._format_user_profile(user_profile)
            if profile_str:
                system_content += f"\n\nUser Profile: {profile_str}"
                system_content += "\n\nPlease consider this medical profile when providing responses and tailor your advice accordingly."
        
        # Add document context
        if context:
            context_text = "\n\n".join([
                f"Relevant Information {i+1}:\n{doc['content']}"
                for i, doc in enumerate(context)
            ])
            system_content += f"\n\nRelevant Medical Information:\n{context_text}"
        
        messages.append({
            "role": "system",
            "content": system_content
        })
        
        # Add conversation history if available
        if conversation_history:
            formatted_history = self._format_conversation_history(conversation_history)
            messages.extend(formatted_history)
        
        # Add current user query
        messages.append({
            "role": "user",
            "content": query
        })
        
        return messages

    async def generate_response(
        self,
        query: str,
        context: List[Dict[str, Any]],
        temperature: float = 0.7,
        user_profile: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generate a response using the LLM with enhanced context support.
        
        Args:
            query: User's question
            context: Retrieved document context
            temperature: Response randomness (0.0 to 1.0)
            user_profile: User's medical profile
            conversation_history: Previous conversation messages
            
        Returns:
            Generated response string
        """
        try:
            # Log context information
            logger.info(f"🔍 LLM: Generating response for query: {query[:50]}...")
            if user_profile:
                logger.info(f"🔍 LLM: Using user profile with keys: {list(user_profile.keys())}")
            if conversation_history:
                logger.info(f"🔍 LLM: Using conversation history with {len(conversation_history)} messages")
            if context:
                logger.info(f"🔍 LLM: Using {len(context)} document chunks for context")
            
            # Build messages with all available context
            messages = self._build_prompt(query, context, user_profile, conversation_history)
            
            # Log the system message for debugging (truncated)
            if messages and messages[0]["role"] == "system":
                system_preview = messages[0]["content"][:200] + "..." if len(messages[0]["content"]) > 200 else messages[0]["content"]
                logger.info(f"🔍 LLM: System message preview: {system_preview}")
            
            # Generate response
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=500  # Reduced from 1000 to encourage more concise responses
            )
            
            generated_response = response.choices[0].message.content
            logger.info(f"✅ LLM: Generated response ({len(generated_response)} characters)")
            
            return generated_response
            
        except Exception as e:
            logger.error(f"❌ LLM: Error generating response: {str(e)}")
            
            # Provide fallback response with available context
            fallback_response = "I apologize, but I encountered an error while generating a response. "
            
            if context:
                fallback_response += f"Based on the information I found, here's what I can tell you: {context[0]['content'][:200]}..."
            else:
                fallback_response += "Please try rephrasing your question or ensure you have uploaded relevant medical documents."
            
            return fallback_response