"""Tests for debate agents."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from adversarial_debate.agents.search_debate_agent import SearchDebateAgent, _extract_json
from adversarial_debate.agents.sentiment_debate_agent import SentimentDebateAgent
from adversarial_debate.agents.valuation_debate_agent import ValuationDebateAgent
from adversarial_debate.models import DebatePosition


class TestExtractJson:
    """Tests for _extract_json utility."""

    def test_extract_json_clean(self):
        """Extract clean JSON without markdown fences."""
        result = _extract_json('{"position": "GO", "confidence": 0.8}')
        assert result == '{"position": "GO", "confidence": 0.8}'

    def test_extract_json_with_markdown(self):
        """Extract JSON from markdown code fences."""
        result = _extract_json('```json\n{"position": "GO", "confidence": 0.8}\n```')
        assert result == '{"position": "GO", "confidence": 0.8}'

    def test_extract_json_with_text_surrounding(self):
        """Extract JSON when surrounded by other text."""
        result = _extract_json('Here is the result: {"position": "GO", "confidence": 0.8} End.')
        assert result == '{"position": "GO", "confidence": 0.8}'


class TestSearchDebateAgent:
    """Tests for SearchDebateAgent."""

    def test_init(self):
        """Test agent initialization."""
        agent = SearchDebateAgent(risk_tolerance="risk_neutral")
        assert agent.risk_tolerance == "risk_neutral"
        assert agent.agent_name == "Search Agent"

    def test_debate_system_prompt_risk_neutral(self):
        """Test debate system prompt selection for risk_neutral."""
        agent = SearchDebateAgent()
        prompt = agent._debate_system_prompt("risk_neutral")
        assert "RISK_NEUTRAL" in prompt
        assert "FOUNDER QUALITY" in prompt

    def test_debate_system_prompt_risk_averse(self):
        """Test debate system prompt selection for risk_averse."""
        agent = SearchDebateAgent()
        prompt = agent._debate_system_prompt("risk_averse")
        assert "RISK_AVERSE" in prompt

    def test_format_debate_history_empty(self):
        """Test formatting empty debate history."""
        agent = SearchDebateAgent()
        result = agent._format_debate_history([])
        assert result == "No prior positions."

    def test_format_debate_history_with_entries(self):
        """Test formatting debate history with entries."""
        agent = SearchDebateAgent()
        history = [
            {
                "round_number": 1,
                "agent_name": "Sentiment Agent",
                "position": "GO",
                "confidence": 0.8,
                "rationale": "Positive sentiment",
                "challenges": ["Founder concern"],
            }
        ]
        result = agent._format_debate_history(history)
        assert "Round 1" in result
        assert "Sentiment Agent" in result
        assert "GO" in result
        assert "Positive sentiment" in result
        assert "Founder concern" in result

    @patch("adversarial_debate.agents.search_debate_agent.AnthropicClient")
    def test_debate_turn_go(self, mock_llm_class):
        """Test debate_turn returns GO position."""
        mock_llm = MagicMock()
        mock_llm.messages_create.return_value = '{"position": "GO", "confidence": 0.85, "rationale": "Strong founders", "challenges": ["Market concern"]}'
        mock_llm_class.return_value = mock_llm

        agent = SearchDebateAgent()
        result = agent.debate_turn(
            company="TestCo",
            phase1_analysis='{"company": {"name": "TestCo"}}',
            debate_history=[],
            round_number=1,
            risk_tolerance="risk_neutral",
        )

        assert isinstance(result, DebatePosition)
        assert result.agent_name == "Search Agent"
        assert result.position == "GO"
        assert result.confidence == 0.85
        assert result.rationale == "Strong founders"
        assert result.challenges == ["Market concern"]
        assert result.round_number == 1

    @patch("adversarial_debate.agents.search_debate_agent.AnthropicClient")
    def test_debate_turn_parse_error_fallback(self, mock_llm_class):
        """Test debate_turn returns safe fallback on parse error."""
        mock_llm = MagicMock()
        mock_llm.messages_create.return_value = "Invalid JSON{{{"
        mock_llm_class.return_value = mock_llm

        agent = SearchDebateAgent()
        result = agent.debate_turn(
            company="TestCo",
            phase1_analysis='{"company": {"name": "TestCo"}}',
            debate_history=[],
            round_number=1,
            risk_tolerance="risk_neutral",
        )

        assert result.position == "NOGO"
        assert result.confidence == 0.0
        assert "Parse error" in result.rationale


class TestSentimentDebateAgent:
    """Tests for SentimentDebateAgent."""

    def test_init(self):
        """Test agent initialization."""
        agent = SentimentDebateAgent(risk_tolerance="risk_averse")
        assert agent.risk_tolerance == "risk_averse"
        assert agent.agent_name == "Sentiment Agent"

    @patch("adversarial_debate.agents.sentiment_debate_agent.AnthropicClient")
    def test_debate_turn_nogo(self, mock_llm_class):
        """Test debate_turn returns NOGO position."""
        mock_llm = MagicMock()
        mock_llm.messages_create.return_value = '{"position": "NOGO", "confidence": 0.6, "rationale": "Mixed sentiment", "challenges": []}'
        mock_llm_class.return_value = mock_llm

        agent = SentimentDebateAgent()
        result = agent.debate_turn(
            company="TestCo",
            phase1_analysis='{"sentiment": {"overall_sentiment_score": 50}}',
            debate_history=[],
            round_number=1,
            risk_tolerance="risk_neutral",
        )

        assert result.position == "NOGO"
        assert result.confidence == 0.6


class TestValuationDebateAgent:
    """Tests for ValuationDebateAgent."""

    def test_init(self):
        """Test agent initialization."""
        agent = ValuationDebateAgent()
        assert agent.risk_tolerance == "risk_neutral"
        assert agent.agent_name == "Valuation Agent"

    @patch("adversarial_debate.agents.valuation_debate_agent.AnthropicClient")
    def test_debate_turn_go(self, mock_llm_class):
        """Test debate_turn returns GO position."""
        mock_llm = MagicMock()
        mock_llm.messages_create.return_value = '{"position": "GO", "confidence": 0.75, "rationale": "Good return potential", "challenges": ["Founder risk"]}'
        mock_llm_class.return_value = mock_llm

        agent = ValuationDebateAgent()
        result = agent.debate_turn(
            company="TestCo",
            phase1_analysis='{"valuation": {"overall_attractiveness_score": 70}}',
            debate_history=[],
            round_number=1,
            risk_tolerance="risk_neutral",
        )

        assert result.position == "GO"
        assert result.confidence == 0.75
        assert "Founder risk" in result.challenges
