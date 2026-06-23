"""Ad-hoc: run the custom-tool agent against one live model + one case and dump
the rejected first attempt, so we can see WHY validation fails.

    cd test
    PYTHONPATH=../lib:. python evals/capture_custom_tool.py gpt-oss-120b-llmlb boxplot_welch_ttest
"""

import asyncio
import logging
import sys

import yaml
from evals.datasets.custom_tool import _PROTO_CASES
from evals.tasks import make_deps

from galaxy.agents.custom_tool import CustomToolAgent

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logging.getLogger("galaxy.agents.custom_tool").setLevel(logging.DEBUG)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)


def _creds(model: str) -> tuple[str, str]:
    cfg = yaml.safe_load(open("evals/models.yaml"))
    entry = cfg[model]
    return entry["api_key"], entry["proxy_url"]


async def main() -> None:
    model = sys.argv[1] if len(sys.argv) > 1 else "gpt-oss-120b-llmlb"
    case_name = sys.argv[2] if len(sys.argv) > 2 else "boxplot_welch_ttest"
    query = next(c["query"] for c in _PROTO_CASES if c["name"] == case_name)

    api_key, base_url = _creds(model)
    deps = make_deps(model=model, api_key=api_key, base_url=base_url)
    agent = CustomToolAgent(deps)

    print(f"\n=== {model} / {case_name} ===")
    response = await agent.process(query)
    meta = response.metadata or {}
    print(
        f"\nmethod={meta.get('method')} error={meta.get('error')} attempts={(meta.get('agent_data') or {}).get('attempts')}"
    )
    print("\n--- response content ---")
    print(response.content[:3000])


if __name__ == "__main__":
    asyncio.run(main())
