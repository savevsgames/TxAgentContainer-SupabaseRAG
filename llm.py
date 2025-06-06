import os
import logging
from typing import List, Dict, Any
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("llm")

class LLMHandler:
    """Handles LLM interactions for chat responses."""
    
    def __init__(self):
        """Initialize the LLM handler."""
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
        
    def _build_prompt(self, query: str, context: List[Dict[str, Any]]) -> str:
        """Build prompt from query and context."""
        context_text = "\n\n".join([
            f"Document {i+1}:\n{doc['content']}"
            for i, doc in enumerate(context)
        ])
        
        return f"""You are a medical AI assistant. Answer the following question based on the provided context. 
If you cannot find relevant information in the context, say so. Do not make up information.

Context:
{context_text}

Question: {query}

Answer:"""

    async def generate_response(
        self,
        query: str,
        context: List[Dict[str, Any]],
        temperature: float = 0.7
    ) -> str:
        """Generate a response using the LLM."""
        try:
            prompt = self._build_prompt(query, context)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a medical AI assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}")
            raise