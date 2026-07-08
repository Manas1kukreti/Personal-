# Quick Start Guide - Testing & LLM-First Routing

## Running the Tests

### Prerequisites
```bash
# Install dependencies
pip install -r requirements.txt
```

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test File
```bash
pytest tests/test_validator.py -v
pytest tests/test_graph_routing.py -v
```

### Run with Coverage
```bash
pytest tests/ --cov=. --cov-report=html
```

### Run Only Unit Tests
```bash
pytest tests/test_validator.py tests/test_financial_logic.py tests/test_field_mapper.py -v
```

### Run Only Integration Tests
```bash
pytest tests/test_graph_routing.py -v
```

## Test Structure

| Test File | Tests | Focus |
|-----------|-------|-------|
| test_config_loader.py | 15 | Configuration loading, caching |
| test_validator.py | 18 | Validation logic, DTCD balancing |
| test_financial_logic.py | 16 | Business rules, account classification |
| test_field_mapper.py | 12 | Field normalization, variant mapping |
| test_graph_routing.py | 17 | LLM-first routing, retry logic |
| test_re_extractor.py | 16 | Field recovery, LLM fallback |

## Using LLM-First Routing

### Basic Usage
```python
from agents.react_agent import choose_validation_route

state = {
    "validation_result": {
        "status": "valid",
        "errors": [],
    },
    "retry_count": 0,
    "max_retries": 5,
}

route = choose_validation_route(state)
# Returns one of: "valid", "push_with_alert", "re_extract", "notify"
```

### With Custom Retry Limit
```python
route = choose_validation_route(state, max_retries=3)
# Will retry LLM up to 3 times before fallback
```

### How It Works
1. **Attempt 1-3**: Try LLM, validate output against allowed routes
2. **Success**: Return valid route from LLM
3. **Invalid Route**: Log warning, retry
4. **All Retries Failed**: Use hardcoded fallback logic

### Routing Logic Flow
```
Input State
    ↓
[LLM Call 1] → Valid? → Return route
    ↓
[LLM Call 2] → Valid? → Return route
    ↓
[LLM Call 3] → Valid? → Return route
    ↓
[Hardcoded Fallback] → Return route
```

## Key Features

### 1. LLM-First Decision Making
The LLM analyzes the validation result and makes routing decisions with full reasoning capability. The LLM considers:
- Validation status (valid/invalid)
- Error types (normal vs DTCD balance errors)
- Retry count vs max retries
- Business context

### 2. 3-Retry Mechanism
If the LLM returns an invalid route:
- Attempt 1: Try LLM with full prompt
- Attempt 2: Retry with enhanced prompt
- Attempt 3: Final retry
- Fallback: Use hardcoded logic

### 3. Allowed Routes
The system only accepts these 4 routes:
- **valid**: Data passed validation, proceed to UI
- **push_with_alert**: DTCD balance errors, push with warning
- **re_extract**: Normal errors, attempt field recovery
- **notify**: Max retries exceeded, notify admin

### 4. Graceful Degradation
Even if all LLM attempts fail:
- System falls back to deterministic logic
- Never breaks data pipeline
- Logs all retry attempts for debugging

## Troubleshooting

### Tests Fail with "GROQ_API_KEY" Error
**Solution**: This should NOT happen - all tests use mocking. If it does:
```bash
# Check if pytest-mock is installed
pip install pytest-mock

# Re-run tests
pytest tests/ -v
```

### Slow Test Execution
The tests are optimized with mocking and should complete in <2 seconds:
```bash
pytest tests/ --durations=10  # Show slowest 10 tests
```

### Import Errors
Ensure you're in the correct directory:
```bash
cd path/to/agentic_Ai
pytest tests/ -v
```

## Extending the Tests

### Add a New Test
```python
# In tests/test_something.py
class TestMyFeature:
    def test_my_case(self):
        """Test description."""
        # Arrange
        data = {...}
        
        # Act
        result = my_function(data)
        
        # Assert
        assert result == expected
```

### Using Fixtures
```python
def test_with_fixture(mock_state):
    """Test using provided fixture."""
    mock_state["retry_count"] = 2
    # ... your test
```

## Performance Notes

- **Test Suite**: ~1.5 seconds for all 91 tests
- **Single Test**: <50ms for most tests
- **No External Calls**: All LLM calls mocked
- **Parallel Execution**: Tests can run in parallel with pytest-xdist

```bash
# Run tests in parallel
pip install pytest-xdist
pytest tests/ -n auto  # Use all CPU cores
```

## Continuous Integration

### GitHub Actions Example
```yaml
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest tests/ -v --tb=short
```

### Pre-commit Hook
```bash
# Install hook
pip install pre-commit

# Create .pre-commit-config.yaml with pytest check
pre-commit install

# Runs tests before each commit
```

## Debugging

### Run with Verbose Output
```bash
pytest tests/test_graph_routing.py::TestValidationRouter::test_valid_data_routes_to_valid -vv
```

### Show Captured Output
```bash
pytest tests/ -v -s  # Shows print statements
```

### Drop into Debugger
```python
def test_my_case():
    import pdb; pdb.set_trace()  # Debugger will stop here
    # ... test code
```

## References

- **ReAct Agents**: LangChain ZERO_SHOT_REACT_DESCRIPTION
- **Routing**: `agents/react_agent.py::choose_validation_route()`
- **Validation**: `agents/validator.py::validate_data()`
- **Tests**: `tests/` directory with 91 tests
