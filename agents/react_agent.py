import json
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError
from langchain_core.output_parsers import BaseOutputParser

from ledgerflow_agent.llm import get_chat_llm
from ledgerflow_agent.prompts import get_agent_prompt
from ledgerflow_agent.tool_policy import filter_langchain_tools

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

DEFAULT_MODEL = "llama-3.3-70b-versatile"


# =========================================================
# ROUTING SCHEMA & PARSER
# =========================================================

class RouteDecision(BaseModel):
    """Schema for validation routing decisions."""
    route: str
    
    model_config = {"validate_assignment": True}


class ValidationRouteParser(BaseOutputParser[str]):
    """Parses and validates routing decisions."""
    
    def parse(self, text: str) -> str:
        allowed_routes = {"valid", "push_with_alert", "re_extract", "notify"}
        route = text.strip().lower()
        
        # Try exact match first
        if route in allowed_routes:
            return route
        
        # Try to extract from common patterns
        for allowed in allowed_routes:
            if allowed in route:
                return allowed
        
        # Default fallback
        return "re_extract"


def get_supervisor_llm():
    return get_chat_llm(model_name=DEFAULT_MODEL, temperature=0.0, max_tokens=512)


class _LangGraphAgentWrapper:
    """
    Thin wrapper around a LangGraph compiled agent graph so the rest of
    the codebase can keep calling  agent.run("...")  unchanged.

    LangChain 1.x removed AgentExecutor entirely; LangGraph's prebuilt
    create_react_agent is the supported replacement.
    """

    def __init__(self, graph, tools: list, verbose: bool = True):
        self._graph = graph
        self._tools = tools
        self._verbose = verbose

    # ── backward-compatible .run() ────────────────────────────────────────
    def run(self, input_text: str) -> str:
        result = self._graph.invoke({"messages": [("human", input_text)]})
        messages = result.get("messages", [])
        if not messages:
            return ""
        last = messages[-1]
        content = last.content if hasattr(last, "content") else str(last)
        if self._verbose:
            print(f"[ReAct] Final answer: {content[:200]}")
        return content

    # ── also support .invoke() for nodes that use that form ──────────────
    def invoke(self, input_val) -> str:
        text = input_val.get("input", str(input_val)) if isinstance(input_val, dict) else str(input_val)
        return self.run(text)


def create_react_agent(agent_name: str = "supervisor"):
    """
    Creates a LangGraph ReAct agent with proper tool selection.

    LangChain >= 1.0 removed langchain.agents entirely.
    We now use langgraph.prebuilt.create_react_agent, which is the
    officially supported replacement and ships with the langgraph package
    already present in this project.

    Args:
        agent_name: Name of the agent for tool scoping

    Returns:
        _LangGraphAgentWrapper (exposes .run() and .invoke())
    """
    from langgraph.prebuilt import create_react_agent as _lg_create_react_agent
    from tools.langchain_tools import ALL_TOOLS

    llm = get_chat_llm(model_name=DEFAULT_MODEL, temperature=0.0, max_tokens=2048)
    scoped_tools = filter_langchain_tools(agent_name, ALL_TOOLS)

    graph = _lg_create_react_agent(llm, scoped_tools)
    return _LangGraphAgentWrapper(graph, scoped_tools, verbose=True)


def choose_validation_route(state, max_retries: int = 3) -> str:
    """
    LLM-first routing decision with retry logic.
    
    The LLM is the sole decision-maker. If it returns an invalid route,
    we retry up to 3 times. Only if all retries fail do we fall back
    to hardcoded logic.
    
    Args:
        state: Agent state containing validation_result and retry_count
        max_retries: Maximum LLM retry attempts (default 3)
        
    Returns:
        One of: "valid", "push_with_alert", "re_extract", "notify"
    """
    validation_result = state.get("validation_result", {})
    retry_count = state.get("retry_count", 0)
    max_graph_retries = state.get("max_retries", 5)
    
    parser = ValidationRouteParser()
    llm = get_supervisor_llm()
    
    for attempt in range(1, max_retries + 1):
        prompt = f"""
{get_agent_prompt("supervisor")}

You are a routing expert. Analyze the validation result and decide which route to take.

VALIDATION RESULT:
{json.dumps(validation_result, indent=2)}

RETRY COUNT: {retry_count}
MAX RETRIES: {max_graph_retries}

DECISION RULES:
1. If validation_result["status"] == "valid", respond: "valid"
2. If there are "not balanced" or "difference" errors (DTCD), respond: "push_with_alert"
3. If there are normal validation errors AND retry_count < {max_graph_retries}, respond: "re_extract"
4. If retry_count >= {max_graph_retries}, respond: "notify"

You MUST respond with EXACTLY ONE of these words:
- valid
- push_with_alert
- re_extract
- notify

NO explanations. NO markdown. Just the route word.
"""
        
        try:
            response = llm.invoke(prompt)
            route = parser.parse(response.content)
            print(f"✓ LLM Routing (Attempt {attempt}/{max_retries}): {route}")
            return route
        except Exception as e:
            print(f"⚠ Routing attempt {attempt}/{max_retries} failed: {e}")
            if attempt == max_retries:
                print(f"⚠ All {max_retries} LLM attempts failed. Using fallback logic.")
                break
    
    # Fallback to hardcoded logic only after all retries fail
    if validation_result.get("status") == "valid":
        return "valid"
    
    errors = validation_result.get("errors", [])
    has_dtcd_errors = any(
        "not balanced" in str(e.get("error", "")).lower() or 
        "difference" in str(e.get("error", "")).lower()
        for e in errors
    )
    
    if has_dtcd_errors:
        return "push_with_alert"
    
    if errors and retry_count < max_graph_retries:
        return "re_extract"
    
    return "notify"


def run_react_pipeline():
    agent = create_react_agent("input")
    response = agent.run(
        "Fetch the latest financial email, read and preprocess the financial data, "
        "extract structured transactions, validate them using accounting rules, "
        "and push valid data to frontend dashboard."
    )
    return response


if __name__ == "__main__":
    response = run_react_pipeline()
    print("\nFINAL OUTPUT:\n")
    print(response)