"""Tests for DebateOrchestrator."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from adversarial_debate.models import DebatePosition, DebateRound
from adversarial_debate.orchestrator import DebateOrchestrator


class TestCheckConsensus:
    """Tests for _check_consensus method."""

    def test_all_go_consensus(self):
        """Test consensus reached when all positions are GO."""
        orchestrator = DebateOrchestrator()
        positions = [
            DebatePosition("Search Agent", "GO", 0.8, "Good", [], 1),
            DebatePosition("Sentiment Agent", "GO", 0.7, "Good", [], 1),
            DebatePosition("Valuation Agent", "GO", 0.75, "Good", [], 1),
        ]
        result, position = orchestrator._check_consensus(positions)
        assert result is True
        assert position == "GO"

    def test_all_nogo_consensus(self):
        """Test consensus reached when all positions are NOGO."""
        orchestrator = DebateOrchestrator()
        positions = [
            DebatePosition("Search Agent", "NOGO", 0.6, "Bad", [], 1),
            DebatePosition("Sentiment Agent", "NOGO", 0.5, "Bad", [], 1),
            DebatePosition("Valuation Agent", "NOGO", 0.4, "Bad", [], 1),
        ]
        result, position = orchestrator._check_consensus(positions)
        assert result is True
        assert position == "NOGO"

    def test_mixed_no_consensus(self):
        """Test no consensus when positions are mixed."""
        orchestrator = DebateOrchestrator()
        positions = [
            DebatePosition("Search Agent", "GO", 0.8, "Good", [], 1),
            DebatePosition("Sentiment Agent", "NOGO", 0.6, "Bad", [], 1),
            DebatePosition("Valuation Agent", "GO", 0.55, "Okay", [], 1),
        ]
        result, position = orchestrator._check_consensus(positions)
        assert result is False
        assert position is None

    def test_empty_positions(self):
        """Test no consensus with empty positions list."""
        orchestrator = DebateOrchestrator()
        result, position = orchestrator._check_consensus([])
        assert result is False
        assert position is None


class TestMajorityVote:
    """Tests for _majority_vote method."""

    def test_majority_go(self):
        """Test majority vote returns GO when GO has more votes."""
        orchestrator = DebateOrchestrator()
        rounds = [
            DebateRound(1, [
                DebatePosition("Search Agent", "GO", 0.8, "", [], 1),
                DebatePosition("Sentiment Agent", "GO", 0.7, "", [], 1),
                DebatePosition("Valuation Agent", "NOGO", 0.6, "", [], 1),
            ], False, None),
        ]
        result = orchestrator._majority_vote(rounds)
        assert result == "GO"

    def test_majority_nogo(self):
        """Test majority vote returns NOGO when NOGO has more votes."""
        orchestrator = DebateOrchestrator()
        rounds = [
            DebateRound(1, [
                DebatePosition("Search Agent", "NOGO", 0.6, "", [], 1),
                DebatePosition("Sentiment Agent", "NOGO", 0.5, "", [], 1),
                DebatePosition("Valuation Agent", "GO", 0.7, "", [], 1),
            ], False, None),
        ]
        result = orchestrator._majority_vote(rounds)
        assert result == "NOGO"

    def test_tie_defaults_to_nogo(self):
        """Test tie defaults to NOGO."""
        orchestrator = DebateOrchestrator()
        rounds = [
            DebateRound(1, [
                DebatePosition("Search Agent", "GO", 0.8, "", [], 1),
                DebatePosition("Sentiment Agent", "NOGO", 0.6, "", [], 1),
                DebatePosition("Valuation Agent", "GO", 0.7, "", [], 1),
                DebatePosition("Search Agent", "NOGO", 0.5, "", [], 2),
            ], False, None),
        ]
        # 2 GO, 2 NOGO -> tie -> NOGO
        result = orchestrator._majority_vote(rounds)
        assert result == "NOGO"

    def test_empty_rounds_defaults_to_nogo(self):
        """Test empty rounds list defaults to NOGO."""
        orchestrator = DebateOrchestrator()
        result = orchestrator._majority_vote([])
        assert result == "NOGO"

    def test_multi_round_accumulation(self):
        """Test majority vote accumulates across all rounds."""
        orchestrator = DebateOrchestrator()
        rounds = [
            DebateRound(1, [
                DebatePosition("Search Agent", "GO", 0.8, "", [], 1),
                DebatePosition("Sentiment Agent", "NOGO", 0.6, "", [], 1),
                DebatePosition("Valuation Agent", "GO", 0.7, "", [], 1),
            ], False, None),
            DebateRound(2, [
                DebatePosition("Search Agent", "GO", 0.9, "", [], 2),
                DebatePosition("Sentiment Agent", "GO", 0.75, "", [], 2),
                DebatePosition("Valuation Agent", "NOGO", 0.5, "", [], 2),
            ], False, None),
        ]
        # Round 1: 2 GO, 1 NOGO
        # Round 2: 2 GO, 1 NOGO
        # Total: 4 GO, 2 NOGO -> GO
        result = orchestrator._majority_vote(rounds)
        assert result == "GO"


class TestRunDebate:
    """Tests for _run_debate method."""

    @patch("adversarial_debate.orchestrator.SearchDebateAgent")
    @patch("adversarial_debate.orchestrator.SentimentDebateAgent")
    @patch("adversarial_debate.orchestrator.ValuationDebateAgent")
    def test_round_1_consensus_exits_early(
        self, mock_valuation_class, mock_sentiment_class, mock_search_class
    ):
        """Test debate exits early when consensus reached in round 1."""
        # Mock all agents to return GO
        for mock_cls in [mock_search_class, mock_sentiment_class, mock_valuation_class]:
            mock_agent = MagicMock()
            mock_agent.debate_turn.return_value = DebatePosition(
                agent_name="Agent",
                position="GO",
                confidence=0.8,
                rationale="Good",
                challenges=[],
                round_number=1,
            )
            mock_cls.return_value = mock_agent

        orchestrator = DebateOrchestrator(max_rounds=3)

        phase1_map = {
            "Search Agent": MagicMock(content='{"company": {"name": "TestCo"}}'),
            "Sentiment Agent": MagicMock(content='{"sentiment": {}}'),
            "Valuation Agent": MagicMock(content='{"valuation": {}}'),
        }

        rounds, verdict, consensus = orchestrator._run_debate(
            company="TestCo",
            risk_tolerance="risk_neutral",
            phase1_map=phase1_map,
            status_callback=None,
        )

        assert len(rounds) == 1
        assert verdict == "GO"
        assert consensus is True
        assert rounds[0].consensus_reached is True

    @patch("adversarial_debate.orchestrator.SearchDebateAgent")
    @patch("adversarial_debate.orchestrator.SentimentDebateAgent")
    @patch("adversarial_debate.orchestrator.ValuationDebateAgent")
    def test_max_rounds_triggers_majority_vote(
        self, mock_valuation_class, mock_sentiment_class, mock_search_class
    ):
        """Test debate uses majority vote when max_rounds exceeded."""
        # Mock agents to never reach consensus
        call_count = {"search": 0, "sentiment": 0, "valuation": 0}

        def mock_search_turn(*args, **kwargs):
            call_count["search"] += 1
            return DebatePosition("Search Agent", "GO", 0.8, "Good", [], call_count["search"])

        def mock_sentiment_turn(*args, **kwargs):
            call_count["sentiment"] += 1
            return DebatePosition("Sentiment Agent", "NOGO", 0.6, "Bad", [], call_count["sentiment"])

        def mock_valuation_turn(*args, **kwargs):
            call_count["valuation"] += 1
            return DebatePosition("Valuation Agent", "GO", 0.7, "Okay", [], call_count["valuation"])

        mock_search_class.return_value.debate_turn = mock_search_turn
        mock_sentiment_class.return_value.debate_turn = mock_sentiment_turn
        mock_valuation_class.return_value.debate_turn = mock_valuation_turn

        orchestrator = DebateOrchestrator(max_rounds=2)

        phase1_map = {
            "Search Agent": MagicMock(content='{"company": {"name": "TestCo"}}'),
            "Sentiment Agent": MagicMock(content='{"sentiment": {}}'),
            "Valuation Agent": MagicMock(content='{"valuation": {}}'),
        }

        rounds, verdict, consensus = orchestrator._run_debate(
            company="TestCo",
            risk_tolerance="risk_neutral",
            phase1_map=phase1_map,
            status_callback=None,
        )

        # Should run 2 rounds then use majority vote
        assert len(rounds) == 2
        assert consensus is False
        # 4 GO votes (2 per round from Search + Valuation), 2 NOGO votes
        assert verdict == "GO"

    def test_status_callback_called(self):
        """Test status_callback is called with progress updates."""
        orchestrator = DebateOrchestrator(max_rounds=1)

        # Mock the debate agents to return consensus immediately
        with patch.multiple(
            "adversarial_debate.orchestrator",
            SearchDebateAgent=MagicMock(),
            SentimentDebateAgent=MagicMock(),
            ValuationDebateAgent=MagicMock(),
        ):
            from adversarial_debate.orchestrator import SearchDebateAgent, SentimentDebateAgent, ValuationDebateAgent

            for mock_cls in [SearchDebateAgent, SentimentDebateAgent, ValuationDebateAgent]:
                mock_agent = MagicMock()
                mock_agent.debate_turn.return_value = DebatePosition(
                    agent_name="Agent", position="GO", confidence=0.8, rationale="Good", challenges=[], round_number=1
                )
                mock_cls.return_value = mock_agent

            phase1_map = {
                "Search Agent": MagicMock(content='{"company": {"name": "TestCo"}}'),
                "Sentiment Agent": MagicMock(content='{"sentiment": {}}'),
                "Valuation Agent": MagicMock(content='{"valuation": {}}'),
            }

            callback_messages = []

            def callback(msg: str) -> None:
                callback_messages.append(msg)

            orchestrator._run_debate(
                company="TestCo",
                risk_tolerance="risk_neutral",
                phase1_map=phase1_map,
                status_callback=callback,
            )

            assert len(callback_messages) > 0
            # Check that we got status messages about the debate round
            assert any("round" in msg.lower() for msg in callback_messages)
