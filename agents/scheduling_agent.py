"""
Scheduling Optimizer Agent for RedevOps.io Social Autopilot.

This agent analyzes historical engagement data and recommends optimal posting times
for maximum reach and engagement across social media platforms.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential


logger = logging.getLogger(__name__)


class SchedulingOptimizerAgent:
    """
    Autonomous agent for optimizing social media posting schedules.
    
    Uses historical engagement data and platform-specific best practices
    to recommend optimal posting times.
    """
    
    def __init__(self):
        self.agent_id = "scheduling-optimizer"
        
        # Platform-specific optimal time patterns (hour-based, 24h format)
        self.platform_patterns = {
            "twitter": {
                "optimal_hours": [9, 10, 11, 13, 17, 18, 19, 20],
                "best_days": ["Wednesday", "Thursday", "Friday"],
                "peak_engagement": {"hour": 9, "day": "Wednesday"},
                "posting_frequency": "multiple daily"
            },
            "linkedin": {
                "optimal_hours": [8, 9, 10, 12, 17, 18],
                "best_days": ["Tuesday", "Wednesday", "Thursday"],
                "peak_engagement": {"hour": 10, "day": "Wednesday"},
                "posting_frequency": "daily or every other day"
            },
            "facebook": {
                "optimal_hours": [13, 14, 15, 16, 19, 20],
                "best_days": ["Thursday", "Friday", "Saturday"],
                "peak_engagement": {"hour": 15, "day": "Thursday"},
                "posting_frequency": "daily"
            },
            "instagram": {
                "optimal_hours": [11, 12, 13, 17, 18, 19],
                "best_days": ["Monday", "Wednesday", "Friday"],
                "peak_engagement": {"hour": 11, "day": "Monday"},
                "posting_frequency": "daily"
            },
            "threads": {
                "optimal_hours": [9, 10, 12, 14, 18, 19],
                "best_days": ["Tuesday", "Wednesday", "Thursday"],
                "peak_engagement": {"hour": 12, "day": "Wednesday"},
                "posting_frequency": "multiple daily"
            }
        }
    
    def _analyze_historical_data(
        self, 
        historical_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Analyze historical engagement data to find patterns.
        
        Returns a confidence score based on data quality and quantity.
        """
        if not historical_data:
            # No historical data - return baseline confidence
            logger.info("No historical data provided, using platform defaults")
            return {"confidence": 0.5}
        
        try:
            # Calculate confidence based on data points
            engagement_points = len(historical_data.get("engagement", []))
            
            if engagement_points >= 100:
                confidence = 0.9
            elif engagement_points >= 50:
                confidence = 0.75
            elif engagement_points >= 20:
                confidence = 0.6
            else:
                confidence = 0.5
            
            return {"confidence": confidence}
        except Exception as e:
            logger.error(f"Error analyzing historical data: {e}")
            return {"confidence": 0.3}
    
    def _get_timezone_adjusted_times(
        self, 
        optimal_hours: List[int], 
        timezone: Optional[str] = None
    ) -> List[str]:
        """Convert optimal hours to formatted time strings."""
        if not timezone or timezone == "UTC":
            return [f"{h:02d}:00" for h in optimal_hours[:6]]  # Top 6 hours
        
        # For other timezones, we'd need pytz or zoneinfo
        # For now, return the base times with a note
        times = [f"{h:02d}:00 (UTC)" for h in optimal_hours[:6]]
        times.append(f"Adjust to {timezone} local time")
        return times
    
    def _generate_recommendations(
        self, 
        platform: str, 
        pattern: Dict[str, Any],
        confidence: float
    ) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []
        
        # Frequency recommendation
        recommendations.append(
            f"Post {pattern['posting_frequency']} for optimal engagement"
        )
        
        # Best day recommendation
        best_day = pattern["best_days"][0] if pattern["best_days"] else "weekday"
        recommendations.append(
            f"Prioritize {best_day} posts for highest reach"
        )
        
        # Peak time recommendation
        peak = pattern["peak_engagement"]
        recommendations.append(
            f"Scheduled posts at {peak['hour']:02d}:00 on {peak['day']} for maximum impact"
        )
        
        # Confidence-based advice
        if confidence < 0.5:
            recommendations.append(
                "Collect more engagement data to improve recommendations"
            )
        elif confidence > 0.8:
            recommendations.append(
                "High confidence - consider A/B testing different time slots"
            )
        
        return recommendations
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def optimize_schedule(
        self,
        platform: str,
        timezone: Optional[str] = None,
        historical_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Optimize posting schedule for a specific platform.
        
        Args:
            platform: Target social media platform
            timezone: Target audience timezone (e.g., "America/New_York")
            historical_data: Optional historical engagement data
            
        Returns:
            Dictionary with optimal times, confidence score, and recommendations
        """
        logger.info(f"Optimizing schedule for {platform}")
        
        # Get platform pattern
        pattern = self.platform_patterns.get(platform)
        
        if not pattern:
            # Fallback to generic pattern
            logger.warning(f"No specific pattern for {platform}, using defaults")
            pattern = {
                "optimal_hours": [9, 12, 15, 18],
                "best_days": ["Tuesday", "Wednesday", "Thursday"],
                "peak_engagement": {"hour": 12, "day": "Wednesday"},
                "posting_frequency": "daily"
            }
        
        # Analyze historical data if provided
        analysis = self._analyze_historical_data(historical_data)
        confidence = analysis.get("confidence", 0.5)
        
        # Get timezone-adjusted optimal times
        optimal_times = self._get_timezone_adjusted_times(
            pattern["optimal_hours"], 
            timezone
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(platform, pattern, confidence)
        
        return {
            "platform": platform,
            "optimal_times": optimal_times,
            "best_days": pattern["best_days"],
            "peak_time": f"{pattern['peak_engagement']['hour']:02d}:00 on {pattern['peak_engagement']['day']}",
            "confidence": confidence,
            "recommendations": recommendations,
            "timezone": timezone or "UTC"
        }


# Export for use in main.py
__all__ = ["SchedulingOptimizerAgent"]
