from __future__ import annotations

import json

from ledgerflow_agent import run_ledgerflow_agent_dynamic


def main() -> None:
    result = run_ledgerflow_agent_dynamic({"retry_count": 0})
    final_output = result.get("final_output", result)

    print("\nLEDGERFLOW AGENT FINISHED\n")
    print(json.dumps(final_output, indent=2, default=str))


if __name__ == "__main__":
    main()
