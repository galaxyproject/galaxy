"""Shared pytest fixtures for agent evaluation tests."""
import os
import random
import time

import pytest

from .report_manager import ReportManager


@pytest.fixture(scope="session")
def anthropic_api_key():
    """Get Anthropic API key for judge evaluations."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY environment variable not set for judge")
    return api_key


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "requires_llm: mark test as requiring live LLM (agent + judge)"
    )


@pytest.fixture(scope="session")
def agent_eval_run_id(request):
    """Generate unique run ID for this test session.

    Format: YYYY-MM-DD_HH-MM-SS_<random>_<model_short_name>
    Example: 2026-02-12_23-10-45_3847_sonnet45

    The random suffix prevents collisions when multiple test sessions
    start in the same second (common in CI/CD environments).
    """
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")

    # Add random suffix to prevent timestamp collisions
    random_suffix = random.randint(1000, 9999)

    # Get model name from environment or use default (matches test config defaults)
    model = os.environ.get("GALAXY_TEST_AI_MODEL", "anthropic:claude-haiku-4-5")

    # Extract short model name (e.g., "claude-sonnet-4-5" -> "sonnet45")
    model_short = model.split(":")[-1].replace("claude-", "").replace("-", "").replace(".", "")

    run_id = f"{timestamp}_{random_suffix}_{model_short}"
    return run_id


@pytest.fixture(autouse=True)
def inject_run_id(request, agent_eval_run_id):
    """Inject run_id and test name into test instance for tracking.

    This fixture runs automatically for all tests and makes the run_id
    and test name available as instance attributes.
    """
    if hasattr(request, 'instance') and request.instance is not None:
        request.instance._agent_eval_run_id = agent_eval_run_id
        # Also inject test name from pytest request (Galaxy TestCase doesn't have _testMethodName)
        request.instance._current_test_name = request.node.name


@pytest.fixture(scope="session")
def report_manager(agent_eval_run_id):
    """Create and manage versioned report storage for this test session.

    Yields a ReportManager instance that tests can use to save reports.
    Automatically finalizes (generates summary, updates latest symlink) after all tests complete.
    """
    # Get agent and judge models from environment (must match test config defaults)
    agent_model = os.environ.get("GALAXY_TEST_AI_MODEL", "anthropic:claude-haiku-4-5")
    judge_model = os.environ.get("GALAXY_TEST_JUDGE_MODEL", "claude-opus-4-6")

    # Create ReportManager
    manager = ReportManager(
        run_id=agent_eval_run_id,
        agent_model=agent_model,
        judge_model=judge_model,
        config={
            "tool_source_url": os.environ.get("AGENT_EVAL_TOOL_SOURCE_URL", "https://usegalaxy.org")
        }
    )

    yield manager

    # Finalize after all tests complete
    manager.finalize()


@pytest.fixture(autouse=True)
def inject_report_manager(request, report_manager):
    """Inject report_manager into test instance.

    This fixture runs automatically for all tests and makes the report_manager
    available as self._report_manager in test methods.
    """
    if hasattr(request, 'instance') and request.instance is not None:
        request.instance._report_manager = report_manager
