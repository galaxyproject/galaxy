"""Bioinformatics workflow scenarios scored by LLMJudge against per-case rubrics.

Adapted from tcollins2011/galaxy PR #64 (`test/integration/agent_evals/
test_bioinformatics_workflows.py`). Tyler's tests run against a live Galaxy
server and judge with Anthropic's SDK directly; ours route through the
mocked-deps router and use whichever judge model the harness is configured
with (any OpenAI-compatible endpoint).

Each case is a real-world bioinformatics question -- "I have FASTQs from
two conditions, how do I find DEGs?" -- with a multi-point rubric the
response should hit. LLMJudge is the only scorer; there's no deterministic
keyword check because the judgable content here is reasoning about a
pipeline, not naming a single canonical tool.

Note on grounding: like ``tool_recommendation``, this runs without a live
toolbox. We're scoring the model's prior knowledge and reasoning quality,
not its grounded behavior. A query that goes to ``orchestrator`` may
return partial output if its sub-agents touch services the MagicMock'd
trans can't satisfy -- those cases fail loudly rather than silently.
"""

from typing import (
    Any,
)

from pydantic_ai.models import Model
from pydantic_evals import (
    Case,
    Dataset,
)
from pydantic_evals.evaluators import (
    LLMJudge,
    OutputConfig,
)

_PROTO_CASES: list[dict[str, Any]] = [
    {
        "name": "scrna_cell_type_identification",
        "query": (
            "I just got my single-cell RNA-seq count matrix back. How can I figure out what cell types are present?"
        ),
        "rubric": (
            "Response should mention:\n"
            "1. Clustering algorithms (Louvain, Leiden, UMAP/tSNE for visualization)\n"
            "2. Marker gene identification (differential expression between clusters)\n"
            "3. Cell type annotation (manual or automated using reference databases)\n"
            "4. Relevant Galaxy tools (Scanpy, Seurat wrapper tools if available)\n"
            "5. General workflow: QC -> normalization -> clustering -> marker genes -> annotation"
        ),
    },
    {
        "name": "bulk_rnaseq_differential_expression",
        "query": (
            "I have RNA-seq FASTQ files from two conditions. "
            "How do I identify differentially expressed genes between them?"
        ),
        "rubric": (
            "Response should outline:\n"
            "1. QC step (FastQC)\n"
            "2. Alignment/quantification (HISAT2, STAR, or Salmon/kallisto)\n"
            "3. Count aggregation (featureCounts, HTSeq-count)\n"
            "4. Differential expression analysis (DESeq2, edgeR, limma)\n"
            "5. Mention of replicates and experimental design importance\n"
            "6. Optional: Functional enrichment analysis (GO, KEGG)"
        ),
    },
    {
        "name": "qc_triage_fastqc",
        "query": (
            "My FastQC reports show poor quality at the ends and clear adapter contamination. "
            "What should I do next to clean up the data?"
        ),
        "rubric": (
            "Response should recommend:\n"
            "1. Adapter trimming (Cutadapt, Trim Galore, Trimmomatic)\n"
            "2. Quality trimming (remove low-quality bases at ends)\n"
            "3. Re-run FastQC after trimming to verify improvement\n"
            "4. Specific Galaxy tools for trimming\n"
            "5. Optional: Explanation of quality scores and adapter contamination"
        ),
    },
    {
        "name": "low_mapping_rate_troubleshooting",
        "query": (
            "My reads only mapped at about 50%. "
            "What could be causing the low mapping rate, and how can I figure out what's wrong?"
        ),
        "rubric": (
            "Response should suggest investigating:\n"
            "1. Wrong reference genome (species mismatch)\n"
            "2. Adapter/quality issues (check FastQC)\n"
            "3. Contamination (run FastQ Screen or Kraken)\n"
            "4. rRNA contamination (if RNA-seq)\n"
            "5. Library type issues (stranded vs unstranded)\n"
            "6. Diagnostic tools: FastQ Screen, Kraken2, BLAST unmapped reads"
        ),
    },
    {
        "name": "metagenomics_community_composition",
        "query": (
            "I have shotgun metagenomic sequencing data from a soil sample. "
            "How can I figure out what organisms are present and their relative abundances?"
        ),
        "rubric": (
            "Response should mention:\n"
            "1. Taxonomic profiling (Kraken2, MetaPhlAn, Kaiju, or Sylph for quick abundance estimates)\n"
            "2. Assembly-based approach (MEGAHIT, metaSPAdes for contigs)\n"
            "3. Binning (MaxBin, MetaBAT to group contigs into MAGs)\n"
            "4. Annotation of bins (CheckM for quality, prokka/DRAM for genes)\n"
            "5. Trade-offs: profiling (fast) vs assembly (detailed)\n"
            "6. Galaxy tools if available (or general workflow)"
        ),
    },
    {
        "name": "somatic_variant_calling",
        "query": ("I have matched tumor and normal whole-exome sequencing data. How do I call somatic variants?"),
        "rubric": (
            "Response should outline a tumor/normal somatic pipeline:\n"
            "1. QC + adapter trimming on both tumor and normal FASTQs\n"
            "2. Alignment to reference (BWA-MEM)\n"
            "3. Mark duplicates (Picard MarkDuplicates) and BQSR (GATK)\n"
            "4. Somatic caller appropriate for tumor/normal pairs (Mutect2, Strelka2 in somatic mode, VarScan2 somatic)\n"
            "5. Filtering (FilterMutectCalls or equivalent) and annotation (VEP, SnpEff)\n"
            "6. Mention of contamination/PoN considerations"
        ),
    },
    {
        "name": "general_onboarding_guidance",
        "query": ("I'm new to Galaxy and have a folder of FASTQ files from a sequencing run. Where do I start?"),
        "rubric": (
            "Response should orient a newcomer:\n"
            "1. Upload data into a Galaxy history\n"
            "2. Run FastQC for an initial QC pass\n"
            "3. Decide on an analysis based on the experiment type (RNA-seq, ChIP-seq, variants, etc.)\n"
            "4. Mention shared workflows / tutorials (Galaxy Training Network, IWC) as starting points\n"
            "5. General orientation tone -- don't dive into a specific pipeline without asking what the data is"
        ),
    },
    {
        "name": "coverage_anomalies_artifacts",
        "query": (
            "After alignment I'm seeing huge coverage spikes in a few regions and gaps elsewhere. "
            "Are these real or artifacts, and how do I tell?"
        ),
        "rubric": (
            "Response should help diagnose coverage anomalies:\n"
            "1. PCR duplicates as a common cause of spikes (run/inspect Picard MarkDuplicates output)\n"
            "2. Repetitive / low-mappability regions (mention mappability tracks, MAPQ filtering)\n"
            "3. Capture bias for exome / panel data\n"
            "4. Real biological signal (CNV, amplifications) as a possibility\n"
            "5. Diagnostic tools: samtools depth, mosdepth, IGV visualization, picard CollectWgsMetrics\n"
            "6. Suggest filtering by MAPQ and excluding duplicates before drawing conclusions"
        ),
    },
]


_RUBRIC_TEMPLATE = """\
You are evaluating a Galaxy AI agent's response to a bioinformatics question.

Acceptance rubric for this case:
{rubric}

Score the response between 0.0 and 1.0:
- 1.0: Excellent, comprehensive, accurate response covering all key points
- 0.7-0.9: Good response covering most key points with minor gaps
- 0.5-0.7: Adequate response but missing some important points
- < 0.5: Poor response with major gaps or inaccuracies

Return a number; no commentary.
"""


def bioinformatics_workflows_dataset(
    judge_model: Model | None = None,
    only: list[str] | None = None,
) -> Dataset[str, str, dict[str, Any]]:
    """Build the bioinformatics_workflows Dataset.

    Requires ``judge_model`` to score; without it the dataset has no
    evaluators and cases will report no scores.
    """
    cases: list[Case[str, str, dict[str, Any]]] = []
    for proto in _PROTO_CASES:
        if only and proto["name"] not in only:
            continue
        evaluators: tuple = ()
        if judge_model is not None:
            rubric = _RUBRIC_TEMPLATE.format(rubric=proto["rubric"])
            evaluators = (
                LLMJudge(
                    rubric=rubric,
                    model=judge_model,
                    include_input=True,
                    score=OutputConfig(evaluation_name="LLMJudge"),
                    assertion=False,
                ),
            )
        cases.append(
            Case(
                name=proto["name"],
                inputs=proto["query"],
                expected_output=None,
                metadata={"rubric": proto["rubric"]},
                evaluators=evaluators,
            )
        )
    return Dataset(name="bioinformatics_workflows", cases=cases)
