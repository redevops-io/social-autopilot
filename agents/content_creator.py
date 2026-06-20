"""
Content Creator Agent for RedevOps.io Social Autopilot.

This agent generates social media content from topics, creating platform-specific
variations with appropriate tone, length, and hashtag suggestions.
"""

import logging
import os
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential

try:
    from agent_harness import AgentHarness, ToolRegistry
except ImportError:
    # Fallback if agent-harness is not installed
    class AgentHarness:
        pass
    
    class ToolRegistry:
        pass


logger = logging.getLogger(__name__)


class ContentCreatorAgent:
    """
    Autonomous agent for creating social media content.
    
    Uses an OpenAI-compatible LLM to generate engaging, platform-specific
    content from user-provided topics.
    """
    
    def __init__(self):
        self.agent_id = "content-creator"
        self.base_url = None
        self.api_key = None
        self.model = None
        
        # Initialize configuration from environment
        self._load_config()
        
        # Platform-specific configurations
        self.platform_configs = {
            "twitter": {
                "max_length": 280,
                "name": "Twitter/X",
                "format": "short post with hashtags"
            },
            "linkedin": {
                "max_length": 3000,
                "name": "LinkedIn",
                "format": "professional post with engagement hook"
            },
            "facebook": {
                "max_length": 63206,
                "name": "Facebook",
                "format": "conversational post with call-to-action"
            },
            "instagram": {
                "max_length": 2200,
                "name": "Instagram",
                "format": "caption with emoji and hashtags"
            },
            "threads": {
                "max_length": 500,
                "name": "Threads",
                "format": "casual post with engagement focus"
            }
        }
    
    def _load_config(self):
        """Load LLM configuration from environment variables."""
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.model = os.getenv("MODEL", "mistralai/mistral-large-2407")
        
        if not self.api_key:
            logger.warning("No OPENAI_API_KEY set. Agent will run in demo mode.")
    
    def _get_platform_prompt(self, platform: str, topic: str, tone: str) -> str:
        """Generate a platform-specific prompt for content creation."""
        config = self.platform_configs.get(platform, {"max_length": 280, "name": platform})
        
        return f"""Create engaging social media content about "{topic}" for {config['name']}.

Requirements:
- Platform: {platform} (max {config['max_length']} characters)
- Tone: {tone}
- Format: {config['format']}
- Include relevant hashtags if appropriate
- Make it engaging and shareable

Provide only the content, no explanations."""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _generate_with_llm(self, prompt: str) -> str:
        """Generate content using the configured LLM endpoint."""
        import httpx
        
        if not self.api_key:
            # Demo mode - return placeholder content
            return f"[Demo Mode] Content for {prompt[:50]}..."
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "You are a social media content expert."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": float(os.getenv("TEMPERATURE", 0.7))
                    }
                )
                
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise
    
    async def create_content(
        self,
        topic: str,
        platforms: List[str] = None,
        tone: str = "professional",
        include_hashtags: bool = True
    ) -> Dict[str, Any]:
        """
        Create social media content for specified platforms.
        
        Args:
            topic: The main topic or theme
            platforms: List of target platforms (default: ["twitter", "linkedin"])
            tone: Content tone/style
            include_hashtags: Whether to include hashtags
            
        Returns:
            Dictionary with generated content per platform
        """
        if platforms is None:
            platforms = ["twitter", "linkedin"]
        
        logger.info(f"Creating content for topic '{topic}' on {platforms}")
        
        result = {
            "id": str(uuid.uuid4()),
            "topic": topic,
            "platforms": {},
            "suggested_times": [],
            "created_at": datetime.utcnow().isoformat()
        }
        
        for platform in platforms:
            prompt = self._get_platform_prompt(platform, topic, tone)
            
            try:
                content = self._generate_with_llm(prompt)
                
                # Add hashtags if requested and not already included
                if include_hashtags and platform == "twitter":
                    # Suggest additional hashtags for Twitter
                    hashtags = f"\n\n# {topic.replace(' ', '')} #{tone}"
                    content = (content + hashtags)[:280]
                
                result["platforms"][platform] = {
                    "content": content,
                    "length": len(content),
                    "has_hashtags": include_hashtags
                }
            except Exception as e:
                logger.error(f"Failed to create content for {platform}: {e}")
                result["platforms"][platform] = {
                    "error": str(e),
                    "content": f"[Error generating content for {platform}]"
                }
        
        # Generate suggested posting times (basic heuristic)
        result["suggested_times"] = self._suggest_posting_times(platforms)
        
        return result
    
    def _suggest_posting_times(self, platforms: List[str]) -> List[str]:
        """Generate basic suggested posting times based on platform best practices."""
        suggestions = []
        
        for platform in platforms:
            if platform == "twitter":
                # Twitter: Best engagement 9-11 AM and 7-9 PM
                suggestions.extend(["09:00", "11:00", "19:00", "21:00"])
            elif platform == "linkedin":
                # LinkedIn: Best on weekdays 8-10 AM, 12 PM, 5-6 PM
                suggestions.extend(["08:00", "09:00", "12:00", "17:00"])
            elif platform == "facebook":
                # Facebook: Best engagement 1-4 PM weekdays
                suggestions.extend(["13:00", "15:00", "16:00"])
        
        return list(set(suggestions))


# Export for use in main.py
__all__ = ["ContentCreatorAgent"]
