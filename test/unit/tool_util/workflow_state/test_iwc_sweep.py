"""Sweep tests: run workflow_state operations against a real IWC checkout.

Gated on GALAXY_TEST_IWC_DIRECTORY — skipped unless set.
Uses the default tool cache (~/.galaxy/tool_info_cache/) and auto-populates
missing tools from the ToolShed on first run.
"""

import os
from pathlib import Path
from typing import (
    List,
    Optional,
)

import pytest
from gxformat2.normalized import ensure_native

from galaxy.tool_util.workflow_state._report_models import SKIP_STATUSES
from galaxy.tool_util.workflow_state._encoding import (
    check_strict_encoding,
    check_strict_structure,
    validate_encoding_format2,
    validate_encoding_native,
)
from galaxy.tool_util.workflow_state.cache import (
    build_tool_info,
    populate_cache,
)
from galaxy.tool_util.workflow_state.clean import clean_stale_state
from galaxy.tool_util.workflow_state.export_format2 import export_workflow_to_format2
from galaxy.tool_util.workflow_state.lint_stateful import run_structural_lint
from galaxy.tool_util.workflow_state.roundtrip import roundtrip_validate
from galaxy.tool_util.workflow_state.to_native_stateful import convert_to_native_stateful
from galaxy.tool_util.workflow_state.validate import validate_workflow_cli
from galaxy.tool_util.workflow_state.validation_json_schema import (
    validate_native_workflow_json_schema,
    validate_workflow_json_schema,
)
from galaxy.tool_util.workflow_state.validation_native import validate_workflow_native
from galaxy.tool_util.workflow_state.workflow_tools import load_workflow
from galaxy.tool_util_models import ParsedTool
from galaxy.util.unittest_utils import skip_unless_environ

IWC_ENV = "GALAXY_TEST_IWC_DIRECTORY"


def _discover_native_workflows() -> List[str]:
    iwc_dir = os.environ.get(IWC_ENV, "")
    if not iwc_dir:
        return []
    return sorted(str(p) for p in Path(iwc_dir).rglob("workflows/**/*.ga") if p.is_file())


_IWC_TESTS_SUFFIXES = ("-tests.yml", "-tests.yaml", "-test.yml", "-test.yaml")


def _discover_tests_files() -> List[str]:
    iwc_dir = os.environ.get(IWC_ENV, "")
    if not iwc_dir:
        return []
    workflows_root = Path(iwc_dir) / "workflows"
    results: List[str] = []
    for suffix in _IWC_TESTS_SUFFIXES:
        results.extend(str(p) for p in workflows_root.rglob(f"*{suffix}") if p.is_file())
    return sorted(set(results))


def _tests_file_id(path: str) -> str:
    iwc_dir = os.environ.get(IWC_ENV, "")
    return os.path.relpath(path, os.path.join(iwc_dir, "workflows"))


def _workflow_id(path: str) -> str:
    iwc_dir = os.environ.get(IWC_ENV, "")
    return os.path.relpath(path, os.path.join(iwc_dir, "workflows"))


class _LenientToolInfo:
    """Wraps a GetToolInfo to return None instead of raising on missing tools."""

    def __init__(self, delegate):
        self._delegate = delegate

    def get_tool_info(self, tool_id: str, tool_version: Optional[str]) -> Optional[ParsedTool]:
        try:
            return self._delegate.get_tool_info(tool_id, tool_version)
        except Exception:
            return None


@pytest.fixture(scope="session")
def tool_info():
    """Build ToolShedGetToolInfo using default cache, populate for all IWC workflows."""
    cache_dir = os.environ.get("GALAXY_TOOL_CACHE_DIR")
    info = build_tool_info(cache_dir)
    for wf_path in _discover_native_workflows():
        populate_cache(info, wf_path, source="shed")
    return _LenientToolInfo(info)


@skip_unless_environ(IWC_ENV)
class TestIWCSweepValidateNative:
    """validate_workflow_native after cleaning stale state."""

    @pytest.mark.parametrize("wf_path", _discover_native_workflows(), ids=_workflow_id)
    def test_validate_native(self, wf_path, tool_info):
        workflow = load_workflow(wf_path)
        normalized = ensure_native(workflow)
        clean_stale_state(normalized, workflow, tool_info)
        validate_workflow_native(workflow, tool_info)


@skip_unless_environ(IWC_ENV)
class TestIWCSweepClean:
    """clean_stale_state on every IWC .ga workflow."""

    @pytest.mark.parametrize("wf_path", _discover_native_workflows(), ids=_workflow_id)
    def test_clean(self, wf_path, tool_info):
        workflow = load_workflow(wf_path)
        normalized = ensure_native(workflow)
        result = clean_stale_state(normalized, workflow, tool_info)
        assert result is not None


@skip_unless_environ(IWC_ENV)
class TestIWCSweepExport:
    """export_workflow_to_format2 on every IWC .ga workflow."""

    @pytest.mark.parametrize("wf_path", _discover_native_workflows(), ids=_workflow_id)
    def test_export(self, wf_path, tool_info):
        workflow = ensure_native(wf_path)
        result = export_workflow_to_format2(workflow, tool_info)
        assert result.format2 is not None
        fmt2_dict = result.format2_dict
        assert fmt2_dict.get("class") == "GalaxyWorkflow"


@skip_unless_environ(IWC_ENV)
class TestIWCSweepRoundtrip:
    """roundtrip_validate on every IWC .ga workflow."""

    @pytest.mark.parametrize("wf_path", _discover_native_workflows(), ids=_workflow_id)
    def test_roundtrip(self, wf_path, tool_info):
        workflow = load_workflow(wf_path)
        result = roundtrip_validate(workflow, tool_info, workflow_path=wf_path)
        assert result.ok, f"Roundtrip failed for {wf_path}: {result.error or result.error_diffs}"


@skip_unless_environ(IWC_ENV)
class TestIWCSweepToNativeStateful:
    """convert_to_native_stateful on every IWC .ga exported to format2 first."""

    @pytest.mark.parametrize("wf_path", _discover_native_workflows(), ids=_workflow_id)
    def test_to_native_stateful(self, wf_path, tool_info, tmp_path):
        workflow = ensure_native(wf_path)
        f2_result = export_workflow_to_format2(workflow, tool_info)
        # Write format2 to temp file so convert_to_native_stateful can load it
        import json

        f2_path = str(tmp_path / "workflow.gxwf.yml")
        with open(f2_path, "w") as f:
            json.dump(f2_result.format2_dict, f, indent=2)
        result = convert_to_native_stateful(f2_path, tool_info)
        assert result.native is not None
        assert result.native_dict.get("a_galaxy_workflow") == "true"


@skip_unless_environ(IWC_ENV)
class TestIWCSweepLintStateful:
    """run_structural_lint + validate_workflow_cli on every IWC .ga workflow."""

    @pytest.mark.parametrize("wf_path", _discover_native_workflows(), ids=_workflow_id)
    def test_lint_stateful(self, wf_path, tool_info):
        workflow_dict = load_workflow(wf_path)
        lint_ctx = run_structural_lint(workflow_dict)
        assert lint_ctx is not None
        results, precheck, _conn_report = validate_workflow_cli(workflow_dict, tool_info)
        assert results is not None


@skip_unless_environ(IWC_ENV)
class TestIWCSweepJsonSchema:
    """Two-level JSON Schema validation on exported format2 workflows."""

    @pytest.mark.parametrize("wf_path", _discover_native_workflows(), ids=_workflow_id)
    def test_json_schema_validate(self, wf_path, tool_info):
        workflow = ensure_native(wf_path)
        export_result = export_workflow_to_format2(workflow, tool_info)
        fmt2_dict = export_result.format2_dict
        result = validate_workflow_json_schema(fmt2_dict, get_tool_info=tool_info)
        errors = []
        if result.structural_errors:
            errors.append(f"structural: {[e.message for e in result.structural_errors]}")
        for sr in result.step_results:
            if sr.status == "fail":
                errors.append(f"step {sr.step} ({sr.tool_id}): {[e.message for e in sr.errors]}")
        assert result.valid, f"JSON Schema validation failed for {wf_path}:\n" + "\n".join(errors)


@skip_unless_environ(IWC_ENV)
class TestIWCSweepStrictEncodingClean:
    """After cleaning, native workflows must satisfy strict-encoding semantics
    (outer tool_state is a proper dict, not a JSON string). Raw .ga files on
    disk store tool_state as a JSON string — strict-encoding is a post-clean
    / post-normalization invariant, meant to catch regressions like
    reintroducing a per-key json.dumps layer in the conversion pipeline."""

    @pytest.mark.parametrize("wf_path", _discover_native_workflows(), ids=_workflow_id)
    def test_strict_encoding_native_after_clean(self, wf_path, tool_info):
        workflow = load_workflow(wf_path)
        normalized = ensure_native(workflow)
        clean_stale_state(normalized, workflow, tool_info)
        errors = validate_encoding_native(workflow)
        assert not errors, f"strict-encoding errors after clean in {wf_path}: {errors}"


@skip_unless_environ(IWC_ENV)
class TestIWCSweepStrictStateClean:
    """After cleaning, --strict-state semantics: every tool step must validate
    with no skipped steps (tool cache resolves everything) and no fails.

    Note: bypasses validate_single() / run_validate() and calls
    validate_workflow_cli() directly because library entry points still take a
    bare `strict: bool` — see STRICT_STATE_PLAN follow-up from review.
    """

    @pytest.mark.parametrize("wf_path", _discover_native_workflows(), ids=_workflow_id)
    def test_strict_state_after_clean(self, wf_path, tool_info):
        workflow_dict = load_workflow(wf_path)
        results, precheck, _conn_report = validate_workflow_cli(workflow_dict, tool_info, clean=True)
        assert (
            precheck is None or precheck.can_process
        ), f"strict-state: precheck refused {wf_path}: {precheck.detail if precheck else ''}"
        fails = [r for r in results if r.status == "fail"]
        skips = [r for r in results if r.status in SKIP_STATUSES]
        assert not fails, f"strict-state fails in {wf_path}: {[(r.step, r.errors) for r in fails]}"
        assert not skips, f"strict-state skips in {wf_path}: {[(r.step, r.tool_id) for r in skips]}"


@skip_unless_environ(IWC_ENV)
class TestIWCSweepRoundtripStrictEncoding:
    """Roundtrip (which cleans internally) must produce format2 and reimported
    native dicts that satisfy --strict-encoding on both sides. Under strict
    semantics a precheck skip is a failure, so we assert rather than skip."""

    @pytest.mark.parametrize("wf_path", _discover_native_workflows(), ids=_workflow_id)
    def test_roundtrip_strict_encoding(self, wf_path, tool_info):
        workflow = load_workflow(wf_path)
        result = roundtrip_validate(workflow, tool_info, workflow_path=wf_path)
        assert not result.skipped_reason, f"strict-state: roundtrip precheck-skipped {wf_path}: {result.skipped_reason}"
        assert result.format2_dict is not None, f"no format2 output for {wf_path}: {result.error}"
        f2_errors = validate_encoding_format2(result.format2_dict)
        assert not f2_errors, f"format2 output strict-encoding errors for {wf_path}: {f2_errors}"
        assert result.reimported_dict is not None, f"no reimported dict for {wf_path}: {result.error}"
        native_errors = validate_encoding_native(result.reimported_dict)
        assert not native_errors, f"reimported native strict-encoding errors for {wf_path}: {native_errors}"


@skip_unless_environ(IWC_ENV)
class TestIWCSweepNativeJsonSchema:
    """JSON Schema validation of native .ga workflows using WorkflowStepNativeToolState schemas."""

    @pytest.mark.parametrize("wf_path", _discover_native_workflows(), ids=_workflow_id)
    def test_native_json_schema_validate(self, wf_path, tool_info):
        workflow = load_workflow(wf_path)
        normalized = ensure_native(workflow)
        clean_stale_state(normalized, workflow, tool_info)
        result = validate_native_workflow_json_schema(workflow, tool_info)
        errors = []
        for sr in result.step_results:
            if sr.status == "fail":
                errors.append(f"step {sr.step} ({sr.tool_id}): {[e.message for e in sr.errors]}")
        assert result.valid, f"Native JSON Schema validation failed for {wf_path}:\n" + "\n".join(errors)


# Older IWC workflows with deprecated position sub-fields (bottom, height,
# right, width, x, y) that were intentionally dropped from the strict model.
_STRICT_STRUCTURE_SKIP = {
    "computational-chemistry/fragment-based-docking-scoring/fragment-based-docking-scoring.ga",
    "computational-chemistry/protein-ligand-complex-parameterization/protein-ligand-complex-parameterization.ga",
    "sars-cov-2-variant-calling/sars-cov-2-ont-artic-variant-calling/ont-artic-variation.ga",
    "sars-cov-2-variant-calling/sars-cov-2-pe-illumina-wgs-variant-calling/pe-wgs-variation.ga",
}


@skip_unless_environ(IWC_ENV)
class TestIWCSweepStrictStructure:
    """Validate IWC workflows against strict-structure (extra='forbid' models).

    Tests that IWC .ga workflows on disk have no unknown keys at the envelope
    or step level. A handful of older workflows with deprecated position
    sub-fields are skipped."""

    @pytest.mark.parametrize("wf_path", _discover_native_workflows(), ids=_workflow_id)
    def test_strict_structure(self, wf_path):
        rel = _workflow_id(wf_path)
        if rel in _STRICT_STRUCTURE_SKIP:
            pytest.skip(f"deprecated position fields: {rel}")
        workflow = load_workflow(wf_path)
        errors = check_strict_structure(workflow)
        assert not errors, f"strict-structure errors in {wf_path}: {errors}"


# IWC tests files currently rejected by the ``Tests`` model — real authoring
# drift pending upstream fixes (duplicate YAML map keys, legacy/unknown fields,
# class-less collection assertions, and ``type:`` used as a ``collection_type``
# alias). Skipped so this sweep flags only NEW drift and regressions. Keep in
# sync with the galaxy-tool-util TS sweep (iwc-sweep.test.ts
# KNOWN_INVALID_TESTS_FILES). TODO(iwc): fix upstream and prune as fixes land.
_TESTS_FILE_SKIP = {
    "VGP-assembly-v2/Assembly-Hifi-HiC-phasing-VGP4/Assembly-Hifi-HiC-phasing-VGP4-tests.yml",
    "VGP-assembly-v2/Plot-Nx-Size/Generate-Nx-and-Size-plots-for-multiple-assemblies-tests.yml",
    "VGP-assembly-v2/Purge-duplicate-contigs-VGP6/Purge-duplicate-contigs-VGP6-tests.yml",
    "VGP-assembly-v2/Purge-duplicates-one-haplotype-VGP6b/Purging-duplicates-one-haplotype-VGP6b-tests.yml",
    "VGP-assembly-v2/Scaffolding-HiC-VGP8/Scaffolding-HiC-VGP8-tests.yml",
    "VGP-assembly-v2/hi-c-contact-map-for-assembly-manual-curation/hi-c-map-for-assembly-manual-curation-tests.yml",
    "VGP-assembly-v2/kmer-profiling-hifi-trio-VGP2/kmer-profiling-hifi-trio-VGP2-tests.yml",
    "amplicon/amplicon-mgnify/mgnify-amplicon-pipeline-v5-complete/mgnify-amplicon-pipeline-v5-complete-tests.yml",
    "amplicon/amplicon-mgnify/mgnify-amplicon-pipeline-v5-its/mgnify-amplicon-pipeline-v5-its-tests.yml",
    "amplicon/amplicon-mgnify/mgnify-amplicon-pipeline-v5-quality-control-paired-end/mgnify-amplicon-pipeline-v5-quality-control-paired-end-tests.yml",
    "amplicon/amplicon-mgnify/mgnify-amplicon-pipeline-v5-quality-control-single-end/mgnify-amplicon-pipeline-v5-quality-control-single-end-tests.yml",
    "amplicon/amplicon-mgnify/mgnify-amplicon-pipeline-v5-rrna-prediction/mgnify-amplicon-pipeline-v5-rrna-prediction-tests.yml",
    "amplicon/dada2/dada2_paired-tests.yml",
    "amplicon/qiime2/qiime2-III-VI-downsteam/QIIME2-VI-diversity-metrics-and-estimations-tests.yml",
    "bacterial_genomics/bacterial-quality-and-contamination-control-post-assembly/bacterial_quality_and_contamination_control_post_assembly-tests.yml",
    "comparative_genomics/hyphy/capheine-core-and-compare-tests.yml",
    "comparative_genomics/hyphy/hyphy-compare-tests.yml",
    "comparative_genomics/hyphy/hyphy-core-tests.yml",
    "comparative_genomics/hyphy/hyphy-preprocessing-tests.yml",
    "computational-chemistry/fragment-based-docking-scoring/fragment-based-docking-scoring-tests.yml",
    "computational-chemistry/gromacs-dctmd/gromacs-dctmd-tests.yml",
    "computational-chemistry/gromacs-mmgbsa/gromacs-mmgbsa-tests.yml",
    "data-fetching/parallel-accession-download/parallel-accession-download-tests.yml",
    "data-fetching/sra-manifest-to-concatenated-fastqs/sra-manifest-to-concatenated-fastqs-tests.yml",
    "epigenetics/atacseq/atacseq-tests.yml",
    "epigenetics/average-bigwig-between-replicates/average-bigwig-between-replicates-tests.yml",
    "epigenetics/chipseq-pe/chipseq-pe-tests.yml",
    "epigenetics/chipseq-sr/chipseq-sr-tests.yml",
    "epigenetics/consensus-peaks/consensus-peaks-atac-cutandrun-tests.yml",
    "epigenetics/consensus-peaks/consensus-peaks-chip-pe-tests.yml",
    "epigenetics/consensus-peaks/consensus-peaks-chip-sr-tests.yml",
    "epigenetics/cutandrun/cutandrun-tests.yml",
    "epigenetics/hic-hicup-cooler/chic-fastq-to-cool-hicup-cooler-tests.yml",
    "epigenetics/hic-hicup-cooler/hic-fastq-to-cool-hicup-cooler-tests.yml",
    "epigenetics/hic-hicup-cooler/hic-fastq-to-pairs-hicup-tests.yml",
    "epigenetics/hic-hicup-cooler/hic-juicermediumtabix-to-cool-cooler-tests.yml",
    "genome-assembly/bacterial-genome-assembly/bacterial_genome_assembly-tests.yml",
    "genome-assembly/quality-and-contamination-control-raw-reads/quality_and_contamination_control_raw_reads-tests.yml",
    "genome_annotation/annotation-braker3/Genome_annotation_with_braker3-tests.yml",
    "genome_annotation/annotation-helixer/Galaxy-Workflow-annotation_helixer-tests.yml",
    "genome_annotation/functional-annotation/functional-annotation-of-sequences/Functional_annotation_of_sequences-tests.yml",
    "genome_annotation/lncRNAs-annotation/Galaxy-Workflow-lncRNAs_annotation_workflow-tests.yml",
    "imaging/fluorescence-nuclei-segmentation-and-counting/segmentation-and-counting-tests.yml",
    "imaging/histological-staining-area-quantification/histological-staining-area-quantification-tests.yml",
    "imaging/tissue-microarray-analysis/multiplex-tissue-microarray-analysis/multiplex-tma-tests.yml",
    "imaging/tissue-microarray-analysis/tissue-microarray-analysis/tissue-micro-array-analysis-tests.yml",
    "metabolomics/mfassignr/mfassignr-tests.yml",
    "microbiome/binning-evaluation/MAGs-binning-evaluation-tests.yml",
    "microbiome/host-contamination-removal/host-contamination-removal-long-reads/host-or-contamination-removal-on-long-reads-tests.yml",
    "microbiome/host-contamination-removal/host-contamination-removal-short-reads/host-or-contamination-removal-on-short-reads-tests.yml",
    "microbiome/mags-building/MAGs-generation-tests.yml",
    "microbiome/mags-taxonomy-annotation/MAGs-taxonomy-annotation-tests.yml",
    "microbiome/metagenomic-genes-catalogue/metagenomic-genes-catalogue-tests.yml",
    "microbiome/metagenomic-raw-reads-amr-analysis/metagenomic-raw-reads-amr-analysis-tests.yml",
    "microbiome/pathogen-identification/nanopore-pre-processing/Nanopore-Pre-Processing-tests.yml",
    "microbiome/pathogen-identification/pathogen-detection-pathogfair-samples-aggregation-and-visualisation/Pathogen-Detection-PathoGFAIR-Samples-Aggregation-and-Visualisation-tests.yml",
    "microbiome/pathogen-identification/taxonomy-profiling-and-visualization-with-krona/Taxonomy-Profiling-and-Visualization-with-Krona-tests.yml",
    "proteomics/openms-metaprosip/metaprosip-tests.yml",
    "read-preprocessing/short-read-qc-trimming/short-read-quality-control-and-trimming-tests.yml",
    "sars-cov-2-variant-calling/sars-cov-2-ont-artic-variant-calling/ont-artic-variation-tests.yml",
    "sars-cov-2-variant-calling/sars-cov-2-pe-illumina-artic-ivar-analysis/pe-wgs-ivar-analysis-test.yml",
    "sars-cov-2-variant-calling/sars-cov-2-pe-illumina-artic-variant-calling/pe-artic-variation-tests.yml",
    "sars-cov-2-variant-calling/sars-cov-2-pe-illumina-wgs-variant-calling/pe-wgs-variation-tests.yml",
    "sars-cov-2-variant-calling/sars-cov-2-se-illumina-wgs-variant-calling/se-wgs-variation-tests.yml",
    "scRNAseq/baredsc/baredSC-1d-logNorm-tests.yml",
    "scRNAseq/baredsc/baredSC-2d-logNorm-tests.yml",
    "scRNAseq/fastq-to-matrix-10x/scrna-seq-fastq-to-matrix-10x-cellplex-tests.yml",
    "scRNAseq/fastq-to-matrix-10x/scrna-seq-fastq-to-matrix-10x-v3-tests.yml",
    "scRNAseq/pseudobulk-worflow-decoupler-edger/pseudo-bulk_edgeR-tests.yml",
    "scRNAseq/scanpy-clustering/Preprocessing-and-Clustering-of-single-cell-RNA-seq-data-with-Scanpy-tests.yml",
    "scRNAseq/velocyto/Velocyto-on10X-filtered-barcodes-tests.yml",
    "scRNAseq/velocyto/Velocyto-on10X-from-bundled-tests.yml",
    "transcriptomics/rnaseq-de/rnaseq-de-filtering-plotting-tests.yml",
    "transcriptomics/rnaseq-pe/rnaseq-pe-tests.yml",
    "transcriptomics/rnaseq-sr/rnaseq-sr-tests.yml",
    "variant-calling/generic-variant-calling-wgs-pe/Generic-variation-analysis-on-WGS-PE-data-tests.yml",
    "variant-calling/haploid-variant-calling-wgs-pe/WGS-PE-variant-calling-in-haploid-system-tests.yml",
    "variant-calling/ploidy-aware-genotype-calling/genotype-variant-calling-wgs-pe-test.yml",
    "variant-calling/variation-reporting/Generic-variation-analysis-reporting-tests.yml",
    "virology/generic-non-segmented-viral-variant-calling/pe-illumina-simple-virus-calling-and-consensus-test.yml",
    "virology/influenza-isolates-consensus-and-subtyping/influenza-consensus-and-subtyping-test.yml",
    "virology/pox-virus-amplicon/pox-virus-half-genome-tests.yml",
}


@skip_unless_environ(IWC_ENV)
class TestIWCSweepValidateTests:
    """Schema-validate every IWC workflow-tests file against ``Tests``.

    Known-invalid files (``_TESTS_FILE_SKIP``) are skipped; a failure here means
    a not-yet-known drift file or a regression in this validator.
    """

    @pytest.mark.parametrize("tests_path", _discover_tests_files(), ids=_tests_file_id)
    def test_validate_tests(self, tests_path):
        from galaxy.tool_util.workflow_state.validation_tests import (
            load_tests_file,
            validate_tests_file,
        )

        rel = _tests_file_id(tests_path)
        if rel in _TESTS_FILE_SKIP:
            pytest.skip(f"known IWC tests-file drift (fix upstream): {rel}")

        parsed = load_tests_file(tests_path)
        result = validate_tests_file(parsed)
        assert result.valid, f"Tests schema errors in {tests_path}:\n" + "\n".join(
            f"  {d.path or '(root)'}: {d.message}" for d in result.diagnostics
        )


@skip_unless_environ(IWC_ENV)
class TestIWCSweepStrictAll:
    """Combined strict validation: structure + encoding + state after clean.

    Exercises the full --strict semantics: strict-structure on raw input,
    strict-encoding after cleaning, and strict-state (no skips/failures)."""

    @pytest.mark.parametrize("wf_path", _discover_native_workflows(), ids=_workflow_id)
    def test_strict_all(self, wf_path, tool_info):
        rel = _workflow_id(wf_path)
        if rel in _STRICT_STRUCTURE_SKIP:
            pytest.skip(f"deprecated position fields: {rel}")
        workflow = load_workflow(wf_path)

        # strict-structure on raw input
        struct_errors = check_strict_structure(workflow)
        assert not struct_errors, f"strict-structure errors in {wf_path}: {struct_errors}"

        # clean, then strict-encoding
        normalized = ensure_native(workflow)
        clean_stale_state(normalized, workflow, tool_info)
        enc_errors = check_strict_encoding(workflow)
        assert not enc_errors, f"strict-encoding errors after clean in {wf_path}: {enc_errors}"

        # strict-state: validate with no skips or failures
        results, precheck, _conn = validate_workflow_cli(workflow, tool_info)
        assert (
            precheck is None or precheck.can_process
        ), f"strict-state: precheck refused {wf_path}: {precheck.detail if precheck else ''}"
        fails = [r for r in results if r.status == "fail"]
        skips = [r for r in results if r.status in SKIP_STATUSES]
        assert not fails, f"strict-state fails in {wf_path}: {[(r.step, r.errors) for r in fails]}"
        assert not skips, f"strict-state skips in {wf_path}: {[(r.step, r.tool_id) for r in skips]}"
