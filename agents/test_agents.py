"""
Tests for RedevOps.io Social Autopilot Agents.

Run with: pytest -v
"""

import pytest
from unittest.mock import patch, MagicMock
import os


# ============================================
# Content Creator Agent Tests
# ============================================

class TestContentCreatorAgent:
    """Tests for the ContentCreatorAgent class."""
    
    def test_agent_initialization(self):
        """Test that agent initializes with default values."""
        from agents.content_creator import ContentCreatorAgent
        
        agent = ContentCreatorAgent()
        
        assert agent.agent_id == "content-creator"
        assert agent.platform_configs is not None
    
    def test_platform_configurations_exist(self):
        """Test that all expected platforms are configured."""
        from agents.content_creator import ContentCreatorAgent
        
        agent = ContentCreatorAgent()
        
        expected_platforms = ["twitter", "linkedin", "facebook", "instagram", "threads"]
        for platform in expected_platforms:
            assert platform in agent.platform_configs
            assert "max_length" in agent.platform_configs[platform]
    
    def test_get_platform_prompt(self):
        """Test prompt generation for a specific platform."""
        from agents.content_creator import ContentCreatorAgent
        
        agent = ContentCreatorAgent()
        
        prompt = agent._get_platform_prompt("twitter", "test topic", "professional")
        
        assert "twitter" in prompt.lower()
        assert "280" in prompt  # max length for Twitter
        assert "test topic" in prompt
    
    def test_suggest_posting_times(self):
        """Test that posting times are generated."""
        from agents.content_creator import ContentCreatorAgent
        
        agent = ContentCreatorAgent()
        
        times = agent._suggest_posting_times(["twitter", "linkedin"])
        
        assert len(times) > 0
        assert isinstance(times, list)


# ============================================
# Scheduling Optimizer Agent Tests
# ============================================

class TestSchedulingOptimizerAgent:
    """Tests for the SchedulingOptimizerAgent class."""
    
    def test_agent_initialization(self):
        """Test that agent initializes correctly."""
        from agents.scheduling_agent import SchedulingOptimizerAgent
        
        agent = SchedulingOptimizerAgent()
        
        assert agent.agent_id == "scheduling-optimizer"
        assert agent.platform_patterns is not None
    
    def test_platform_patterns_exist(self):
        """Test that platform patterns are defined."""
        from agents.scheduling_agent import SchedulingOptimizerAgent
        
        agent = SchedulingOptimizerAgent()
        
        expected_platforms = ["twitter", "linkedin", "facebook", "instagram"]
        for platform in expected_platforms:
            assert platform in agent.platform_patterns
    
    def test_urgency_classification(self):
        """Test urgency classification logic."""
        from agents.scheduling_agent import SchedulingOptimizerAgent
        
        agent = SchedulingOptimizerAgent()
        
        # Test critical detection
        assert agent._classify_urgency("This is urgent!") == "critical"
        assert agent._classify_urgency("I need help ASAP") == "critical"
    
    def test_sentiment_detection(self):
        """Test sentiment detection logic."""
        from agents.scheduling_agent import SchedulingOptimizerAgent
        
        agent = SchedulingOptimizerAgent()
        
        # Test positive sentiment
        assert agent._detect_sentiment("This is amazing!") == "positive"
        
        # Test negative sentiment  
        assert agent._detect_sentiment("This is terrible") == "negative"
    
    def test_timezone_adjusted_times(self):
        """Test timezone-adjusted time generation."""
        from agents.scheduling_agent import SchedulingOptimizerAgent
        
        agent = SchedulingOptimizerAgent()
        
        times = agent._get_timezone_adjusted_times([9, 10, 11], "UTC")
        
        assert len(times) == 3
        assert "09:00" in times[0]


# ============================================
# Engagement Manager Agent Tests
# ============================================

class TestEngagementManagerAgent:
    """Tests for the EngagementManagerAgent class."""
    
    def test_agent_initialization(self):
        """Test that agent initializes correctly."""
        from agents.engagement_agent import EngagementManagerAgent
        
        agent = EngagementManagerAgent()
        
        assert agent.agent_id == "engagement-manager"
        assert agent.critical_keywords is not None
    
    def test_urgency_classification(self):
        """Test urgency classification for various inputs."""
        from agents.engagement_agent import EngagementManagerAgent
        
        agent = EngagementManagerAgent()
        
        # Critical keywords
        assert agent._classify_urgency("This is urgent!") == "critical"
        assert agent._classify_urgency("I need a refund now") == "critical"
        
        # High priority keywords
        assert agent._classify_urgency("There's an issue with my order") == "high"
        assert agent._classify_urgency("Help, not working!") == "high"
        
        # Default cases
        assert agent._classify_urgency("Nice post!") in ["low", "medium"]
    
    def test_sentiment_detection(self):
        """Test sentiment detection for various inputs."""
        from agents.engagement_agent import EngagementManagerAgent
        
        agent = EngagementManagerAgent()
        
        # Positive
        assert agent._detect_sentiment("I love this product!") == "positive"
        
        # Negative
        assert agent._detect_sentiment("This is awful") == "negative"
        
        # Question
        assert agent._detect_sentiment("How do I use this?") == "question"
        
        # Neutral
        assert agent._detect_sentiment("Thanks for the update") == "neutral"
    
    def test_response_generation(self):
        """Test that responses are generated."""
        from agents.engagement_agent import EngagementManagerAgent
        
        agent = EngagementManagerAgent()
        
        response = agent._generate_response(
            original_text="Great product!",
            sentiment="positive",
            urgency="low"
        )
        
        assert len(response) > 0
        assert isinstance(response, str)
    
    def test_critical_escalation(self):
        """Test that critical items are flagged for escalation."""
        from agents.engagement_agent import EngagementManagerAgent
        
        agent = EngagementManagerAgent()
        
        response = agent._generate_response(
            original_text="I want to sue you!",
            sentiment="negative",
            urgency="critical"
        )
        
        assert "ESCALATE" in response.upper()


# ============================================
# Integration Tests (Mocked)
# ============================================

class TestAgentIntegration:
    """Integration tests with mocked LLM calls."""
    
    @patch('agents.content_creator.httpx.Client')
    @pytest.mark.asyncio
    async def test_content_creation_with_mock_llm(self, mock_client):
        """Test content creation flow with mocked LLM response."""
        from agents.content_creator import ContentCreatorAgent
        
        # Setup mock
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "This is generated content"}}]
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_instance = MagicMock()
        mock_instance.__enter__ = lambda s: mock_instance
        mock_instance.__exit__ = lambda s, *args: None
        mock_instance.post.return_value = mock_response
        
        mock_client.return_value = mock_instance
        
        # Set required env vars for the test
        os.environ["OPENAI_API_KEY"] = "test-key"
        
        agent = ContentCreatorAgent()
        result = await agent.create_content(
            topic="Test Topic",
            platforms=["twitter"],
            tone="professional"
        )
        
        assert result is not None
        assert "platforms" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
