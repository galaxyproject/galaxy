"""Evaluate ToolRecommendation agent's accuracy for tool suggestions."""
import json
import os
import time
from pathlib import Path

import pytest

from galaxy_test.driver.integration_util import IntegrationTestCase
from .eval_utils import calculate_model_cost


pytestmark = pytest.mark.requires_llm


class TestToolRecommendationAccuracy(IntegrationTestCase):
    """Test tool recommendation quality."""

    def setUp(self):
        super().setUp()
        self._test_start_time = time.time()
        self._test_metrics = {}
        # Capture test metadata for categorization
        # (test name is injected by conftest.py fixture)
        self._test_category = self.__class__.__module__.split('.')[-1].replace('test_', '')
        self._test_class = self.__class__.__name__

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        """Configure Galaxy with AI agent settings."""
        # Use useGalaxy.org tools for realistic tool recommendations
        config["agent_eval_tool_source_url"] = "https://usegalaxy.org"

        # Set AI model (from env var or default to Claude Haiku 4.5)
        config["ai_model"] = os.environ.get("GALAXY_TEST_AI_MODEL", "anthropic:claude-haiku-4-5")

        # Set AI API key if provided
        if ai_api_key := os.environ.get("GALAXY_TEST_AI_API_KEY"):
            config["ai_api_key"] = ai_api_key

    @pytest.mark.asyncio
    async def test_recommends_fastqc_for_qc(self):
        """Should recommend FastQC for quality control."""
        prompt = "I need to check the quality of my FASTQ files. What tool should I use?"

        start_time = time.time()
        response = self._post(
            "/api/ai/agents/query", data={"query": prompt, "agent_type": "tool_recommendation"}, json=True
        )
        query_duration = time.time() - start_time

        result = response.json()
        content = result["response"]["content"].lower()

        # Store metrics
        self._test_metrics.update({
            "query_duration_ms": int(query_duration * 1000),
            "prompt": prompt,
            "agent_response": result["response"]["content"],
            "expected_tool": "fastqc"
        })

        # Extract token usage from API response if available
        if "usage" in result:
            self._test_metrics["agent_tokens_input"] = result["usage"].get("input_tokens", 0)
            self._test_metrics["agent_tokens_output"] = result["usage"].get("output_tokens", 0)

        # Should mention FastQC
        assert "fastqc" in content or "fast qc" in content

    @pytest.mark.asyncio
    async def test_recommends_alignment_tools(self):
        """Should recommend alignment tools for mapping."""
        prompt = "I need to align RNA-seq reads to a reference genome."

        start_time = time.time()
        response = self._post(
            "/api/ai/agents/query", data={"query": prompt, "agent_type": "tool_recommendation"}, json=True
        )
        query_duration = time.time() - start_time

        result = response.json()
        content = result["response"]["content"].lower()

        # Store metrics
        self._test_metrics.update({
            "query_duration_ms": int(query_duration * 1000),
            "prompt": prompt,
            "agent_response": result["response"]["content"],
            "expected_tools": ["hisat2", "star", "bowtie", "bwa"]
        })

        # Extract token usage from API response if available
        if "usage" in result:
            self._test_metrics["agent_tokens_input"] = result["usage"].get("input_tokens", 0)
            self._test_metrics["agent_tokens_output"] = result["usage"].get("output_tokens", 0)

        # Should mention common aligners
        alignment_tools = ["hisat2", "star", "bowtie", "bwa"]
        assert any(tool in content for tool in alignment_tools)

    def _save_test_report(self, test_name: str, status: str, error_message: str = None):
        """Save test results as JSON report for dashboard."""
        reports_dir = Path("test-reports")
        reports_dir.mkdir(exist_ok=True)

        duration_ms = int((time.time() - self._test_start_time) * 1000)

        # Extract token counts (if available - tool recommendation tests may not have judge tokens)
        agent_tokens_in = self._test_metrics.get('agent_tokens_input', 0)
        agent_tokens_out = self._test_metrics.get('agent_tokens_output', 0)
        judge_tokens_in = self._test_metrics.get('judge_tokens_input', 0)
        judge_tokens_out = self._test_metrics.get('judge_tokens_output', 0)

        # Get model names for cost calculation
        agent_model = getattr(self._app.config, 'ai_model', 'claude-sonnet-4-5')
        judge_model = self._test_metrics.get('judge_model', 'claude-opus-4-6')

        # Calculate costs using pricing utility
        agent_cost = calculate_model_cost(agent_model, agent_tokens_in, agent_tokens_out)
        judge_cost = calculate_model_cost(judge_model, judge_tokens_in, judge_tokens_out)
        total_cost = agent_cost + judge_cost

        # Build report with both legacy fields (for dashboard compatibility) and detailed metrics
        report = {
            # Test identity
            "test_name": test_name,
            "test_class": getattr(self, '_test_class', 'Unknown'),
            "test_category": getattr(self, '_test_category', 'unknown'),
            "test_file": "test_tool_recommendations.py",
            # Run context
            "run_id": getattr(self, '_agent_eval_run_id', 'unknown'),
            "agent_model": agent_model,
            "judge_model": judge_model,
            "tool_source_url": getattr(self._app.config, 'agent_eval_tool_source_url', None),
            # Test execution
            "status": status,
            "duration_ms": duration_ms,
            "timestamp": time.time(),
            # Legacy fields for current dashboard compatibility
            "tokens_input": agent_tokens_in + judge_tokens_in,
            "tokens_output": agent_tokens_out + judge_tokens_out,
            "cost": total_cost,
            **self._test_metrics
        }

        if error_message:
            report["error"] = error_message

        # Add detailed metrics breakdown
        report["detailed_metrics"] = {
            "agent_tokens": {"input": agent_tokens_in, "output": agent_tokens_out},
            "judge_tokens": {"input": judge_tokens_in, "output": judge_tokens_out},
            "costs": {
                "agent_cost": agent_cost,
                "judge_cost": judge_cost,
                "total_cost": total_cost
            }
        }

        # Save to legacy location (test-reports/) for backward compatibility
        report_file = reports_dir / f"{test_name}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        # Save to versioned storage using ReportManager
        if hasattr(self, '_report_manager'):
            category = report.get('test_category', 'unknown')
            self._report_manager.save_report(category, test_name, report)

    def tearDown(self):
        """Save test report after each test."""
        test_name = getattr(self, '_current_test_name', 'unknown_test')

        status = "PASSED"
        error_msg = None

        if hasattr(self, "_outcome"):
            result = self._outcome.result
            if result.failures or result.errors:
                status = "FAILED"
                if result.failures:
                    error_msg = str(result.failures[-1][1])
                elif result.errors:
                    error_msg = str(result.errors[-1][1])

        # Also check quality score if available
        if status == "PASSED" and "quality_score" in self._test_metrics and "min_score" in self._test_metrics:
            quality_score = self._test_metrics["quality_score"]
            min_score = self._test_metrics["min_score"]
            if quality_score < min_score:
                status = "FAILED"
                error_msg = f"Quality score {quality_score} below threshold {min_score}"

        self._save_test_report(test_name, status, error_msg)
        super().tearDown()
