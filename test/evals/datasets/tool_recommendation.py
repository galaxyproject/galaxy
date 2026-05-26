"""Tool-recommendation dataset: did the agent name canonical tools?

Each case is a "what should I use for X?" query against ToolRecommendationAgent.
Scored two ways:

- MustMention (deterministic): response contains at least one canonical tool
  name we'd accept for that task. Stored as ``must_mention_any`` in metadata
  so partial credit for naming any well-known option works.
- LLMJudge (fuzzy): given the analysis goal, does the response recommend a
  real Galaxy tool, justify the choice, and avoid hallucinating tool IDs?

Note on grounding: the eval harness runs without a live toolbox, so the
agent's in-agent ``search_galaxy_tools`` returns empty and any tool-existence
verification fails. We're measuring the model's prior knowledge of canonical
Galaxy tools, which is what the production prompt has to lean on before
search results come back. Not a substitute for an end-to-end test.
"""

from typing import (
    Any,
    Optional,
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
        "name": "rnaseq_alignment",
        "query": "What tool should I use to align RNA-seq reads to a reference genome?",
        "must_mention_any": ["hisat2", "star", "tophat", "salmon"],
        "rubric": "Recommend a splice-aware aligner appropriate for RNA-seq -- HISAT2, STAR, TopHat, or a pseudo-aligner like Salmon. Reject DNA-only aligners like BWA as the primary choice.",
    },
    {
        "name": "dna_short_read_alignment",
        "query": "I need to align Illumina short reads to a reference genome for variant calling. What tool should I use?",
        "must_mention_any": ["bwa", "bowtie2", "bowtie 2", "minimap2"],
        "rubric": "Recommend a short-read DNA aligner -- BWA-MEM, Bowtie2, or minimap2. RNA-specific aligners (HISAT2, STAR) should not be the primary choice for variant-calling workflows.",
    },
    {
        "name": "fastq_quality_control",
        "query": "How do I check the quality of my FASTQ files?",
        "must_mention_any": ["fastqc", "multiqc", "falco"],
        "rubric": "Recommend FastQC (or MultiQC for aggregated reports) as the canonical Galaxy QC tool. Generic 'check the headers' answers should fail.",
    },
    {
        "name": "adapter_trimming",
        "query": "What's the best tool to trim adapters from my paired-end reads?",
        "must_mention_any": ["trimmomatic", "cutadapt", "trim galore", "fastp"],
        "rubric": "Recommend a real adapter-trimming tool -- Trimmomatic, Cutadapt, Trim Galore, or fastp. Quality-only trimmers without adapter awareness should not be the primary recommendation.",
    },
    {
        "name": "variant_calling_germline",
        "query": "I have aligned BAM files from a human exome and want to call germline SNPs and indels. Which tool?",
        "must_mention_any": [
            "gatk",
            "haplotypecaller",
            "bcftools",
            "deepvariant",
            "freebayes",
        ],
        "rubric": "Recommend a germline variant caller appropriate for human exome data -- GATK HaplotypeCaller, DeepVariant, FreeBayes, or bcftools call. Somatic-only callers (Mutect2 alone, Strelka2 in somatic mode) should not be the primary recommendation.",
    },
    {
        "name": "differential_expression",
        "query": "I have RNA-seq count tables from two conditions. How do I find differentially expressed genes?",
        "must_mention_any": ["deseq2", "edger", "limma"],
        "rubric": "Recommend DESeq2, edgeR, or limma-voom -- the canonical R/Bioconductor differential-expression tools wrapped in Galaxy. Generic statistical-test answers should fail.",
    },
    {
        "name": "peak_calling_chipseq",
        "query": "What tool do I use for peak calling on ChIP-seq data?",
        "must_mention_any": ["macs2", "macs3", "macs"],
        "rubric": "Recommend MACS2 or MACS3 as the canonical ChIP-seq peak caller. Generic 'find peaks' answers without naming a specific tool should fail.",
    },
    {
        "name": "16s_taxonomy",
        "query": "I have 16S rRNA amplicon data and want to classify sequences taxonomically. What's the standard Galaxy tool?",
        "must_mention_any": ["qiime", "mothur", "dada2", "kraken"],
        "rubric": "Recommend a real 16S analysis tool -- QIIME2, Mothur, DADA2, or Kraken (for k-mer taxonomy). Generic BLAST recommendations alone should not be the primary answer.",
    },
    {
        "name": "bam_sort_index",
        "query": "I need to sort and index a BAM file. What tool?",
        "must_mention_any": ["samtools", "picard"],
        "rubric": "Recommend SAMtools (sort + index) or Picard SortSam + BuildBamIndex. These are the canonical BAM utilities.",
    },
    {
        "name": "ambiguous_what_tools_exist",
        "query": "What kinds of tools are available in Galaxy?",
        "must_mention_any": ["category", "categories", "tool panel", "section"],
        "rubric": "Should describe Galaxy's tool organization (panel sections / categories) rather than dumping a tool list, OR offer to call a category-listing tool. Don't penalize for naming a few example categories.",
    },
]


_RUBRIC_TEMPLATE = """\
You are reviewing a response from Galaxy's tool-recommendation agent.

User asked: a question about which Galaxy tool to use for this task.

Acceptance rubric for this case:
{rubric}

Score the response between 0.0 and 1.0:
- 1.0: Recommends a real Galaxy tool that fits the rubric, with a brief
  reason tied to the user's task.
- 0.5: Names a plausible tool but the reasoning is generic or wrong, OR
  recommends an off-target but related tool.
- 0.0: Hallucinates a tool that doesn't exist, refuses to answer, or
  recommends a tool that's clearly inappropriate for the task.

Return a number; no commentary.
"""


def tool_recommendation_dataset(
    judge_model: Optional[Model] = None,
    only: Optional[list[str]] = None,
) -> Dataset[str, str, dict[str, Any]]:
    """Build the tool_recommendation Dataset.

    If judge_model is given, attaches a per-case LLMJudge with a
    rubric-specific prompt.
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
                metadata={
                    "must_mention_any": proto["must_mention_any"],
                    "rubric": proto["rubric"],
                },
                evaluators=evaluators,
            )
        )
    return Dataset(name="tool_recommendation", cases=cases)
