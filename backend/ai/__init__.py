"""AI Module for Groq LLM Integration.

This module provides OPTIONAL intelligent intent parsing using Groq's LLM.
It does NOT replace business logic - only enhances language understanding.

If LLM fails, the system falls back to keyword-based parsing.
"""

from .intent_parser import parse_message_with_ai
from .fallback import parse_message_fallback

__all__ = ["parse_message_with_ai", "parse_message_fallback"]
