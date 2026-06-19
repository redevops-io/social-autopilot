"""
Engagement Manager Agent for RedevOps.io Social Autopilot.

This agent monitors comments and mentions, drafts contextual responses,
and escalates urgent matters to human review.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential


logger = logging.getLogger(__name__)


class EngagementManagerAgent:
    """
    Autonomous agent for managing social media engagement.
    
    Monitors comments and mentions across platforms, drafts appropriate responses,
    and identifies urgent matters requiring human attention.
    """
    
    def __init__(self):
        self.agent_id = "engagement-manager"
        
        # Urgency classification keywords
        self.critical_keywords = [
            "urgent", "emergency", "asap", "immediately", "critical",
            "lawsuit", "legal", "complaint", "refund", "scam", "fraud"
        ]
        
        self.high_priority_keywords = [
            "problem", "issue", "broken", "not working", "error",
            "help", "support", "question", "concern"
        ]
        
        # Response templates by sentiment/type
        self.response_templates = {
            "positive": [
                "Thank you so much for your kind words! We really appreciate it. 🙏",
                "We're thrilled to hear you had a great experience! Thanks for sharing!",
                "This made our day! Thank you for being part of our community!"
            ],
            "neutral": [
                "Thanks for reaching out! How can we help?",
                "Great question! Let us look into this for you.",
                "We appreciate your feedback. What specifically would you like to know?"
            ],
            "negative": [
                "We're sorry to hear about your experience. We'd love to make this right - please DM us!",
                "Thank you for bringing this to our attention. Our team is looking into it.",
                "We apologize for the inconvenience. Let's resolve this together."
            ],
            "question": [
                "Great question! Here's what we know...",
                "Thanks for asking! The answer is...",
                "We're glad you asked! Here are the details..."
            ]
        }
    
    def _classify_urgency(self, text: str) -> str:
        """Classify the urgency level of a message."""
        text_lower = text.lower()
        
        # Check for critical keywords
        if any(keyword in text_lower for keyword in self.critical_keywords):
            return "critical"
        
        # Check for high priority keywords
        if any(keyword in text_lower for keyword in self.high_priority_keywords):
            return "high"
        
        # Default to low/medium based on sentiment analysis (simplified)
        negative_words = ["bad", "terrible", "awful", "horrible", "worst"]
        positive_words = ["great", "amazing", "excellent", "wonderful", "best"]
        
        if any(word in text_lower for word in negative_words):
            return "medium"
        
        return "low"
    
    def _detect_sentiment(self, text: str) -> str:
        """Detect the sentiment of a message."""
        text_lower = text.lower()
        
        positive_indicators = [
            "great", "amazing", "excellent", "wonderful", "love", 
            "awesome", "fantastic", "perfect", "best", "thank"
        ]
        
        negative_indicators = [
            "bad", "terrible", "awful", "horrible", "hate",
            "worst", "disappointed", "frustrated", "angry"
        ]
        
        positive_count = sum(1 for word in positive_indicators if word in text_lower)
        negative_count = sum(1 for word in negative_indicators if word in text_lower)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            # Check if it's a question
            if "?" in text or any(w in text_lower for w in ["how", "what", "when", "where", "why"]):
                return "question"
            return "neutral"
    
    def _generate_response(
        self, 
        original_text: str, 
        sentiment: str,
        urgency: str
    ) -> str:
        """Generate an appropriate response based on sentiment and context."""
        if urgency == "critical":
            # Critical issues should be escalated, not auto-responded
            return "[ESCALATE TO HUMAN] This requires immediate human attention."
        
        templates = self.response_templates.get(sentiment, self.response_templates["neutral"])
        
        # Simple selection based on length (could be improved with LLM)
        import random
        return random.choice(templates)
    
    def _analyze_engagement_data(
        self, 
        post_id: str,
        mentions: List[Dict[str, Any]] = None,
        comments: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze engagement data for a specific post."""
        mentions = mentions or []
        comments = comments or []
        
        # Count by urgency level
        urgency_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        responses = []
        
        all_items = mentions + comments
        
        for item in all_items:
            text = item.get("text", "") or ""
            urgency = self._classify_urgency(text)
            sentiment = self._detect_sentiment(text)
            
            # Update counts
            if urgency == "critical":
                urgency_counts["critical"] += 1
            elif urgency == "high":
                urgency_counts["high"] += 1
            
            # Generate suggested response
            response = {
                "item_id": item.get("id", ""),
                "original_text": text[:100],  # Truncate for display
                "sentiment": sentiment,
                "urgency": urgency,
                "suggested_response": self._generate_response(text, sentiment, urgency),
                "requires_human_review": urgency in ["critical", "high"]
            }
            responses.append(response)
        
        # Determine overall urgency level for the post
        if urgency_counts["critical"] > 0:
            overall_urgency = "critical"
        elif urgency_counts["high"] > 0:
            overall_urgency = "high"
        elif len(all_items) > 10:
            overall_urgency = "medium"
        else:
            overall_urgency = "low"
        
        return {
            "total_engagements": len(all_items),
            "mentions_count": len(mentions),
            "comments_count": len(comments),
            "urgency_counts": urgency_counts,
            "overall_urgency": overall_urgency,
            "responses": responses
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def manage_engagement(
        self,
        post_id: str,
        action: str = "monitor",
        draft_responses: bool = True,
        mentions: List[Dict[str, Any]] = None,
        comments: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Manage engagement for a specific post.
        
        Args:
            post_id: ID of the post to manage
            action: Action type - "monitor", "respond", or "escalate"
            draft_responses: Whether to draft AI responses
            mentions: Optional list of mention data
            comments: Optional list of comment data
            
        Returns:
            Dictionary with engagement analysis and suggested actions
        """
        logger.info(f"Managing engagement for post {post_id}, action: {action}")
        
        # Analyze the engagement data
        analysis = self._analyze_engagement_data(post_id, mentions, comments)
        
        result = {
            "post_id": post_id,
            "mentions_count": analysis["mentions_count"],
            "comments_count": analysis["comments_count"],
            "total_engagements": analysis["total_engagements"],
            "urgency_level": analysis["overall_urgency"],
            "requires_attention": analysis["overall_urgency"] in ["critical", "high"],
            "suggested_responses": [] if not draft_responses else [
                r for r in analysis["responses"] 
                if not r.get("requires_human_review")
            ],
            "escalation_queue": [
                r for r in analysis["responses"]
                if r.get("requires_human_review")
            ]
        }
        
        # Log escalation items
        if result["escalation_queue"]:
            logger.warning(
                f"Post {post_id} has {len(result['escalation_queue'])} items "
                "requiring human review"
            )
        
        return result


# Export for use in main.py
__all__ = ["EngagementManagerAgent"]
