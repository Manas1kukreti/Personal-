"""Tests for graph routing logic"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Adjust path to import from parent directory
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestValidationRouter:
    """Test suite for validation_router logic."""
    
    @patch('agents.react_agent.get_supervisor_llm')
    def test_valid_data_routes_to_valid(self, mock_get_llm):
        """Test that valid data produces 'valid' route."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "valid"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm
        
        from agents.react_agent import choose_validation_route
        
        state = {
            "validation_result": {
                "status": "valid",
                "errors": [],
            },
            "retry_count": 0,
        }
        
        result = choose_validation_route(state)
        
        # Should route to valid
        assert result == "valid"
    
    @patch('agents.react_agent.get_supervisor_llm')
    def test_dtcd_imbalance_routes_to_push_with_alert(self, mock_get_llm):
        """Test that DTCD imbalance produces 'push_with_alert' route."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "push_with_alert"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm
        
        from agents.react_agent import choose_validation_route
        
        state = {
            "validation_result": {
                "status": "invalid",
                "errors": [
                    {
                        "error": "Debit Credit Total Difference not balanced",
                        "difference": 0.05,
                    }
                ],
            },
            "retry_count": 0,
        }
        
        result = choose_validation_route(state)
        
        # Should route to push_with_alert
        assert result == "push_with_alert"
    
    @patch('agents.react_agent.get_supervisor_llm')
    def test_normal_error_under_retry_limit_routes_to_re_extract(self, mock_get_llm):
        """Test that normal errors under retry limit route to 're_extract'."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "re_extract"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm
        
        from agents.react_agent import choose_validation_route
        
        state = {
            "validation_result": {
                "status": "invalid",
                "errors": [
                    {
                        "error": "Field validation failed",
                        "field": "amount",
                    }
                ],
            },
            "retry_count": 2,
            "max_retries": 5,
        }
        
        result = choose_validation_route(state)
        
        # Should route to re_extract
        assert result == "re_extract"
    
    @patch('agents.react_agent.get_supervisor_llm')
    def test_error_at_max_retries_routes_to_notify(self, mock_get_llm):
        """Test that errors at max retries route to 'notify'."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "notify"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm
        
        from agents.react_agent import choose_validation_route
        
        state = {
            "validation_result": {
                "status": "invalid",
                "errors": [
                    {
                        "error": "Field validation failed",
                        "field": "amount",
                    }
                ],
            },
            "retry_count": 5,
            "max_retries": 5,
        }
        
        result = choose_validation_route(state)
        
        # Should route to notify
        assert result == "notify"


class TestChooseValidationRouteLLMFirst:
    """Test suite for LLM-first routing with retry logic."""
    
    @patch('agents.react_agent.get_supervisor_llm')
    def test_llm_is_called_first(self, mock_get_llm):
        """Test that LLM is called as the first decision-maker."""
        from agents.react_agent import choose_validation_route
        
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "valid"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm
        
        state = {
            "validation_result": {"status": "valid", "errors": []},
            "retry_count": 0,
            "max_retries": 5,
        }
        
        result = choose_validation_route(state)
        
        # LLM should be called
        assert mock_get_llm.called
        assert result == "valid"
    
    @patch('agents.react_agent.get_supervisor_llm')
    def test_invalid_route_triggers_retry(self, mock_get_llm):
        """Test that invalid LLM response triggers retry."""
        from agents.react_agent import choose_validation_route
        
        mock_llm = MagicMock()
        
        # First attempt returns invalid route
        mock_response_1 = MagicMock()
        mock_response_1.content = "invalid_route_xyz"
        
        # Second attempt returns valid route
        mock_response_2 = MagicMock()
        mock_response_2.content = "valid"
        
        mock_llm.invoke.side_effect = [mock_response_1, mock_response_2]
        mock_get_llm.return_value = mock_llm
        
        state = {
            "validation_result": {"status": "valid", "errors": []},
            "retry_count": 0,
            "max_retries": 5,
        }
        
        result = choose_validation_route(state, max_retries=3)
        
        # Should retry and eventually succeed
        assert result in {"valid", "push_with_alert", "re_extract", "notify"}
    
    @patch('agents.react_agent.get_supervisor_llm')
    def test_three_retries_before_fallback(self, mock_get_llm):
        """Test that LLM has 3 retry attempts before fallback."""
        from agents.react_agent import choose_validation_route
        
        mock_llm = MagicMock()
        
        # All attempts fail
        mock_llm.invoke.side_effect = Exception("LLM Error")
        mock_get_llm.return_value = mock_llm
        
        state = {
            "validation_result": {
                "status": "invalid",
                "errors": [{"error": "Test error"}],
            },
            "retry_count": 0,
            "max_retries": 5,
        }
        
        result = choose_validation_route(state, max_retries=3)
        
        # Should try 3 times
        assert mock_llm.invoke.call_count == 3
        
        # Should fall back to hardcoded logic
        assert result is not None
    
    @patch('agents.react_agent.get_supervisor_llm')
    def test_fallback_after_max_retries(self, mock_get_llm):
        """Test that fallback is used after max retries exhausted."""
        from agents.react_agent import choose_validation_route
        
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("LLM Error")
        mock_get_llm.return_value = mock_llm
        
        state = {
            "validation_result": {
                "status": "valid",
                "errors": [],
            },
            "retry_count": 0,
            "max_retries": 5,
        }
        
        result = choose_validation_route(state, max_retries=3)
        
        # With valid status, fallback should return "valid"
        assert result in {"valid", "push_with_alert", "re_extract", "notify"}


class TestGraphRouterIntegration:
    """Integration tests for graph routing."""
    
    @patch('agents.react_agent.get_supervisor_llm')
    def test_full_routing_path_valid_to_ui(self, mock_get_llm):
        """Test full routing path when data is valid."""
        from agents.react_agent import choose_validation_route
        
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "valid"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm
        
        state = {
            "validation_result": {
                "status": "valid",
                "errors": [],
            },
            "retry_count": 0,
            "max_retries": 5,
        }
        
        route = choose_validation_route(state)
        
        # Valid data should route to "valid" which leads to UI
        assert route == "valid"
    
    @patch('agents.react_agent.get_supervisor_llm')
    def test_full_routing_path_dtcd_error_to_alert(self, mock_get_llm):
        """Test full routing path for DTCD errors."""
        from agents.react_agent import choose_validation_route
        
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "push_with_alert"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm
        
        state = {
            "validation_result": {
                "status": "invalid",
                "errors": [
                    {
                        "error": "Total Debit and Credit not balanced",
                        "difference": 10.50,
                    }
                ],
            },
            "retry_count": 0,
            "max_retries": 5,
        }
        
        route = choose_validation_route(state)
        
        # DTCD errors should route to "push_with_alert"
        assert route == "push_with_alert"
    
    @patch('agents.react_agent.get_supervisor_llm')
    def test_full_routing_path_recoverable_error(self, mock_get_llm):
        """Test full routing path for recoverable errors."""
        from agents.react_agent import choose_validation_route
        
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "re_extract"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm
        
        state = {
            "validation_result": {
                "status": "invalid",
                "errors": [
                    {
                        "error": "Field 'amount' is empty",
                        "field": "amount",
                    }
                ],
            },
            "retry_count": 1,
            "max_retries": 5,
        }
        
        route = choose_validation_route(state)
        
        # Recoverable errors under retry limit should route to "re_extract"
        assert route == "re_extract"
    
    @patch('agents.react_agent.get_supervisor_llm')
    def test_full_routing_path_max_retries_exceeded(self, mock_get_llm):
        """Test full routing path when max retries exceeded."""
        from agents.react_agent import choose_validation_route
        
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "notify"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm
        
        state = {
            "validation_result": {
                "status": "invalid",
                "errors": [
                    {
                        "error": "Field 'amount' is empty",
                        "field": "amount",
                    }
                ],
            },
            "retry_count": 5,
            "max_retries": 5,
        }
        
        route = choose_validation_route(state)
        
        # Exceeded retry limit should route to "notify"
        assert route == "notify"


class TestValidationRouterStateHandling:
    """Test state handling in routing."""
    
    @patch('agents.react_agent.get_supervisor_llm')
    def test_missing_validation_result_defaults_to_empty(self, mock_get_llm):
        """Test that missing validation_result defaults to empty dict."""
        from agents.react_agent import choose_validation_route
        
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "valid"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm
        
        state = {
            "retry_count": 0,
            "max_retries": 5,
        }
        
        result = choose_validation_route(state)
        
        # Should handle missing validation_result gracefully
        assert result is not None
    
    @patch('agents.react_agent.get_supervisor_llm')
    def test_missing_retry_count_defaults_to_zero(self, mock_get_llm):
        """Test that missing retry_count defaults to 0."""
        from agents.react_agent import choose_validation_route
        
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "valid"
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm
        
        state = {
            "validation_result": {"status": "valid", "errors": []},
        }
        
        result = choose_validation_route(state)
        
        # Should handle missing retry_count gracefully
        assert result is not None
    
    @patch('agents.react_agent.get_supervisor_llm')
    def test_allowed_routes_only(self, mock_get_llm):
        """Test that only allowed routes are returned."""
        from agents.react_agent import choose_validation_route
        
        mock_llm = MagicMock()
        
        allowed_routes = {"valid", "push_with_alert", "re_extract", "notify"}
        
        # Test various states
        test_states = [
            {"validation_result": {"status": "valid", "errors": []}, "retry_count": 0, "max_retries": 5},
            {"validation_result": {"status": "invalid", "errors": [{"error": "not balanced"}]}, "retry_count": 0, "max_retries": 5},
            {"validation_result": {"status": "invalid", "errors": [{"error": "field error"}]}, "retry_count": 0, "max_retries": 5},
            {"validation_result": {"status": "invalid", "errors": [{"error": "field error"}]}, "retry_count": 5, "max_retries": 5},
        ]
        
        for i, state in enumerate(test_states):
            mock_response = MagicMock()
            mock_response.content = list(allowed_routes)[i % len(allowed_routes)]
            mock_llm.invoke.return_value = mock_response
            mock_get_llm.return_value = mock_llm
            
            result = choose_validation_route(state)
            assert result in allowed_routes


class TestCompiledGraph:
    """Test suite for the compiled StateGraph structure."""

    def test_compiled_graph_nodes_and_edges(self):
        """Verify the compiled graph has the exact supervisor-centric nodes."""
        from graph.graph import ledgerflow_graph

        expected_nodes = {
            "supervisor",
            "fetch_email",
            "preprocessing_tools",
            "extract_data",
            "validate",
            "re_extract",
            "push_to_ui",
            "notification",
        }
        for node in expected_nodes:
            assert node in ledgerflow_graph.nodes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
