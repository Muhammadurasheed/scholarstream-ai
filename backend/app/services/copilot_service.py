
import structlog
from typing import Dict, Any, List, Optional
import json

from app.services.ai_service import ai_service
from app.config import settings

logger = structlog.get_logger()

class CopilotService:
    """
    Service for the Chrome Extension Co-Pilot.
    Handles RAG, Page Context Analysis, and Chat.
    """
    
    async def chat(self, 
                   query: str, 
                   page_context: Dict[str, Any], 
                   project_context: Optional[str] = None,
                   user_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main chat handler.
        
        Args:
            query: User's voice/text input.
            page_context: HTML/Text of the current page.
            project_context: Content of uploaded README/Doc.
            user_profile: User's profile data.
            
        Returns:
            Dict with 'message' (agent response) and optional 'action' (fill field).
        """
        
        # Construct the "Mega Prompt" for Gemini 1.5 PRO
        # We leverage the 1M+ context window to dump everything in.
        # IMPROVED: Added Chain-of-Thought reasoning to reduce hallucinations.
        
        prompt = f"""
You are the ScholarStream Co-Pilot, an elite AI agent helping a student apply for a scholarship or hackathon opportunity.
You are running directly in their browser extension.

USER PROFILE:
{json.dumps(user_profile, indent=2) if user_profile else "Not provided"}

PROJECT CONTEXT (Uploaded Doc/Resume/Essay):
{project_context if project_context else "No project document uploaded."}

CURRENT PAGE CONTEXT (Refined):
- URL: {page_context.get('url')}
- Title: {page_context.get('title')}
- Visible Text (Truncated): {page_context.get('content', '')[:50000]} 

USER QUERY:
"{query}"

INSTRUCTIONS:
1.  **Analyze** the user's query in the context of the current page and their profile.
2.  **Determine Intent**:
    *   **Q&A**: If the user asks a question about the page or opportunity, answer it concisely.
    *   **DRAFTING**: If the user asks to write an essay, cover letter, or short answer, use the PROFILE and PROJECT CONTEXT to write a high-quality, personalized response.
    *   **FILLING**: If the user explicitly asks to "fill this field" or "put my name here", generate a `fill_field` action.
3.  **Output Format**: You must return ONLY a JSON object.

RESPONSE JSON STRUCTURE:
{{
  "thought_process": "Brief explanation of your reasoning (internal use)",
  "message": "The text response to show the user. If drafting, put the content here.",
  "action": {{
    "type": "fill_field", 
    "selector": "css_selector_for_closest_matching_field", 
    "value": "content_to_fill"
  }} OR null
}}
"""
        try:
            # Use Gemini Pro for reasoning/writing
            result = await ai_service.generate_content_async(prompt) # Ensure async call if available, else synchronous
            # Note: assuming scalar sync method if async not available, but 'await' implies async interface.
            # If ai_service.generate_content is sync, remove 'await'. 
            # wrapper for safety:
            if not result:
                 raise ValueError("Empty response from AI Service")

            # Parse JSON with robust cleanup
            text = result.strip()
            if text.startswith('```json'):
                text = text[7:]
            if text.endswith('```'):
                text = text[:-3]
            text = text.strip()
            
            response_data = json.loads(text)
            
            # Sanitize response
            return {
                "message": response_data.get("message", "I processed that for you."),
                "action": response_data.get("action")
            }
            
        except json.JSONDecodeError:
            logger.error("Copilot JSON Parse Error", raw_result=result)
            return {
                "message": "I understood your request, but I had a glitch processing the action. Here is the raw response: " + result[:200],
                "action": None
            }
        except Exception as e:
            logger.error("Copilot chat failed", error=str(e))
            return {
                "message": "I'm having trouble connecting to my brain right now. Please try again in a moment.",
                "action": None
            }

    async def generate_field_content(self, target_field: Dict[str, Any], user_profile: Dict[str, Any], instruction: Optional[str] = None) -> Dict[str, Any]:
        """
        Sparkle / Focus Fill Handler.
        Generates content for a SINGLE specific field with high precision.
        """
        prompt = f"""
You are the "Sparkle" engine for ScholarStream. A student is stuck on a form field.
Your job is to write the PERFECT content for just this one field.

USER PROFILE:
{json.dumps(user_profile, indent=2)}

TARGET FIELD INFO:
Label: {target_field.get('label')}
Name/ID: {target_field.get('name')} / {target_field.get('id')}
Placeholder: {target_field.get('placeholder')}
Type: {target_field.get('type')}
Surrounding Text: {target_field.get('surroundingText', '')}

USER INSTRUCTION: {instruction or "Fill this based on my profile."}

TASK:
1. Logic: Think about what this field needs. Is it a "Why do you want this?" essay? A "GitHub URL"?
2. Draft: Write the content. If it's an essay, make it compelling and professional. If it's a URL, be exact.
3. Reasoning: Explain why you wrote it this way in 1 short sentence.

OUTPUT JSON:
{{
  "content": "The actual text to fill in the box",
  "reasoning": "I used your project X to highlight leadership skills."
}}
"""
        try:
            # Reusing the async generation if available, else synchronous
            result = await ai_service.generate_content_async(prompt)
            
            # Simple cleanup for JSON
            cleaned = result.strip()
            if cleaned.startswith('```json'): cleaned = cleaned[7:]
            if cleaned.startswith('```'): cleaned = cleaned[3:]
            if cleaned.endswith('```'): cleaned = cleaned[:-3]
            
            data = json.loads(cleaned.strip())
            return data
        except Exception as e:
             logger.error("Sparkle generation failed", error=str(e))
             return {
                 "content": "",
                 "reasoning": "I had a brain freeze. Please type manually for now."
             }

copilot_service = CopilotService()
