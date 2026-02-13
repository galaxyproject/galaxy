"""Agent evaluation tests for bioinformatics workflows.

Tests Galaxy AI agents (Router, ToolRecommendation, Orchestrator) with
real-world bioinformatics use cases:
- Single-cell RNA-seq cell type identification
- Bulk RNA-seq differential expression
- QC triage for problematic FastQC results
- Low mapping rate troubleshooting
- Metagenomics community composition
- Somatic variant calling
- General onboarding guidance
- Coverage anomalies and artifacts

Uses mcp-eval's evaluation framework with LLM judges to assess response quality.
"""
import json
import os
import time
from pathlib import Path

import pytest

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver.integration_util import IntegrationTestCase
from .eval_utils import calculate_model_cost


# Requires live LLM for evaluation
pytestmark = pytest.mark.requires_llm


class TestBioinformaticsWorkflowEvals(IntegrationTestCase):
    """Evaluate agent responses for bioinformatics workflows."""

    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self._test_start_time = time.time()
        self._test_metrics = {}
        # Capture test metadata for categorization
        # (test name is injected by conftest.py fixture)
        self._test_category = self.__class__.__module__.split('.')[-1].replace('test_', '')
        self._test_class = self.__class__.__name__

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        """Configure Galaxy with AI agent settings."""
        # Use useGalaxy.org tools for realistic tool recommendations in evaluation tests
        config["agent_eval_tool_source_url"] = "https://usegalaxy.org"

        # Set AI model (from env var or default to Claude Haiku 4.5)
        config["ai_model"] = os.environ.get("GALAXY_TEST_AI_MODEL", "anthropic:claude-haiku-4-5")

        # Set AI API key if provided
        if ai_api_key := os.environ.get("GALAXY_TEST_AI_API_KEY"):
            config["ai_api_key"] = ai_api_key

    @pytest.mark.asyncio
    async def test_scrna_cell_type_identification(self):
        """7.1 Single-cell RNA-seq: Identify cell types.

        Goal: Evaluate scRNA-seq reasoning (clustering → marker genes → annotation).
        """
        prompt = (
            "I just got my single-cell RNA-seq count matrix back. "
            "How can I figure out what cell types are present?"
        )

        response = await self._query_router(prompt)

        # Evaluation using LLM judge
        quality_score = await self._evaluate_response(
            response=response,
            rubric=(
                "Response should mention:\n"
                "1. Clustering algorithms (Louvain, Leiden, UMAP/tSNE for visualization)\n"
                "2. Marker gene identification (differential expression between clusters)\n"
                "3. Cell type annotation (manual or automated using reference databases)\n"
                "4. Relevant Galaxy tools (Scanpy, Seurat wrapper tools if available)\n"
                "5. General workflow: QC → normalization → clustering → marker genes → annotation"
            ),
            min_score=0.7,
        )

        assert quality_score >= 0.7, f"Response quality too low: {quality_score}"

    @pytest.mark.asyncio
    async def test_bulk_rnaseq_differential_expression(self):
        """7.2 Bulk RNA-seq: Differential expression.

        Goal: Verify the agent describes a proper DE pipeline.
        """
        prompt = (
            "I have RNA-seq FASTQ files from two conditions. "
            "How do I identify differentially expressed genes between them?"
        )

        response = await self._query_router(prompt)

        quality_score = await self._evaluate_response(
            response=response,
            rubric=(
                "Response should outline:\n"
                "1. QC step (FastQC)\n"
                "2. Alignment/quantification (HISAT2, STAR, or Salmon/kallisto)\n"
                "3. Count aggregation (featureCounts, HTSeq-count)\n"
                "4. Differential expression analysis (DESeq2, edgeR, limma)\n"
                "5. Mention of replicates and experimental design importance\n"
                "6. Optional: Functional enrichment analysis (GO, KEGG)"
            ),
            min_score=0.7,
        )

        assert quality_score >= 0.7, f"Response quality too low: {quality_score}"

    @pytest.mark.asyncio
    async def test_qc_triage_fastqc(self):
        """7.3 QC triage: Problematic FastQC results.

        Goal: Evaluate reasoning on QC-based preprocessing.
        """
        prompt = (
            "My FastQC reports show poor quality at the ends and clear adapter contamination. "
            "What should I do next to clean up the data?"
        )

        response = await self._query_router(prompt)

        quality_score = await self._evaluate_response(
            response=response,
            rubric=(
                "Response should recommend:\n"
                "1. Adapter trimming (Cutadapt, Trim Galore, Trimmomatic)\n"
                "2. Quality trimming (remove low-quality bases at ends)\n"
                "3. Re-run FastQC after trimming to verify improvement\n"
                "4. Specific Galaxy tools for trimming\n"
                "5. Optional: Explanation of quality scores and adapter contamination"
            ),
            min_score=0.7,
        )

        assert quality_score >= 0.7, f"Response quality too low: {quality_score}"

    @pytest.mark.asyncio
    async def test_low_mapping_rate_troubleshooting(self):
        """7.4 Low mapping rate troubleshooting.

        Goal: Test diagnostic insight for alignment problems.
        """
        prompt = (
            "My reads only mapped at about 50%. "
            "What could be causing the low mapping rate, and how can I figure out what's wrong?"
        )

        response = await self._query_router(prompt)

        quality_score = await self._evaluate_response(
            response=response,
            rubric=(
                "Response should suggest investigating:\n"
                "1. Wrong reference genome (species mismatch)\n"
                "2. Adapter/quality issues (check FastQC)\n"
                "3. Contamination (run FastQ Screen or Kraken)\n"
                "4. rRNA contamination (if RNA-seq)\n"
                "5. Library type issues (stranded vs unstranded)\n"
                "6. Diagnostic tools: FastQ Screen, Kraken2, BLAST unmapped reads"
            ),
            min_score=0.7,
        )

        assert quality_score >= 0.7, f"Response quality too low: {quality_score}"

    @pytest.mark.asyncio
    async def test_metagenomics_community_composition(self):
        """7.5 Metagenomics: Identify community composition.

        Goal: Test reasoning about taxonomic profiling + assembly + binning.
        """
        prompt = (
            "I have shotgun metagenomic sequencing data from a soil sample. "
            "How can I figure out what organisms are present and their relative abundances?"
        )

        response = await self._query_router(prompt)

        quality_score = await self._evaluate_response(
            response=response,
            rubric=(
                "Response should mention:\n"
                "1. Taxonomic profiling (Kraken2, MetaPhlAn, Kaiju for quick abundance estimates)\n"
                "2. Assembly-based approach (MEGAHIT, metaSPAdes for contigs)\n"
                "3. Binning (MaxBin, MetaBAT to group contigs into MAGs)\n"
                "4. Annotation of bins (CheckM for quality, prokka/DRAM for genes)\n"
                "5. Trade-offs: profiling (fast) vs assembly (detailed)\n"
                "6. Galaxy tools if available (or general workflow)"
            ),
            min_score=0.7,
        )

        assert quality_score >= 0.7, f"Response quality too low: {quality_score}"

    @pytest.mark.asyncio
    async def test_somatic_variant_calling(self):
        """7.6 Somatic variant calling (tumor/normal).

        Goal: Ensure the agent outlines an appropriate variant-calling pipeline.
        """
        prompt = (
            "I have sequencing data from a tumor and its matched normal sample. "
            "How do I identify somatic variants between them?"
        )

        response = await self._query_router(prompt)

        quality_score = await self._evaluate_response(
            response=response,
            rubric=(
                "Response should outline:\n"
                "1. Alignment (BWA-MEM, Bowtie2)\n"
                "2. Pre-processing (duplicate marking, base recalibration - GATK)\n"
                "3. Somatic variant calling (Mutect2, VarScan, Strelka)\n"
                "4. Filtering (remove germline variants, low-quality calls)\n"
                "5. Annotation (VEP, ANNOVAR for functional impact)\n"
                "6. Mention of tumor-normal paired analysis importance"
            ),
            min_score=0.7,
        )

        assert quality_score >= 0.7, f"Response quality too low: {quality_score}"

    @pytest.mark.asyncio
    async def test_general_onboarding(self):
        """7.7 'What should I do next?' general onboarding.

        Goal: Evaluate clarification, data-typing, and analytical guidance.
        """
        prompt = (
            "I just got my sequencing data back, but I'm not sure where to begin analyzing it. "
            "What should I do first?"
        )

        response = await self._query_router(prompt)

        quality_score = await self._evaluate_response(
            response=response,
            rubric=(
                "Response should:\n"
                "1. Ask clarifying questions (data type: RNA-seq, WGS, scRNA-seq, etc.)\n"
                "2. Suggest starting with QC (FastQC, MultiQC)\n"
                "3. Mention checking data format and quality\n"
                "4. Provide general overview of typical workflows based on data type\n"
                "5. Be helpful and not overwhelming\n"
                "6. Offer to provide more specific guidance once data type is known"
            ),
            min_score=0.7,
        )

        assert quality_score >= 0.7, f"Response quality too low: {quality_score}"

    @pytest.mark.asyncio
    async def test_coverage_anomalies(self):
        """7.8 Coverage anomalies & artifacts.

        Goal: Test recognition of common sequencing artifacts.
        """
        prompt = (
            "My coverage plot looks uneven across the genome. "
            "What could be causing this, and how can I investigate further?"
        )

        response = await self._query_router(prompt)

        quality_score = await self._evaluate_response(
            response=response,
            rubric=(
                "Response should mention possible causes:\n"
                "1. PCR duplicates (use Picard MarkDuplicates)\n"
                "2. GC bias (use tools like deepTools or Picard CollectGcBiasMetrics)\n"
                "3. Copy number variations (if cancer/tumor sample)\n"
                "4. Library preparation artifacts\n"
                "5. Alignment issues (mappability)\n"
                "6. Suggested diagnostic tools: IGV for visualization, deepTools for metrics\n"
                "7. Quality control metrics to check"
            ),
            min_score=0.7,
        )

        assert quality_score >= 0.7, f"Response quality too low: {quality_score}"

    # Helper methods

    async def _query_router(self, prompt: str) -> str:
        """Send prompt to Router agent and return response."""
        start_time = time.time()
        response = self._post(
            "/api/ai/agents/query", data={"query": prompt, "agent_type": "router"}, json=True  # Start with router
        )
        query_duration = time.time() - start_time

        self._assert_status_code_is(response, 200)
        result = response.json()

        # Store metrics for reporting
        self._test_metrics["query_duration_ms"] = int(query_duration * 1000)
        self._test_metrics["prompt"] = prompt
        self._test_metrics["agent_response"] = result["response"]["content"]
        self._test_metrics["agent_type"] = result["response"].get("agent_type", "router")

        # Extract token usage from API response if available
        if "usage" in result:
            self._test_metrics["agent_tokens_input"] = result["usage"].get("input_tokens", 0)
            self._test_metrics["agent_tokens_output"] = result["usage"].get("output_tokens", 0)

        return result["response"]["content"]

    async def _evaluate_response(self, response: str, rubric: str, min_score: float) -> float:
        """Evaluate response quality using LLM judge.

        This uses Claude Sonnet 4.0 as a judge to assess response quality.
        Returns a score between 0.0 and 1.0.
        """
        # Try to get judge API key from Galaxy config, then environment, then fall back to ai_api_key
        judge_api_key = (
            getattr(self._app.config, "agent_eval_judge_api_key", None)
            or os.environ.get("ANTHROPIC_API_KEY")
            or getattr(self._app.config, "ai_api_key", None)
        )
        if not judge_api_key:
            pytest.skip(
                "No API key available for judge evaluation. Set agent_eval_judge_api_key "
                "in galaxy.yml or ANTHROPIC_API_KEY environment variable"
            )

        # Use anthropic SDK to call Claude Sonnet 4.0 as judge
        from anthropic import (
            Anthropic,
            APIError,
            APITimeoutError,
            RateLimitError,
        )

        # Reuse client if already created, otherwise create new one
        if not hasattr(self, '_judge_client') or self._judge_client is None:
            self._judge_client = Anthropic(api_key=judge_api_key)

        client = self._judge_client

        # Get judge model from config or use default
        judge_model = getattr(self._app.config, "agent_eval_judge_model", None) or "claude-opus-4-6"

        judge_prompt = f"""You are an expert evaluator of AI agent responses for bioinformatics workflows.

Evaluate the following agent response against this rubric:

{rubric}

Agent Response:
{response}

Provide a score from 0.0 to 1.0, where:
- 1.0 = Excellent, comprehensive, accurate response covering all key points
- 0.7-0.9 = Good response covering most key points with minor gaps
- 0.5-0.7 = Adequate response but missing some important points
- < 0.5 = Poor response with major gaps or inaccuracies

Respond with ONLY a JSON object: {{"score": 0.X, "reasoning": "brief explanation"}}"""

        start_time = time.time()

        try:
            message = client.messages.create(
                model=judge_model, max_tokens=500, messages=[{"role": "user", "content": judge_prompt}]
            )
            judge_duration = time.time() - start_time

            # Parse judge response
            judge_result = json.loads(message.content[0].text)
            score = float(judge_result["score"])

        except RateLimitError as e:
            pytest.skip(f"Judge API rate limited - test inconclusive: {e}")
        except APITimeoutError as e:
            pytest.skip(f"Judge API timeout - test inconclusive: {e}")
        except (APIError, json.JSONDecodeError, KeyError, ValueError) as e:
            # These are test failures, not skips
            pytest.fail(f"Judge API error or invalid response: {e}")
        except Exception as e:
            # Unexpected error - fail the test
            pytest.fail(f"Unexpected error during judge evaluation: {e}")

        # Store judge metrics
        self._test_metrics["judge_duration_ms"] = int(judge_duration * 1000)
        self._test_metrics["judge_model"] = judge_model
        self._test_metrics["quality_score"] = score
        self._test_metrics["judge_reasoning"] = judge_result.get("reasoning", "")
        self._test_metrics["rubric"] = rubric
        self._test_metrics["min_score"] = min_score

        # Store token usage if available
        if hasattr(message, "usage"):
            self._test_metrics["judge_tokens_input"] = message.usage.input_tokens
            self._test_metrics["judge_tokens_output"] = message.usage.output_tokens

        return score

    def _save_test_report(self, test_name: str, status: str, error_message: str = None):
        """Save test results as JSON report for dashboard."""
        reports_dir = Path("test-reports")
        reports_dir.mkdir(exist_ok=True)

        # Calculate total duration
        duration_ms = 0
        if self._test_start_time:
            duration_ms = int((time.time() - self._test_start_time) * 1000)

        # Extract token counts (agent tokens come from API response, judge tokens from evaluation)
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
            "test_file": "test_bioinformatics_workflows.py",
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

        # Clean up Anthropic client to prevent resource leaks
        if hasattr(self, '_judge_client') and self._judge_client is not None:
            del self._judge_client
            self._judge_client = None

        super().tearDown()
