"""
Message Analyzer - Identifies messages requiring follow-up

Uses rule-based analysis and optional AI analysis to determine
which messages need attention.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from anthropic import Anthropic
import os

from imessage_service import Conversation, Message

logger = logging.getLogger(__name__)


class FollowUpItem:
    """Represents a message or conversation requiring follow-up."""

    PRIORITY_URGENT = "urgent"
    PRIORITY_HIGH = "high"
    PRIORITY_MEDIUM = "medium"
    PRIORITY_LOW = "low"

    def __init__(
        self,
        conversation: Conversation,
        reason: str,
        priority: str,
        analysis: Optional[str] = None,
        suggested_actions: Optional[List[str]] = None
    ):
        """
        Initialize follow-up item.

        Args:
            conversation: The conversation needing follow-up
            reason: Why this needs follow-up
            priority: Priority level (urgent, high, medium, low)
            analysis: Optional AI analysis of the conversation
            suggested_actions: Optional list of suggested actions
        """
        self.conversation = conversation
        self.reason = reason
        self.priority = priority
        self.analysis = analysis or ""
        self.suggested_actions = suggested_actions or []
        self.identified_at = datetime.now()

    @property
    def contact_name(self) -> str:
        """Get the contact name for this follow-up."""
        return self.conversation.display_name

    @property
    def hours_since_last_message(self) -> float:
        """Calculate hours since last message."""
        if not self.conversation.last_message:
            return 0.0

        time_diff = datetime.now() - self.conversation.last_message.date
        return time_diff.total_seconds() / 3600

    def __repr__(self):
        return f"<FollowUpItem {self.priority.upper()}: {self.contact_name} - {self.reason}>"


class MessageAnalyzer:
    """Analyzes messages to identify follow-up needs."""

    # Keywords that suggest action items
    ACTION_KEYWORDS = [
        'schedule', 'confirm', 'send', 'call', 'email', 'book', 'reserve',
        'remind', 'let me know', 'can you', 'could you', 'would you',
        'please', 'need', 'should', 'must', 'have to'
    ]

    # Time-related keywords
    TIME_KEYWORDS = [
        'today', 'tomorrow', 'tonight', 'this week', 'next week',
        'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
        'deadline', 'by', 'before', 'after', 'at', 'am', 'pm'
    ]

    def __init__(self, config: dict):
        """
        Initialize message analyzer.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.use_ai_analysis = config.get('analysis', {}).get('use_ai_analysis', True)
        self.criteria = config.get('analysis', {}).get('criteria', {})
        self.min_hours = self.criteria.get('min_hours_since_message', 12)

        # Initialize Claude client if AI analysis is enabled
        self.claude_client = None
        if self.use_ai_analysis:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                self.claude_client = Anthropic(api_key=api_key)
                logger.info("Claude AI analysis enabled")
            else:
                logger.warning("ANTHROPIC_API_KEY not found. AI analysis disabled.")
                self.use_ai_analysis = False

    def analyze_conversations(
        self,
        conversations: List[Conversation]
    ) -> List[FollowUpItem]:
        """
        Analyze conversations to identify those requiring follow-up.

        Args:
            conversations: List of conversations to analyze

        Returns:
            List of FollowUpItem objects for conversations needing attention
        """
        follow_up_items = []

        for conversation in conversations:
            # Skip if no messages
            if not conversation.messages:
                continue

            # Skip if too recent (within min_hours threshold)
            if conversation.last_message:
                hours_since = (datetime.now() - conversation.last_message.date).total_seconds() / 3600
                if hours_since < self.min_hours:
                    continue

            # Check various criteria
            item = self._analyze_conversation(conversation)

            if item:
                follow_up_items.append(item)

        logger.info(f"Identified {len(follow_up_items)} conversations requiring follow-up")

        # Sort by priority
        priority_order = {
            FollowUpItem.PRIORITY_URGENT: 0,
            FollowUpItem.PRIORITY_HIGH: 1,
            FollowUpItem.PRIORITY_MEDIUM: 2,
            FollowUpItem.PRIORITY_LOW: 3
        }
        follow_up_items.sort(key=lambda x: priority_order.get(x.priority, 99))

        return follow_up_items

    def _analyze_conversation(self, conversation: Conversation) -> Optional[FollowUpItem]:
        """
        Analyze a single conversation.

        Args:
            conversation: Conversation to analyze

        Returns:
            FollowUpItem if follow-up needed, None otherwise
        """
        reasons = []
        priority = FollowUpItem.PRIORITY_LOW

        # Check: Unanswered questions
        if self.criteria.get('unanswered_questions', True):
            if self._has_unanswered_question(conversation):
                reasons.append("Unanswered question")
                priority = FollowUpItem.PRIORITY_HIGH

        # Check: Pending response (last message from other person)
        if self.criteria.get('pending_responses', True):
            if conversation.needs_response():
                reasons.append("Awaiting your response")
                if priority == FollowUpItem.PRIORITY_LOW:
                    priority = FollowUpItem.PRIORITY_MEDIUM

        # Check: Action items
        if self.criteria.get('action_items', True):
            if self._contains_action_item(conversation):
                reasons.append("Contains action item")
                priority = FollowUpItem.PRIORITY_HIGH

        # Check: Time-sensitive content
        if self.criteria.get('time_sensitive', True):
            if self._is_time_sensitive(conversation):
                reasons.append("Time-sensitive content")
                priority = FollowUpItem.PRIORITY_URGENT

        # If no reasons found, no follow-up needed
        if not reasons:
            return None

        # Combine reasons
        reason = "; ".join(reasons)

        # Optionally use AI for deeper analysis
        analysis = None
        suggested_actions = []

        if self.use_ai_analysis and self.claude_client:
            analysis, suggested_actions, ai_priority = self._ai_analyze_conversation(conversation)

            # AI can upgrade priority
            if ai_priority and ai_priority != priority:
                priority = ai_priority

        return FollowUpItem(
            conversation=conversation,
            reason=reason,
            priority=priority,
            analysis=analysis,
            suggested_actions=suggested_actions
        )

    def _has_unanswered_question(self, conversation: Conversation) -> bool:
        """
        Check if conversation has an unanswered question.

        Args:
            conversation: Conversation to check

        Returns:
            True if there's an unanswered question
        """
        # Get the last incoming message
        last_incoming = conversation.last_incoming_message

        if not last_incoming:
            return False

        # Check if it contains a question mark
        if '?' in last_incoming.text:
            # Check if we've responded since
            last_outgoing = conversation.last_outgoing_message

            if not last_outgoing:
                return True

            # If the question is more recent than our last response
            return last_incoming.date > last_outgoing.date

        return False

    def _contains_action_item(self, conversation: Conversation) -> bool:
        """
        Check if conversation contains action items.

        Args:
            conversation: Conversation to check

        Returns:
            True if action items found
        """
        # Check recent messages for action keywords
        recent_incoming = [m for m in conversation.messages if not m.is_from_me][-5:]

        for message in recent_incoming:
            text_lower = message.text.lower()

            for keyword in self.ACTION_KEYWORDS:
                if keyword in text_lower:
                    return True

        return False

    def _is_time_sensitive(self, conversation: Conversation) -> bool:
        """
        Check if conversation contains time-sensitive content.

        Args:
            conversation: Conversation to check

        Returns:
            True if time-sensitive content found
        """
        # Check recent messages for time keywords
        recent_incoming = [m for m in conversation.messages if not m.is_from_me][-3:]

        for message in recent_incoming:
            text_lower = message.text.lower()

            for keyword in self.TIME_KEYWORDS:
                if keyword in text_lower:
                    return True

        return False

    def _ai_analyze_conversation(
        self,
        conversation: Conversation
    ) -> tuple[Optional[str], List[str], Optional[str]]:
        """
        Use Claude AI to analyze conversation and suggest actions.

        Args:
            conversation: Conversation to analyze

        Returns:
            Tuple of (analysis text, suggested actions list, priority)
        """
        if not self.claude_client:
            return None, [], None

        try:
            # Build conversation context (last 10 messages)
            messages_context = []
            for msg in conversation.messages[-10:]:
                sender = "You" if msg.is_from_me else conversation.display_name
                timestamp = msg.date.strftime("%Y-%m-%d %H:%M")
                messages_context.append(f"[{timestamp}] {sender}: {msg.text}")

            context = "\n".join(messages_context)

            # Create prompt for Claude
            prompt = f"""Analyze this iMessage conversation and determine if it requires follow-up action.

Conversation with: {conversation.display_name}
Recent messages:
{context}

Please provide:
1. A brief analysis (2-3 sentences) of whether this conversation needs follow-up and why
2. Specific actions I should take (if any), formatted as a bullet list
3. Priority level: urgent, high, medium, or low

Format your response as:
ANALYSIS: [your analysis]
ACTIONS:
- [action 1]
- [action 2]
PRIORITY: [priority level]
"""

            # Call Claude API
            model = self.config.get('analysis', {}).get('claude_model', 'claude-sonnet-4-5-20250929')

            response = self.claude_client.messages.create(
                model=model,
                max_tokens=500,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Parse response
            response_text = response.content[0].text

            # Extract analysis
            analysis = None
            if "ANALYSIS:" in response_text:
                analysis = response_text.split("ANALYSIS:")[1].split("ACTIONS:")[0].strip()

            # Extract actions
            actions = []
            if "ACTIONS:" in response_text:
                actions_text = response_text.split("ACTIONS:")[1].split("PRIORITY:")[0].strip()
                actions = [
                    line.strip("- ").strip()
                    for line in actions_text.split("\n")
                    if line.strip() and line.strip().startswith("-")
                ]

            # Extract priority
            priority = None
            if "PRIORITY:" in response_text:
                priority_text = response_text.split("PRIORITY:")[1].strip().lower()
                for p in [FollowUpItem.PRIORITY_URGENT, FollowUpItem.PRIORITY_HIGH,
                          FollowUpItem.PRIORITY_MEDIUM, FollowUpItem.PRIORITY_LOW]:
                    if p in priority_text:
                        priority = p
                        break

            logger.debug(f"AI analysis for {conversation.display_name}: {analysis}")
            return analysis, actions, priority

        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return None, [], None
