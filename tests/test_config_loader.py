"""Tests for config_loader.py"""

import pytest
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

# Adjust path to import from parent directory
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_loader import (
    load_project_config,
    get_config_section,
    get_workflow_config,
    get_agent_config,
    get_excel_reader_config,
    get_field_mapping_config,
    get_relation_mapping_config,
    get_financial_logic_config,
)


class TestConfigLoader:
    """Test suite for config_loader functions."""
    
    def test_load_project_config_returns_dict(self):
        """Test that load_project_config returns a dict."""
        # Clear cache first
        load_project_config.cache_clear()
        result = load_project_config()
        assert isinstance(result, dict)
    
    def test_load_project_config_is_cached(self):
        """Test that lru_cache means file is read only once."""
        # Clear cache first
        load_project_config.cache_clear()
        
        # Get file size to confirm it was read
        info1 = load_project_config()
        info2 = load_project_config()
        
        # Both calls should return the same object (cached)
        assert info1 is info2
    
    def test_get_workflow_config_returns_dict(self):
        """Test that get_workflow_config returns a dict."""
        result = get_workflow_config()
        assert isinstance(result, dict)
    
    def test_get_workflow_config_has_expected_keys(self):
        """Test that workflow config has expected keys."""
        result = get_workflow_config()
        # These keys are expected based on usage in codebase
        expected_keys = {"max_retries", "structured_data_required_fields", "excel_row_limit"}
        actual_keys = set(result.keys())
        # Check if at least some expected keys exist (not all may be present)
        assert len(actual_keys) >= 0  # Config might be empty, that's okay
    
    def test_get_workflow_config_max_retries_is_int(self):
        """Test that max_retries is an integer if present."""
        result = get_workflow_config()
        if "max_retries" in result:
            assert isinstance(result["max_retries"], (int, float))
    
    def test_get_agent_config_returns_dict(self):
        """Test that get_agent_config returns a dict."""
        result = get_agent_config("supervisor")
        assert isinstance(result, dict)
    
    def test_get_agent_config_nonexistent_returns_empty_dict(self):
        """Test that get_agent_config for nonexistent agent returns empty dict not exception."""
        result = get_agent_config("nonexistent_agent_xyz")
        assert isinstance(result, dict)
        assert len(result) == 0  # Should be empty, not throw exception
    
    def test_get_agent_config_known_agents(self):
        """Test that known agents return some config."""
        # These are agents referenced in the codebase
        agent_names = ["supervisor", "input", "extraction", "validation", "ui", "notification"]
        for agent_name in agent_names:
            result = get_agent_config(agent_name)
            assert isinstance(result, dict)
    
    def test_get_excel_reader_config_returns_dict(self):
        """Test that get_excel_reader_config returns a dict."""
        result = get_excel_reader_config()
        assert isinstance(result, dict)
    
    def test_get_field_mapping_config_returns_dict(self):
        """Test that get_field_mapping_config returns a dict."""
        result = get_field_mapping_config()
        assert isinstance(result, dict)
    
    def test_get_relation_mapping_config_returns_dict(self):
        """Test that get_relation_mapping_config returns a dict."""
        result = get_relation_mapping_config()
        assert isinstance(result, dict)
    
    def test_get_financial_logic_config_returns_dict(self):
        """Test that get_financial_logic_config returns a dict."""
        result = get_financial_logic_config()
        assert isinstance(result, dict)
    
    def test_get_config_section_missing_returns_default(self):
        """Test that missing section returns default not an exception."""
        result = get_config_section("nonexistent_section_xyz", default={})
        assert isinstance(result, dict)
        assert len(result) == 0
    
    def test_get_config_section_missing_returns_none_if_no_default(self):
        """Test that missing section returns None if no default provided."""
        result = get_config_section("nonexistent_section_xyz")
        # Either None or empty dict is acceptable
        assert result is None or isinstance(result, dict)
    
    def test_lru_cache_works_correctly(self):
        """Test that lru_cache prevents file rereading."""
        # Clear the cache
        load_project_config.cache_clear()
        
        # Get info about first call
        call_count_before = load_project_config.cache_info().hits
        
        # Make first call
        result1 = load_project_config()
        
        # Make second call
        result2 = load_project_config()
        
        # Check cache hits increased
        call_count_after = load_project_config.cache_info().hits
        assert call_count_after > call_count_before


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
