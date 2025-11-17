"""
Action Recommender - Generates AI-powered action recommendations

Uses Claude to generate specific, actionable recommendations
for how to respond to messages and how Claude Code can help.
"""

import logging
import os
from typing import List, Dict, Optional
from anthropic import Anthropic

from message_analyzer import FollowUpItem

logger = logging.getLogger(__name__)


class ActionRecommendation:
    """Represents a recommended action."""

    def __init__(
        self,
        title: str,
        description: str,
        action_type: str,
        details: Optional[Dict] = None
    ):
        """
        Initialize action recommendation.

        Args:
            title: Short title for the action
            description: Detailed description
            action_type: Type (respond, task, calendar, other)
            details: Additional details specific to action type
        """
        self.title = title
        self.description = description
        self.action_type = action_type
        self.details = details or {}

    def __repr__(self):
        return f"<ActionRecommendation {self.action_type}: {self.title}>"


class ActionRecommender:
    """Generates action recommendations using AI."""

    def __init__(self, config: dict):
        """
        Initialize action recommender.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.recommendations_config = config.get('analysis', {}).get('recommendations', {})

        # Initialize Claude client
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            self.claude_client = Anthropic(api_key=api_key)
            logger.info("Action recommender initialized with Claude API")
        else:
            logger.warning("ANTHROPIC_API_KEY not found. Recommendations disabled.")
            self.claude_client = None

    def generate_recommendations(
        self,
        follow_up_item: FollowUpItem
    ) -> List[ActionRecommendation]:
        """
        Generate action recommendations for a follow-up item.

        Args:
            follow_up_item: The follow-up item to generate recommendations for

        Returns:
            List of ActionRecommendation objects
        """
        if not self.claude_client:
            return []

        if not self.recommendations_config.get('enabled', True):
            return []

        try:
            # Build conversation context
            conversation = follow_up_item.conversation
            messages_context = []

            for msg in conversation.messages[-10:]:
                sender = "You" if msg.is_from_me else conversation.display_name
                timestamp = msg.date.strftime("%Y-%m-%d %H:%M")
                messages_context.append(f"[{timestamp}] {sender}: {msg.text}")

            context = "\n".join(messages_context)

            # Create prompt
            prompt = self._build_recommendations_prompt(
                contact_name=conversation.display_name,
                context=context,
                reason=follow_up_item.reason,
                priority=follow_up_item.priority
            )

            # Call Claude API
            model = self.config.get('analysis', {}).get('claude_model', 'claude-sonnet-4-5-20250929')

            response = self.claude_client.messages.create(
                model=model,
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Parse recommendations
            recommendations = self._parse_recommendations(response.content[0].text)

            logger.info(f"Generated {len(recommendations)} recommendations for {conversation.display_name}")
            return recommendations

        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            return []

    def _build_recommendations_prompt(
        self,
        contact_name: str,
        context: str,
        reason: str,
        priority: str
    ) -> str:
        """Build the prompt for Claude to generate recommendations."""

        suggest_responses = self.recommendations_config.get('suggest_responses', True)
        suggest_tasks = self.recommendations_config.get('suggest_tasks', True)
        suggest_calendar = self.recommendations_config.get('suggest_calendar_events', True)

        prompt = f"""You are helping someone manage their iMessage conversations. They have a message thread that needs follow-up.

Contact: {contact_name}
Priority: {priority}
Reason: {reason}

Recent conversation:
{context}

Please provide specific, actionable recommendations for how to respond or follow up. Consider:
"""

        if suggest_responses:
            prompt += "\n- Suggested response messages (be specific and contextual)"

        if suggest_tasks:
            prompt += "\n- Tasks that should be created in a task manager"

        if suggest_calendar:
            prompt += "\n- Calendar events that should be scheduled"

        prompt += """

Also suggest how Claude Code (an AI coding assistant) could help automate or assist with the follow-up.

Format your response as:

RESPONSE SUGGESTIONS:
- [Suggestion 1 with exact wording they could send]
- [Suggestion 2 with exact wording they could send]

TASK RECOMMENDATIONS:
- [Task 1: specific task to create]
- [Task 2: specific task to create]

CALENDAR RECOMMENDATIONS:
- [Event 1: what to schedule and when]

CLAUDE CODE ASSISTANCE:
- [How Claude Code could help automate this]
- [Specific automation suggestions]

Keep suggestions practical and immediately actionable.
"""

        return prompt

    def _parse_recommendations(self, response_text: str) -> List[ActionRecommendation]:
        """Parse Claude's response into ActionRecommendation objects."""

        recommendations = []

        # Parse response suggestions
        if "RESPONSE SUGGESTIONS:" in response_text:
            section = self._extract_section(response_text, "RESPONSE SUGGESTIONS:", "TASK RECOMMENDATIONS:")
            for item in self._extract_bullet_items(section):
                recommendations.append(ActionRecommendation(
                    title="Suggested Response",
                    description=item,
                    action_type="respond",
                    details={"message": item}
                ))

        # Parse task recommendations
        if "TASK RECOMMENDATIONS:" in response_text:
            section = self._extract_section(response_text, "TASK RECOMMENDATIONS:", "CALENDAR RECOMMENDATIONS:")
            for item in self._extract_bullet_items(section):
                recommendations.append(ActionRecommendation(
                    title="Create Task",
                    description=item,
                    action_type="task",
                    details={"task_title": item}
                ))

        # Parse calendar recommendations
        if "CALENDAR RECOMMENDATIONS:" in response_text:
            section = self._extract_section(response_text, "CALENDAR RECOMMENDATIONS:", "CLAUDE CODE ASSISTANCE:")
            for item in self._extract_bullet_items(section):
                recommendations.append(ActionRecommendation(
                    title="Schedule Event",
                    description=item,
                    action_type="calendar",
                    details={"event_description": item}
                ))

        # Parse Claude Code assistance suggestions
        if "CLAUDE CODE ASSISTANCE:" in response_text:
            section = self._extract_section(response_text, "CLAUDE CODE ASSISTANCE:", None)
            for item in self._extract_bullet_items(section):
                recommendations.append(ActionRecommendation(
                    title="Automate with Claude Code",
                    description=item,
                    action_type="automation",
                    details={"automation_idea": item}
                ))

        return recommendations

    @staticmethod
    def _extract_section(text: str, start_marker: str, end_marker: Optional[str]) -> str:
        """Extract a section of text between two markers."""
        try:
            start_idx = text.index(start_marker) + len(start_marker)

            if end_marker and end_marker in text:
                end_idx = text.index(end_marker, start_idx)
                return text[start_idx:end_idx].strip()
            else:
                return text[start_idx:].strip()

        except ValueError:
            return ""

    @staticmethod
    def _extract_bullet_items(text: str) -> List[str]:
        """Extract bullet point items from text."""
        items = []

        for line in text.split('\n'):
            line = line.strip()

            # Look for bullet points (-, *, •)
            if line.startswith('-') or line.startswith('*') or line.startswith('•'):
                item = line[1:].strip()
                if item:
                    items.append(item)

        return items
