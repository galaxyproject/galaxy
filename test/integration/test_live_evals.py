"""Live-Galaxy runner for the ``test/evals/`` agent eval suite.

Wraps the standalone ``evals.run_evals`` machinery inside a Galaxy
integration-test fixture so the ``requires_galaxy=True`` cases (the
staining quantification history sanity check, summarize-to-page, report
takeaway, social media post, plus the history_analyzer routing cases)
actually run against a real history.

The mock-trans CLI under ``test/evals/run_evals.py`` stays the fast
loop for prompt iteration on the cases that don't need live data. This
test is the real flight check before demo rehearsals -- it shares
dataset definitions, evaluators, and the report renderer with the CLI,
only the deps construction differs.

## Running

    export GALAXY_TEST_ENABLE_LIVE_LLM=1
    export GALAXY_TEST_LIVE_EVALS=1
    # Either inline AI config:
    export GALAXY_TEST_AI_API_KEY="..."
    export GALAXY_TEST_AI_API_BASE_URL="http://localhost:4000/v1/"
    export GALAXY_TEST_AI_MODEL="gpt-oss-120b"
    # Or point at a models.yaml that's structured for the eval CLI:
    export EVALS_MODEL_CONFIG=/path/to/models.yaml
    export EVALS_MODELS="gpt-oss-120b"      # optional comma-separated subset
    export EVALS_JUDGE_MODEL="..."          # optional override; defaults to
                                            # Llama-4-Maverick-17B-128E-Instruct
                                            # so the candidate isn't judging
                                            # its own output
    export EVALS_DATASETS="staining_quantification"   # optional comma-separated subset

    pytest test/integration/test_live_evals.py -v

Reports land in ``test/evals/results/<stamp>-<datasets>-<sha>.{md,json}``,
the same place and naming as the CLI so ``--baseline`` diffing keeps
working across both runners.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

import pytest

from galaxy.util.unittest_utils import pytestmark_live_llm
from galaxy.work.context import WorkRequestContext
from galaxy_test.base.populators import (
    DatasetPopulator,
    WorkflowPopulator,
)
from galaxy_test.driver.integration_util import IntegrationTestCase

# test/evals/ isn't an installable package -- put test/ on sys.path so the
# `evals.*` modules import cleanly without an editable install or an
# __init__.py at test/.
_TEST_ROOT = Path(__file__).resolve().parents[1]
if str(_TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(_TEST_ROOT))

from evals.run_evals import (  # noqa: E402
    _load_model_config,
    run_eval_suite,
    write_eval_report,
)
from evals.seed_staining_quantification_history import seed_demo_history  # noqa: E402
from evals.tasks import make_live_deps  # noqa: E402

log = logging.getLogger(__name__)

pytestmark_live_evals = pytest.mark.skipif(
    not os.environ.get("GALAXY_TEST_LIVE_EVALS"),
    reason="Set GALAXY_TEST_LIVE_EVALS=1 to run the live-Galaxy eval suite.",
)


@pytestmark_live_llm
@pytestmark_live_evals
class TestLiveEvals(IntegrationTestCase):
    """Run evals/datasets/* against a real Galaxy with a seeded demo history."""

    dataset_populator: DatasetPopulator
    workflow_populator: WorkflowPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        # Same env-var wiring as test_agents.py so this test can reuse a
        # configured LLM if one's already set up.
        if ai_api_key := os.environ.get("GALAXY_TEST_AI_API_KEY"):
            config["ai_api_key"] = ai_api_key
        if ai_api_base_url := os.environ.get("GALAXY_TEST_AI_API_BASE_URL"):
            config["ai_api_base_url"] = ai_api_base_url
        if ai_model := os.environ.get("GALAXY_TEST_AI_MODEL"):
            config["ai_model"] = ai_model

    def test_run_live_eval_suite(self):
        """Seed the demo history, run the eval suite, write reports.

        Default scope: ``staining_quantification`` dataset with
        ``--include-galaxy-required`` so the cases that need a real
        history actually run. Override via the ``EVALS_*`` env vars
        documented at the top of the file.
        """
        history_id = seed_demo_history(self.dataset_populator)
        log.info("Seeded staining quantification fixture history: %s", history_id)

        datasets = [
            d.strip() for d in os.environ.get("EVALS_DATASETS", "staining_quantification").split(",") if d.strip()
        ]

        config_path = os.environ.get("EVALS_MODEL_CONFIG")
        _path, model_config = _load_model_config(config_path)

        if env_models := os.environ.get("EVALS_MODELS"):
            models = [m.strip() for m in env_models.split(",") if m.strip()]
        else:
            models = list(model_config.keys())

        # Default to a different judge than the candidate model. gpt-oss-120b
        # is the typical candidate (the free Jetstream-backed default) and
        # tends to be too charitable when judging its own output; Maverick
        # scores hand-graded "obviously correct" responses more accurately.
        # Override with EVALS_JUDGE_MODEL if Maverick isn't reachable.
        judge_model_name = os.environ.get("EVALS_JUDGE_MODEL", "Llama-4-Maverick-17B-128E-Instruct")

        # Build a real trans bound to the test user, then close over it in
        # the deps factory so every (dataset, model) pair sees the same
        # seeded history.
        #
        # The history agent's tools call trans.url_for(...) to encode dataset
        # references, which raises NotImplementedError without a url_builder.
        # MCP solves this with a fallback URL builder for non-HTTP contexts --
        # reuse it here so history_sanity_check / summarize_to_page don't
        # ERROR out before the agent's response is even scored.
        from galaxy.webapps.galaxy.api.mcp import get_mcp_url_builder

        api_key = self.galaxy_interactor.api_key
        assert api_key, "Test setup must provide a galaxy_interactor.api_key"
        user = self._user_for_api_key(api_key)
        history = self._history_for_id(history_id)
        url_builder = get_mcp_url_builder(self.url)
        trans = WorkRequestContext(app=self._app, user=user, history=history, url_builder=url_builder)

        def _live_deps_factory(model: str, api_key: str, base_url: str):
            return make_live_deps(trans=trans, model=model, api_key=api_key, base_url=base_url)

        results = asyncio.run(
            run_eval_suite(
                datasets=datasets,
                models=models,
                model_config=model_config,
                judge_model_name=judge_model_name,
                deps_factory=_live_deps_factory,
                include_galaxy_required=True,
            )
        )

        results_dir = _TEST_ROOT / "evals" / "results"
        md_path, json_path = write_eval_report(results, datasets, results_dir)
        log.info("Wrote live eval report: %s", md_path)
        log.info("Wrote live eval JSON sidecar: %s", json_path)

        # Don't assert per-case scores here -- the harness is a measurement
        # tool, not a pass/fail gate. The report file is the artifact.
        assert results, "Expected at least one (dataset, model) result"

    def _user_for_api_key(self, api_key: str):
        user_id = self._user_id_for_api_key(api_key)
        return self._app.model.session.get(self._app.model.User, user_id)

    def _history_for_id(self, history_id: str):
        decoded = self._decode_id(history_id)
        return self._app.model.session.get(self._app.model.History, decoded)
