"""
Classes encapsulating galaxy tools and tool configuration.
"""

import itertools
import json
import logging
import math
import os
import re
import tarfile
import tempfile
from collections.abc import MutableMapping
from pathlib import Path
from typing import (
    Any,
    cast,
    Dict,
    List,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Type,
    TYPE_CHECKING,
    Union,
)
from urllib.parse import unquote_plus

import webob.exc
from mako.template import Template
from packaging.version import Version
from sqlalchemy import (
    delete,
    func,
    select,
)

from galaxy import (
    exceptions,
    model,
)
from galaxy.exceptions import (
    ToolInputsNotOKException,
    ToolInputsNotReadyException,
)
from galaxy.job_execution import output_collect
from galaxy.metadata import get_metadata_compute_strategy
from galaxy.model import (
    Job,
    StoredWorkflow,
)
from galaxy.model.dataset_collections.matching import MatchingCollections
from galaxy.tool_shed.util.repository_util import get_installed_repository
from galaxy.tool_shed.util.shed_util_common import set_image_paths
from galaxy.tool_util.deps import (
    build_dependency_manager,
    CachedDependencyManager,
    NullDependencyManager,
)
from galaxy.tool_util.fetcher import ToolLocationFetcher
from galaxy.tool_util.loader import (
    imported_macro_paths,
    raw_tool_xml_tree,
    template_macro_params,
)
from galaxy.tool_util.loader_directory import looks_like_a_tool
from galaxy.tool_util.ontologies.ontology_data import (
    biotools_reference,
    expand_ontology_data,
)
from galaxy.tool_util.output_checker import DETECTED_JOB_STATE
from galaxy.tool_util.parser import (
    get_tool_source,
    get_tool_source_from_representation,
    RequiredFiles,
    ToolOutputCollectionPart,
)
from galaxy.tool_util.parser.interface import (
    HelpContent,
    InputSource,
    PageSource,
    ToolSource,
)
from galaxy.tool_util.parser.output_objects import (
    ToolOutput,
    ToolOutputCollection,
)
from galaxy.tool_util.parser.util import (
    parse_profile_version,
    parse_tool_version_with_defaults,
)
from galaxy.tool_util.parser.xml import (
    XmlPageSource,
    XmlToolSource,
)
from galaxy.tool_util.provided_metadata import parse_tool_provided_metadata
from galaxy.tool_util.toolbox import (
    AbstractToolBox,
    AbstractToolTagManager,
    ToolLoadError,
    ToolSection,
)
from galaxy.tool_util.toolbox.views.sources import StaticToolBoxViewSources
from galaxy.tool_util.verify.interactor import ToolTestDescription
from galaxy.tool_util.verify.parse import parse_tool_test_descriptions
from galaxy.tool_util.verify.test_data import TestDataNotFoundError
from galaxy.tool_util.version import (
    LegacyVersion,
    parse_version,
)
from galaxy.tools import expressions
from galaxy.tools.actions import (
    DefaultToolAction,
    ToolAction,
)
from galaxy.tools.actions.data_manager import DataManagerToolAction
from galaxy.tools.actions.data_source import DataSourceToolAction
from galaxy.tools.actions.model_operations import ModelOperationToolAction
from galaxy.tools.cache import ToolDocumentCache
from galaxy.tools.evaluation import global_tool_errors
from galaxy.tools.execution_helpers import ToolExecutionCache
from galaxy.tools.imp_exp import JobImportHistoryArchiveWrapper
from galaxy.tools.parameters import (
    check_param,
    params_from_strings,
    params_to_incoming,
    params_to_json,
    params_to_json_internal,
    params_to_strings,
    populate_state,
    visit_input_values,
)
from galaxy.tools.parameters.basic import (
    BaseURLToolParameter,
    BooleanToolParameter,
    ColumnListParameter,
    DataCollectionToolParameter,
    DataToolParameter,
    HiddenToolParameter,
    SelectTagParameter,
    SelectToolParameter,
    ToolParameter,
)
from galaxy.tools.parameters.dataset_matcher import (
    set_dataset_matcher_factory,
    unset_dataset_matcher_factory,
)
from galaxy.tools.parameters.grouping import (
    Conditional,
    ConditionalWhen,
    Group,
    Repeat,
    Section,
    UploadDataset,
)
from galaxy.tools.parameters.input_translation import ToolInputTranslator
from galaxy.tools.parameters.meta import expand_meta_parameters
from galaxy.tools.parameters.populate_model import populate_model
from galaxy.tools.parameters.workflow_utils import workflow_building_modes
from galaxy.tools.parameters.wrapped_json import json_wrap
from galaxy.util import (
    in_directory,
    listify,
    Params,
    parse_xml_string,
    parse_xml_string_to_etree,
    rst_to_html,
    string_as_bool,
    unicodify,
    UNKNOWN,
    XML,
)
from galaxy.util.bunch import Bunch
from galaxy.util.compression_utils import get_fileobj_raw
from galaxy.util.dictifiable import UsesDictVisibleKeys
from galaxy.util.expressions import ExpressionContext
from galaxy.util.form_builder import SelectField
from galaxy.util.json import (
    safe_loads,
    swap_inf_nan,
)
from galaxy.util.path import StrPath
from galaxy.util.rules_dsl import RuleSet
from galaxy.util.template import (
    fill_template,
    refactoring_tool,
)
from galaxy.util.tool_shed.common_util import (
    get_tool_shed_repository_url,
    get_tool_shed_url_from_tool_shed_registry,
)
from galaxy.version import VERSION_MAJOR
from galaxy.work.context import (
    proxy_work_context_for_history,
    WorkRequestContext,
)
from ._types import (
    InputFormatT,
    ParameterValidationErrorsT,
    ToolRequestT,
    ToolStateDumpedToJsonInternalT,
    ToolStateDumpedToJsonT,
    ToolStateJobInstancePopulatedT,
    ToolStateJobInstanceT,
)
from .execute import (
    DatasetCollectionElementsSliceT,
    DEFAULT_JOB_CALLBACK,
    DEFAULT_PREFERRED_OBJECT_STORE_ID,
    DEFAULT_RERUN_REMAP_JOB_ID,
    DEFAULT_SET_OUTPUT_HID,
    DEFAULT_USE_CACHED_JOB,
    execute as execute_job,
    ExecutionSlice,
    JobCallbackT,
    MappingParameters,
)

if TYPE_CHECKING:
    from galaxy.app import UniverseApplication
    from galaxy.managers.context import ProvidesUserContext
    from galaxy.managers.jobs import JobSearch
    from galaxy.tools.actions.metadata import SetMetadataToolAction

log = logging.getLogger(__name__)

REQUIRES_JS_RUNTIME_MESSAGE = (
    "The tool [%s] requires a nodejs runtime to execute "
    "but node or nodejs could not be found. Please contact the Galaxy adminstrator"
)

MODEL_TOOLS_PATH = os.path.abspath(os.path.dirname(__file__))
# Tools that require Galaxy's Python environment to be preserved.
GALAXY_LIB_TOOLS_UNVERSIONED = [
    "upload1",
    "send_to_cloud",
    "__DATA_FETCH__",
    "directory_uri",
    "export_remote",
    # Legacy tools bundled with Galaxy.
    "laj_1",
    "gff2bed1",
    "gff_filter_by_feature_count",
    "Interval_Maf_Merged_Fasta2",
    "GeneBed_Maf_Fasta2",
    "maf_stats1",
    "Interval2Maf_pairwise1",
    "MAF_To_Interval1",
    "MAF_filter",
    "MAF_To_Fasta1",
    "MAF_Reverse_Complement_1",
    "MAF_split_blocks_by_species1",
    "MAF_Limit_To_Species1",
    "maf_by_block_number1",
    # Converters
    "CONVERTER_bed_to_fli_0",
    "CONVERTER_gff_to_fli_0",
    "CONVERTER_gff_to_interval_index_0",
    "CONVERTER_maf_to_fasta_0",
    "CONVERTER_maf_to_interval_0",
    # Tools improperly migrated to the tool shed (devteam)
    "qualityFilter",
    "pileup_interval",
    "count_gff_features",
    "lastz_paired_reads_wrapper",
    "subRate1",
    "find_diag_hits",
    # Tools improperly migrated using Galaxy (from shed other)
    "column_join",
    "gd_coverage_distributions",  # Genome Diversity tools from miller-lab
    "gd_dpmix",
    "gd_pca",
    "gd_phylogenetic_tree",
    "gd_population_structure",
    "gd_prepare_population_structure",
]
# Tools that needed galaxy on the PATH in the past but no longer do along
# with the version at which they were fixed.
GALAXY_LIB_TOOLS_VERSIONED = {
    "meme_fimo": parse_version("5.0.5"),
    "Extract genomic DNA 1": parse_version("3.0.0"),
    "fetchflank": parse_version("1.0.1"),
    "gops_intersect_1": parse_version("1.0.0"),
    "lastz_wrapper_2": parse_version("1.3"),
    "PEsortedSAM2readprofile": parse_version("1.1.1"),
    "sam_to_bam": parse_version("1.1.3"),
    "sam_pileup": parse_version("1.1.3"),
    "vcf_to_maf_customtrack1": parse_version("1.0.1"),
    "secure_hash_message_digest": parse_version("0.0.2"),
    "join1": parse_version("2.1.3"),
    "wiggle2simple1": parse_version("1.0.1"),
    "CONVERTER_wiggle_to_interval_0": parse_version("1.0.1"),
    "aggregate_scores_in_intervals2": parse_version("1.1.4"),
    "CONVERTER_fastq_to_fqtoc0": parse_version("1.0.1"),
    "CONVERTER_tar_to_directory": parse_version("1.0.1"),
    "tabular_to_dbnsfp": parse_version("1.0.1"),
    "cufflinks": parse_version("2.2.1.3"),
    "Convert characters1": parse_version("1.0.1"),
    "substitutions1": parse_version("1.0.1"),
    "winSplitter": parse_version("1.0.1"),
    "Interval2Maf1": parse_version("1.0.1+galaxy0"),
}

REQUIRE_FULL_DIRECTORY = {
    "includes": [{"path": "**", "path_type": "glob"}],
}
IMPLICITLY_REQUIRED_TOOL_FILES: Dict[str, Dict] = {
    "deseq2": {
        "version": parse_version("2.11.40.6"),
        "required": {"includes": [{"path": "*.R", "path_type": "glob"}]},
    },
    # minimum example:
    # "foobar": {"required": REQUIRE_FULL_DIRECTORY}
    # if no version is specified, all versions without explicit RequiredFiles will be selected
    "circos": {"required": REQUIRE_FULL_DIRECTORY},
    "cp_image_math": {"required": {"includes": [{"path": "*.py", "path_type": "glob"}]}},
    "enumerate_charges": {"required": REQUIRE_FULL_DIRECTORY},
    "fasta_compute_length": {"required": {"includes": [{"path": "utils/*", "path_type": "glob"}]}},
    "fasta_concatenate0": {"required": {"includes": [{"path": "utils/*", "path_type": "glob"}]}},
    "filter_tabular": {"required": {"includes": [{"path": "*.py", "path_type": "glob"}]}},
    "flanking_features_1": {"required": {"includes": [{"path": "utils/*", "path_type": "glob"}]}},
    "gops_intersect_1": {"required": {"includes": [{"path": "utils/*", "path_type": "glob"}]}},
    "gops_subtract_1": {"required": {"includes": [{"path": "utils/*", "path_type": "glob"}]}},
    "maxquant": {"required": {"includes": [{"path": "*.py", "path_type": "glob"}]}},
    "maxquant_mqpar": {"required": {"includes": [{"path": "*.py", "path_type": "glob"}]}},
    "query_tabular": {"required": {"includes": [{"path": "*.py", "path_type": "glob"}]}},
    "shasta": {"required": {"includes": [{"path": "configs/*", "path_type": "glob"}]}},
    "sqlite_to_tabular": {"required": {"includes": [{"path": "*.py", "path_type": "glob"}]}},
    "sucos_max_score": {"required": {"includes": [{"path": "*.py", "path_type": "glob"}]}},
}


class safe_update(NamedTuple):
    min_version: Union[LegacyVersion, Version]
    current_version: Union[LegacyVersion, Version]


# Tool updates that did not change parameters in a way that requires rebuilding workflows
WORKFLOW_SAFE_TOOL_VERSION_UPDATES = {
    "Filter1": safe_update(parse_version("1.1.0"), parse_version("1.1.1")),
    "__BUILD_LIST__": safe_update(parse_version("1.0.0"), parse_version("1.1.0")),
    "__APPLY_RULES__": safe_update(parse_version("1.0.0"), parse_version("1.1.0")),
    "__EXTRACT_DATASET__": safe_update(parse_version("1.0.0"), parse_version("1.0.1")),
    "__RELABEL_FROM_FILE__": safe_update(parse_version("1.0.0"), parse_version("1.1.0")),
    "Grep1": safe_update(parse_version("1.0.1"), parse_version("1.0.4")),
    "Show beginning1": safe_update(parse_version("1.0.0"), parse_version("1.0.2")),
    "Show tail1": safe_update(parse_version("1.0.0"), parse_version("1.0.1")),
    "sort1": safe_update(parse_version("1.1.0"), parse_version("1.2.0")),
    "CONVERTER_interval_to_bgzip_0": safe_update(parse_version("1.0.1"), parse_version("1.0.2")),
    "CONVERTER_Bam_Bai_0": safe_update(parse_version("1.0.0"), parse_version("1.0.1")),
    "CONVERTER_cram_to_bam_0": safe_update(parse_version("1.0.1"), parse_version("1.0.2")),
    "CONVERTER_fasta_to_fai": safe_update(parse_version("1.0.0"), parse_version("1.0.1")),
    "CONVERTER_sam_to_bigwig_0": safe_update(parse_version("1.0.2"), parse_version("1.0.3")),
    "CONVERTER_bam_to_coodinate_sorted_bam": safe_update(parse_version("1.0.0"), parse_version("1.0.1")),
    "CONVERTER_bam_to_qname_sorted_bam": safe_update(parse_version("1.0.0"), parse_version("1.0.1")),
}


def get_safe_version(tool: "Tool", requested_tool_version: str) -> Optional[str]:
    if tool.id:
        safe_version = WORKFLOW_SAFE_TOOL_VERSION_UPDATES.get(tool.id)
        if (
            safe_version
            and tool.lineage
            and safe_version.current_version >= parse_version(requested_tool_version) >= safe_version.min_version
        ):
            # tool versions are sorted from old to new, so check newest version first
            for lineage_version in reversed(tool.lineage.tool_versions):
                if safe_version.current_version >= parse_version(lineage_version) >= safe_version.min_version:
                    return lineage_version
    return None


class ToolNotFoundException(Exception):
    pass


def create_tool_from_source(app, tool_source: ToolSource, config_file: Optional[StrPath] = None, **kwds):
    # Allow specifying a different tool subclass to instantiate
    if (tool_module := tool_source.parse_tool_module()) is not None:
        module, cls = tool_module
        mod = __import__(module, globals(), locals(), [cls])
        ToolClass = getattr(mod, cls)
    elif tool_type := tool_source.parse_tool_type():
        ToolClass = tool_types.get(tool_type)
        if not ToolClass:
            if tool_type == "cwl":
                raise ToolLoadError("Runtime support for CWL tools is not implemented currently")
            else:
                raise ToolLoadError(f"Parsed unrecognized tool type ({tool_type}) from tool")
    else:
        # Normal tool
        root = getattr(tool_source, "root", None)
        ToolClass = Tool
    tool = ToolClass(config_file, tool_source, app, **kwds)
    return tool


def create_tool_from_representation(
    app, raw_tool_source: str, tool_dir: Optional[StrPath] = None, tool_source_class="XmlToolSource"
) -> "Tool":
    tool_source = get_tool_source(tool_source_class=tool_source_class, raw_tool_source=raw_tool_source)
    return create_tool_from_source(app, tool_source=tool_source, tool_dir=tool_dir)


class NullToolTagManager(AbstractToolTagManager):
    def reset_tags(self):
        return None

    def handle_tags(self, tool_id, tool_definition_source):
        return None


class PersistentToolTagManager(AbstractToolTagManager):
    def __init__(self, app):
        self.app = app
        self.sa_session = app.model.context

    def reset_tags(self):
        log.info(
            f"removing all tool tag associations ({str(self.sa_session.scalar(select(func.count(self.app.model.ToolTagAssociation.id))))})"
        )
        self.sa_session.execute(delete(self.app.model.ToolTagAssociation))
        self.sa_session.commit()

    def handle_tags(self, tool_id, tool_definition_source):
        elem = tool_definition_source
        if self.app.config.get_bool("enable_tool_tags", False):
            tag_names = elem.get("tags", "").split(",")
            for tag_name in tag_names:
                if tag_name == "":
                    continue
                stmt = select(self.app.model.Tag).filter_by(name=tag_name).limit(1)
                tag = self.sa_session.scalars(stmt).first()
                if not tag:
                    tag = self.app.model.Tag(name=tag_name)
                    self.sa_session.add(tag)
                    self.sa_session.commit()
                    tta = self.app.model.ToolTagAssociation(tool_id=tool_id, tag_id=tag.id)
                    self.sa_session.add(tta)
                    self.sa_session.commit()
                else:
                    for tagged_tool in tag.tagged_tools:
                        if tagged_tool.tool_id == tool_id:
                            break
                    else:
                        tta = self.app.model.ToolTagAssociation(tool_id=tool_id, tag_id=tag.id)
                        self.sa_session.add(tta)
                        self.sa_session.commit()


class ToolBox(AbstractToolBox):
    """
    A derivative of AbstractToolBox with Galaxy tooling-specific functionality
    and knowledge about Tool internals - how to construct them, action types,
    dependency management, etc.
    """

    def __init__(self, config_filenames, tool_root_dir, app, save_integrated_tool_panel: bool = True):
        self._reload_count = 0
        self.tool_location_fetcher = ToolLocationFetcher()
        self.cache_regions: Dict[str, ToolDocumentCache] = {}
        # This is here to deal with the old default value, which doesn't make
        # sense in an "installed Galaxy" world.
        # FIXME: ./
        if tool_root_dir == "./tools":
            tool_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "bundled"))
        view_sources = StaticToolBoxViewSources(
            view_directories=app.config.panel_views_dir,
            view_dicts=app.config.panel_views,
        )
        default_panel_view = app.config.default_panel_view

        super().__init__(
            config_filenames=config_filenames,
            tool_root_dir=tool_root_dir,
            app=app,
            view_sources=view_sources,
            default_panel_view=default_panel_view,
            save_integrated_tool_panel=save_integrated_tool_panel,
        )
        # Load built-in converters
        if app.config.display_builtin_converters:
            self.load_builtin_converters()
        if old_toolbox := getattr(app, "toolbox", None):
            self.dependency_manager = old_toolbox.dependency_manager
        else:
            self._init_dependency_manager()

    def tool_tag_manager(self):
        if hasattr(self.app.config, "get_bool") and self.app.config.get_bool("enable_tool_tags", False):
            return PersistentToolTagManager(self.app)
        else:
            return NullToolTagManager()

    @property
    def sa_session(self):
        """
        Returns a SQLAlchemy session
        """
        return self.app.model.context

    def reload_dependency_manager(self):
        self._init_dependency_manager()

    def load_builtin_converters(self):
        id = "builtin_converters"
        section = ToolSection({"name": "Built-in Converters", "id": id})
        self._tool_panel[id] = section

        converters = {
            tool for target in self.app.datatypes_registry.datatype_converters.values() for tool in target.values()
        }
        for tool in converters:
            tool.hidden = False
            section.elems.append_tool(tool)

    def persist_cache(self, register_postfork: bool = False):
        """
        Persists any modified tool cache files to disk.

        Set ``register_postfork`` to stop database thread queue,
        close database connection and register re-open function
        that re-opens the database after forking.
        """
        for region in self.cache_regions.values():
            if not region.disabled:
                region.persist()
                if register_postfork:
                    region.close()
                    self.app.application_stack.register_postfork_function(region.reopen_ro)

    def can_load_config_file(self, config_filename):
        if config_filename == self.app.config.shed_tool_config_file and not self.app.config.is_set(
            "shed_tool_config_file"
        ):
            if self.dynamic_confs():
                # Do not load or create a default shed_tool_config_file if another shed_tool_config file has already been loaded
                return False
        elif self.app.config.is_set("tool_config_file"):
            log.warning(
                "The default shed tool config file (%s) has been added to the tool_config_file option, if this is "
                "not the desired behavior, please set shed_tool_config_file to your primary shed-enabled tool "
                "config file",
                self.app.config.shed_tool_config_file,
            )
        return True

    def has_reloaded(self, other_toolbox):
        return self._reload_count != other_toolbox._reload_count

    @property
    def all_requirements(self):
        reqs = {req for _, tool in self.tools() for req in tool.tool_requirements}
        return [r.to_dict() for r in reqs]

    @property
    def tools_by_id(self):
        # Deprecated method, TODO - eliminate calls to this in test/.
        return self._tools_by_id

    def get_cache_region(self, tool_cache_data_dir: Optional[str]):
        if self.app.config.enable_tool_document_cache and tool_cache_data_dir:
            if tool_cache_data_dir not in self.cache_regions:
                self.cache_regions[tool_cache_data_dir] = ToolDocumentCache(cache_dir=tool_cache_data_dir)
            return self.cache_regions[tool_cache_data_dir]

    def create_tool(self, config_file: str, tool_cache_data_dir: Optional[str] = None, **kwds):
        cache = self.get_cache_region(tool_cache_data_dir)
        if config_file.endswith(".xml") and cache and not cache.disabled:
            tool_document = cache.get(config_file)
            if tool_document:
                tool_source = self.get_expanded_tool_source(
                    config_file=config_file,
                    xml_tree=parse_xml_string_to_etree(tool_document["document"]),
                    macro_paths=tool_document["macro_paths"],
                )
            else:
                tool_source = self.get_expanded_tool_source(config_file)
                cache.set(config_file, tool_source)
        else:
            tool_source = self.get_expanded_tool_source(config_file)
        return self._create_tool_from_source(tool_source, config_file=config_file, **kwds)

    def get_expanded_tool_source(self, config_file, **kwargs):
        try:
            return get_tool_source(
                config_file,
                enable_beta_formats=getattr(self.app.config, "enable_beta_tool_formats", False),
                tool_location_fetcher=self.tool_location_fetcher,
                **kwargs,
            )
        except Exception as e:
            # capture and log parsing errors
            global_tool_errors.add_error(config_file, "Tool XML parsing", e)
            raise e

    def _create_tool_from_source(self, tool_source, **kwds):
        return create_tool_from_source(self.app, tool_source, **kwds)

    def create_dynamic_tool(self, dynamic_tool, **kwds):
        tool_format = dynamic_tool.tool_format
        tool_representation = dynamic_tool.value
        if "name" not in tool_representation:
            tool_representation["name"] = f"dynamic tool {dynamic_tool.uuid}"
        tool_source = get_tool_source_from_representation(
            tool_format=tool_format,
            tool_representation=tool_representation,
        )
        kwds["dynamic"] = True
        tool = self._create_tool_from_source(tool_source, **kwds)
        tool.dynamic_tool = dynamic_tool
        tool.uuid = dynamic_tool.uuid
        if not tool.id:
            tool.id = dynamic_tool.tool_id
        if not tool.name:
            tool.name = tool.id
        return tool

    def get_tool_components(self, tool_id, tool_version=None, get_loaded_tools_by_lineage=False, set_selected=False):
        """
        Retrieve all loaded versions of a tool from the toolbox and return a select list enabling
        selection of a different version, the list of the tool's loaded versions, and the specified tool.
        """
        tool_version_select_field = None
        tools = []
        tool = None
        # Backwards compatibility for datasource tools that have default tool_id configured, but which
        # are now using only GALAXY_URL.
        tool_ids = listify(tool_id)
        for tool_id in tool_ids:
            if tool_id.endswith("/"):
                # Some data sources send back redirects ending with `/`, this takes care of that case
                tool_id = tool_id[:-1]
            if get_loaded_tools_by_lineage:
                tools = self.get_loaded_tools_by_lineage(tool_id)
            else:
                tools = self.get_tool(tool_id, tool_version=tool_version, get_all_versions=True)
            if tools:
                tool = self.get_tool(tool_id, tool_version=tool_version, get_all_versions=False)
                if len(tools) > 1:
                    tool_version_select_field = self.__build_tool_version_select_field(tools, tool.id, set_selected)
                break
        return tool_version_select_field, tools, tool

    def _path_template_kwds(self):
        return {
            "model_tools_path": MODEL_TOOLS_PATH,
        }

    def _get_tool_shed_repository(self, tool_shed, name, owner, installed_changeset_revision):
        # Abstract toolbox doesn't have a dependency on the database, so
        # override _get_tool_shed_repository here to provide this information.

        return get_installed_repository(
            self.app,
            tool_shed=tool_shed,
            name=name,
            owner=owner,
            installed_changeset_revision=installed_changeset_revision,
            from_cache=True,
        )

    def _looks_like_a_tool(self, path):
        return looks_like_a_tool(path, enable_beta_formats=getattr(self.app.config, "enable_beta_tool_formats", False))

    def _init_dependency_manager(self):
        use_tool_dependency_resolution = getattr(self.app, "use_tool_dependency_resolution", True)
        if not use_tool_dependency_resolution:
            self.dependency_manager = NullDependencyManager()
            return
        app_config_dict = self.app.config.config_dict
        conf_file = app_config_dict.get("dependency_resolvers_config_file")
        default_tool_dependency_dir = os.path.join(
            self.app.config.data_dir, self.app.config.schema.defaults["tool_dependency_dir"]
        )
        self.dependency_manager = build_dependency_manager(
            app_config_dict=app_config_dict,
            conf_file=conf_file,
            default_tool_dependency_dir=default_tool_dependency_dir,
        )

    def _load_workflow(self, workflow_id):
        """
        Return an instance of 'Workflow' identified by `id`,
        which is encoded in the tool panel.
        """
        id = self.app.security.decode_id(workflow_id)
        session = self.app.model.context
        stored = session.get(StoredWorkflow, id)
        return stored.latest_workflow

    def __build_tool_version_select_field(self, tools, tool_id, set_selected):
        """Build a SelectField whose options are the ids for the received list of tools."""
        options: List[Tuple[str, str]] = []
        for tool in tools:
            options.insert(0, (tool.version, tool.id))
        select_field = SelectField(name="tool_id")
        for option_tup in options:
            selected = set_selected and option_tup[1] == tool_id
            if selected:
                select_field.add_option(f"version {option_tup[0]}", option_tup[1], selected=True)
            else:
                select_field.add_option(f"version {option_tup[0]}", option_tup[1])
        return select_field


class DefaultToolState:
    """
    Keeps track of the state of a users interaction with a tool between
    requests.
    """

    def __init__(self):
        self.page = 0
        self.rerun_remap_job_id = None
        self.inputs = {}

    def initialize(self, trans, tool):
        """
        Create a new `DefaultToolState` for this tool. It will be initialized
        with default values for inputs. Grouping elements are filled in recursively.
        """
        self.inputs = {}
        context = ExpressionContext(self.inputs)
        for input in tool.inputs.values():
            self.inputs[input.name] = input.get_initial_value(trans, context)

    def encode(self, tool, app, nested=False):
        """
        Convert the data to a string
        """
        value = cast(Dict[str, Any], params_to_strings(tool.inputs, self.inputs, app, nested=nested))
        value["__page__"] = self.page
        value["__rerun_remap_job_id__"] = self.rerun_remap_job_id
        return value

    def decode(self, values, tool, app):
        """
        Restore the state from a string
        """
        values = safe_loads(values) or {}
        self.page = values.pop("__page__") if "__page__" in values else 0
        self.rerun_remap_job_id = values.pop("__rerun_remap_job_id__") if "__rerun_remap_job_id__" in values else None
        self.inputs = params_from_strings(tool.inputs, values, app, ignore_errors=True)

    def copy(self):
        """
        Shallow copy of the state
        """
        new_state = DefaultToolState()
        new_state.page = self.page
        new_state.rerun_remap_job_id = self.rerun_remap_job_id
        new_state.inputs = self.inputs
        return new_state


class _Options(Bunch):
    sanitize: str
    refresh: str


class Tool(UsesDictVisibleKeys):
    """
    Represents a computational tool that can be executed through Galaxy.
    """

    job_tool_configurations: list
    tool_type = "default"
    requires_setting_metadata = True
    produces_entry_points = False
    default_tool_action = DefaultToolAction
    tool_action: ToolAction
    tool_type_local = False
    dict_collection_visible_keys = ["id", "name", "version", "description", "labels"]
    __help: Optional[Template]
    job_search: "JobSearch"
    version: str

    def __init__(
        self,
        config_file: Optional[StrPath],
        tool_source: ToolSource,
        app: "UniverseApplication",
        guid: Optional[str] = None,
        repository_id=None,
        tool_shed_repository=None,
        allow_code_files: bool = True,
        dynamic: bool = False,
        tool_dir: Optional[StrPath] = None,
    ):
        """Load a tool from the config named by `config_file`"""
        self.config_file = config_file
        # Determine the full path of the directory where the tool config is
        if config_file is not None:
            tool_dir = tool_dir or os.path.dirname(config_file)
        self.tool_dir = tool_dir

        self.app = app
        self.repository_id = repository_id
        self._allow_code_files = allow_code_files
        # setup initial attribute values
        self.stdio_exit_codes: List = []
        self.stdio_regexes: List = []
        self.inputs_by_page: List[Dict] = []
        self.display_by_page: List = []
        self.action: Union[str, Tuple[str, str]] = "/tool_runner/index"
        self.target = "galaxy_main"
        self.method = "post"
        self.labels: List = []
        self.check_values = True
        self.nginx_upload = False
        self.input_required = False
        self.display_interface = True
        self.require_login = False
        self.rerun = False
        # This will be non-None for tools loaded from the database (DynamicTool objects).
        self.dynamic_tool = None
        # Define a place to keep track of all input   These
        # differ from the inputs dictionary in that inputs can be page
        # elements like conditionals, but input_params are basic form
        # parameters like SelectField objects.  This enables us to more
        # easily ensure that parameter dependencies like index files or
        # tool_data_table_conf.xml entries exist.
        self.input_params: List[ToolParameter] = []
        # Attributes of tools installed from Galaxy tool sheds.
        self.tool_shed: Optional[str] = None
        self.repository_name = None
        self.repository_owner = None
        self.changeset_revision = None
        self.installed_changeset_revision = None
        self.sharable_url = None
        self.npages = 0
        # The tool.id value will be the value of guid, but we'll keep the
        # guid attribute since it is useful to have.
        self.guid = guid
        self.old_id: Optional[str] = None
        self.python_template_version: Optional[Version] = None
        self._lineage = None
        self.dependencies: List = []
        # populate toolshed repository info, if available
        self.populate_tool_shed_info(tool_shed_repository)
        # add tool resource parameters
        self.populate_resource_parameters(tool_source)
        self.tool_errors = None
        # Parse XML element containing configuration
        self.tool_source = tool_source
        self.outputs: Dict[str, ToolOutput] = {}
        self.output_collections: Dict[str, ToolOutputCollection] = {}
        self._is_workflow_compatible = None
        self.__help = None
        self.__tests: Optional[str] = None
        try:
            self.parse(tool_source, guid=guid, dynamic=dynamic)
        except Exception as e:
            global_tool_errors.add_error(config_file, "Tool Loading", e)
            raise e
        mem_optimize = getattr(self.tool_source, "mem_optimize", None)
        if mem_optimize is not None:
            mem_optimize()
        # The job search is only relevant in a galaxy context, and breaks
        # loading tools into the toolshed for validation.
        if self.app.name == "galaxy":
            self.job_search = self.app.job_search

    def remove_from_cache(self):
        if source_path := self.tool_source.source_path:
            for region in self.app.toolbox.cache_regions.values():
                region.delete(source_path)

    @property
    def history_manager(self):
        return self.app.history_manager

    @property
    def _view(self):
        return self.app.dependency_resolvers_view

    @property
    def version_object(self):
        return parse_version(self.version)

    @property
    def sa_session(self):
        """Returns a SQLAlchemy session"""
        return self.app.model.context

    @property
    def lineage(self):
        """Return ToolLineage for this tool."""
        return self._lineage

    @property
    def tool_versions(self):
        # If we have versions, return them.
        if self.lineage:
            return list(self.lineage.tool_versions)
        else:
            return []

    @property
    def is_latest_version(self):
        tool_versions = self.tool_versions
        return not tool_versions or self.version == self.tool_versions[-1]

    @property
    def latest_version(self):
        if self.is_latest_version:
            return self
        else:
            return self.app.tool_cache.get_tool_by_id(self.lineage.get_versions()[-1].id)

    @property
    def is_datatype_converter(self):
        return self in self.app.datatypes_registry.converter_tools

    @property
    def tool_shed_repository(self):
        # If this tool is included in an installed tool shed repository, return it.
        if self.tool_shed:
            return get_installed_repository(
                self.app,
                tool_shed=self.tool_shed,
                name=self.repository_name,
                owner=self.repository_owner,
                installed_changeset_revision=self.installed_changeset_revision,
                from_cache=True,
            )

    @property
    def produces_collections_with_unknown_structure(self):
        def output_is_dynamic(output):
            if not output.collection:
                return False
            return output.dynamic_structure

        return any(map(output_is_dynamic, self.outputs.values()))

    @property
    def valid_input_states(self):
        return model.Dataset.valid_input_states

    @property
    def requires_galaxy_python_environment(self):
        """Indicates this tool's runtime requires Galaxy's Python environment."""
        # All special tool types (data source, history import/export, etc...)
        # seem to require Galaxy's Python.
        # FIXME: the (instantiated) tool class should emit this behavior, and not
        #        use inspection by string check
        if self.tool_type not in ["default", "manage_data", "interactive", "data_source", "data_source_async"]:
            return True

        if self.tool_type == "manage_data" and Version(str(self.profile)) < Version("18.09"):
            return True

        if self.tool_type == "data_source" and Version(str(self.profile)) < Version("21.09"):
            return True

        if self.tool_type == "data_source_async" and self.profile < 24.0:
            return True

        config = self.app.config
        preserve_python_environment = config.preserve_python_environment
        if preserve_python_environment == "always":
            return True
        elif preserve_python_environment == "legacy_and_local" and self.tool_shed is None:
            return True
        else:
            unversioned_legacy_tool = self.old_id in GALAXY_LIB_TOOLS_UNVERSIONED
            versioned_legacy_tool = self.old_id in GALAXY_LIB_TOOLS_VERSIONED
            legacy_tool = unversioned_legacy_tool or (
                versioned_legacy_tool and self.old_id and self.version_object < GALAXY_LIB_TOOLS_VERSIONED[self.old_id]
            )
            return legacy_tool

    def __get_job_tool_configuration(self, job_params=None):
        """Generalized method for getting this tool's job configuration.

        :type job_params: dict or None
        :returns: `galaxy.jobs.JobToolConfiguration` -- JobToolConfiguration that matches this `Tool` and the given `job_params`
        """
        rval = None
        if len(self.job_tool_configurations) == 1:
            # If there's only one config, use it rather than wasting time on comparisons
            rval = self.job_tool_configurations[0]
        elif job_params is None:
            for job_tool_config in self.job_tool_configurations:
                if not job_tool_config.params:
                    rval = job_tool_config
                    break
        else:
            for job_tool_config in self.job_tool_configurations:
                if job_tool_config.params:
                    # There are job params and this config has params defined
                    for param, value in job_params.items():
                        if param not in job_tool_config.params or job_tool_config.params[param] != value:
                            break
                    else:
                        # All params match, use this config
                        rval = job_tool_config
                        break
                else:
                    rval = job_tool_config
        assert (
            rval is not None
        ), f"Could not get a job tool configuration for Tool {self.id} with job_params {job_params}, this is a bug"
        return rval

    def get_configured_job_handler(self, job_params=None):
        """Get the configured job handler for this `Tool` given the provided `job_params`.

        Unlike the former ``get_job_handler()`` method, this does not perform "preassignment" (random selection of
        a configured handler ID from a tag).

        :param job_params: Any params specific to this job (e.g. the job source)
        :type job_params: dict or None

        :returns: str or None -- The configured handler for a job run of this `Tool`
        """
        return self.__get_job_tool_configuration(job_params=job_params).handler

    def get_job_destination(self, job_params=None):
        """
        :returns: galaxy.jobs.JobDestination -- The destination definition and runner parameters.
        """
        return self.app.job_config.get_destination(self.__get_job_tool_configuration(job_params=job_params).destination)

    def get_panel_section(self):
        return self.app.toolbox.get_section_for_tool(self)

    def allow_user_access(self, user, attempting_access=True):
        """
        :returns: bool -- Whether the user is allowed to access the tool.
        """
        if self.require_login and user is None:
            return False
        return True

    def parse(self, tool_source: ToolSource, guid: Optional[str] = None, dynamic: bool = False) -> None:
        """
        Read tool configuration from the element `root` and fill in `self`.
        """
        self.profile = parse_profile_version(tool_source)
        # Get the UNIQUE id for the tool
        self.old_id = tool_source.parse_id()
        if guid is None:
            self.id = self.old_id
        else:
            self.id = guid

        if not dynamic and not self.id:
            raise Exception(f"Missing tool 'id' for tool at '{tool_source}'")

        profile = Version(str(self.profile))
        if self.app.name == "galaxy" and profile >= Version("16.04") and Version(VERSION_MAJOR) < profile:
            message = f"The tool [{self.id}] targets version {self.profile} of Galaxy, you should upgrade Galaxy to ensure proper functioning of this tool."
            raise Exception(message)

        self.python_template_version = tool_source.parse_python_template_version()
        if self.python_template_version is None:
            # If python_template_version not specified we assume tools with profile versions >= 19.05 are python 3 ready
            if profile >= Version("19.05"):
                self.python_template_version = Version("3.5")
            else:
                self.python_template_version = Version("2.7")

        # Get the (user visible) name of the tool
        self.name = tool_source.parse_name()
        if not self.name and dynamic and self.id:
            self.name = self.id
        if not dynamic and not self.name:
            raise Exception(f"Missing tool 'name' for tool with id '{self.id}' at '{tool_source}'")

        version = parse_tool_version_with_defaults(self.id, tool_source, profile)
        self.version = version

        # Legacy feature, ignored by UI.
        self.force_history_refresh = False

        self.display_interface = tool_source.parse_display_interface(default=self.display_interface)

        self.require_login = tool_source.parse_require_login(self.require_login)

        request_param_translation_elem = tool_source.parse_request_param_translation_elem()
        if request_param_translation_elem is not None:
            # Load input translator, used by datasource tools to change names/values of incoming parameters
            self.input_translator = ToolInputTranslator.from_element(request_param_translation_elem)
        else:
            self.input_translator = None

        self.parse_command(tool_source)
        self.environment_variables = self.parse_environment_variables(tool_source)
        self.tmp_directory_vars = tool_source.parse_tmp_directory_vars()

        home_target = tool_source.parse_home_target()
        tmp_target = tool_source.parse_tmp_target()
        # If a tool explicitly sets one of these variables just respect that and turn off
        # explicit processing by Galaxy.
        for environment_variable in self.environment_variables:
            if environment_variable.get("name") == "HOME":
                home_target = None
                continue
            for tmp_directory_var in self.tmp_directory_vars:
                if environment_variable.get("name") == tmp_directory_var:
                    tmp_target = None
                    break
        self.home_target = home_target
        self.tmp_target = tmp_target
        self.docker_env_pass_through = tool_source.parse_docker_env_pass_through()
        if self.environment_variables:
            if not self.docker_env_pass_through:
                self.docker_env_pass_through = []
            self.docker_env_pass_through.extend(x["name"] for x in self.environment_variables)

        # Parameters used to build URL for redirection to external app
        redirect_url_params = tool_source.parse_redirect_url_params_elem()
        if redirect_url_params is not None and redirect_url_params.text is not None:
            # get rid of leading / trailing white space
            redirect_url_params = redirect_url_params.text.strip()
            # Replace remaining white space with something we can safely split on later
            # when we are building the params
            self.redirect_url_params = redirect_url_params.replace(" ", "**^**")
        else:
            self.redirect_url_params = ""

        # Short description of the tool
        self.description = tool_source.parse_description()

        # Versioning for tools
        self.version_string_cmd = None
        if (version_command := tool_source.parse_version_command()) is not None:
            self.version_string_cmd = version_command.strip()

            version_cmd_interpreter = tool_source.parse_version_command_interpreter()
            if version_cmd_interpreter:
                executable = self.version_string_cmd.split()[0]
                assert self.tool_dir is not None
                abs_executable = os.path.abspath(os.path.join(self.tool_dir, executable))
                command_line = self.version_string_cmd.replace(executable, abs_executable, 1)
                self.version_string_cmd = f"{version_cmd_interpreter} {command_line}"

        # Parallelism for tasks, read from tool config.
        self.parallelism = tool_source.parse_parallelism()

        # Get JobToolConfiguration(s) valid for this particular Tool.  At least
        # a 'default' will be provided that uses the 'default' handler and
        # 'default' destination.  I thought about moving this to the
        # job_config, but it makes more sense to store here. -nate
        if self.id:
            self_ids = [self.id.lower()]
            if self.old_id and self.old_id != self.id:
                # Handle toolshed guids
                self_ids = [self.id.lower(), self.id.lower().rsplit("/", 1)[0], self.old_id.lower()]
        else:
            self_ids = []
        self.all_ids = self_ids

        # In the toolshed context, there is no job config.
        if hasattr(self.app, "job_config"):
            # Order of this list must match documentation in job_conf.sample_advanced.yml
            tool_classes = []
            if self.tool_type_local:
                tool_classes.append("local")
            elif self.old_id in ["upload1", "__DATA_FETCH__"]:
                tool_classes.append("local")
            if self.requires_galaxy_python_environment:
                tool_classes.append("requires_galaxy")

            self.job_tool_configurations = self.app.job_config.get_job_tool_configurations(self_ids, tool_classes)

        # Is this a 'hidden' tool (hidden in tool menu)
        self.hidden = tool_source.parse_hidden()
        self.license = tool_source.parse_license()
        self.creator = tool_source.parse_creator()
        self.parse_inputs(self.tool_source)
        self.parse_outputs(self.tool_source)
        self.raw_help = None

        if self.app.is_webapp:
            self.raw_help = self.__get_help_with_images(tool_source.parse_help())
            self.parse_tests()
        self.__parse_legacy_features(tool_source)

        # Load any tool specific options (optional)
        self.options = _Options(
            **dict(
                sanitize=tool_source.parse_sanitize(),
                refresh=tool_source.parse_refresh(),
            )
        )

        # Read in name of galaxy.json metadata file and how to parse it.
        self.provided_metadata_file = tool_source.parse_provided_metadata_file()
        self.provided_metadata_style = tool_source.parse_provided_metadata_style()

        # Parse result handling for tool exit codes and stdout/stderr messages:
        self.parse_stdio(tool_source)

        self.strict_shell = tool_source.parse_strict_shell()

        # Any extra generated config files for the tool
        self.__parse_config_files(tool_source)
        # Action
        action = tool_source.parse_action_module()
        if action is None:
            self.tool_action = self.default_tool_action()
        else:
            module, cls = action
            mod = __import__(module, globals(), locals(), [cls])
            self.tool_action = getattr(mod, cls)()
            if getattr(self.tool_action, "requires_js_runtime", False):
                try:
                    expressions.find_engine(self.app.config)
                except Exception:
                    message = REQUIRES_JS_RUNTIME_MESSAGE % self.id or getattr(self, "uuid", "unknown tool id")
                    raise Exception(message)

        # Requirements (dependencies)
        requirements, containers, resource_requirements = tool_source.parse_requirements_and_containers()
        self.requirements = requirements
        self.containers = containers
        self.resource_requirements = resource_requirements

        required_files = tool_source.parse_required_files()
        if required_files is None:
            old_id = self.old_id
            if old_id in IMPLICITLY_REQUIRED_TOOL_FILES:
                lineage_requirement = IMPLICITLY_REQUIRED_TOOL_FILES[old_id]
                lineage_requirement_until = lineage_requirement.get("version")
                if lineage_requirement_until is None or self.version_object < lineage_requirement_until:
                    required_files = RequiredFiles.from_dict(lineage_requirement["required"])
        self.required_files = required_files

        self.citations = self._parse_citations(tool_source)
        biotools_metadata_source = getattr(self.app, "biotools_metadata_source", None)
        if biotools_metadata_source:
            ontology_data = expand_ontology_data(
                tool_source,
                self.all_ids,
                biotools_metadata_source,
            )
            self.xrefs = ontology_data.xrefs
            self.edam_operations = ontology_data.edam_operations
            self.edam_topics = ontology_data.edam_topics
        else:
            self.xrefs = []
            self.edam_operations = None
            self.edam_topics = None

        self.__parse_trackster_conf(tool_source)
        # Record macro paths so we can reload a tool if any of its macro has changes
        self._macro_paths = tool_source.macro_paths
        self.ports = tool_source.parse_interactivetool()

        self._is_workflow_compatible = self.check_workflow_compatible(self.tool_source)

    def __parse_legacy_features(self, tool_source: ToolSource):
        self.code_namespace: Dict[str, str] = {}
        self.hook_map: Dict[str, str] = {}
        self.uihints: Dict[str, str] = {}

        if not hasattr(tool_source, "root"):
            return

        # TODO: Move following logic into XmlToolSource.
        root = tool_source.root
        # Load any tool specific code (optional) Edit: INS 5/29/2007,
        # allow code files to have access to the individual tool's
        # "module" if it has one.  Allows us to reuse code files, etc.
        for code_elem in root.findall("code"):
            for hook_elem in code_elem.findall("hook"):
                for key, value in hook_elem.items():
                    # map hook to function
                    self.hook_map[key] = value
            file_name = code_elem.get("file")
            assert self.tool_dir is not None
            code_path = os.path.join(self.tool_dir, file_name)
            if self._allow_code_files:
                with open(code_path) as f:
                    code_string = f.read()
                try:
                    compiled_code = compile(code_string, code_path, "exec")
                    exec(compiled_code, self.code_namespace)
                except Exception:
                    if (
                        refactoring_tool
                        and self.python_template_version
                        and self.python_template_version.release[0] < 3
                    ):
                        # Could be a code file that uses python 2 syntax
                        translated_code = str(
                            refactoring_tool.refactor_string(code_string, name="auto_translated_code_file")
                        )
                        compiled_code = compile(translated_code, f"futurized_{code_path}", "exec")
                        exec(compiled_code, self.code_namespace)
                    else:
                        raise

        # User interface hints
        if (uihints_elem := root.find("uihints")) is not None:
            for key, value in uihints_elem.attrib.items():
                self.uihints[key] = value

    def __parse_config_files(self, tool_source):
        self.config_files = []
        if not hasattr(tool_source, "root"):
            return

        root = tool_source.root
        if (conf_parent_elem := root.find("configfiles")) is not None:
            inputs_elem = conf_parent_elem.find("inputs")
            if inputs_elem is not None:
                name = inputs_elem.get("name")
                filename = inputs_elem.get("filename", None)
                format = inputs_elem.get("format", "json")
                data_style = inputs_elem.get("data_style", "skip")
                content = dict(format=format, handle_files=data_style, type="inputs")
                self.config_files.append((name, filename, content))
            file_sources_elem = conf_parent_elem.find("file_sources")
            if file_sources_elem is not None:
                name = file_sources_elem.get("name")
                filename = file_sources_elem.get("filename", None)
                content = dict(type="files")
                self.config_files.append((name, filename, content))
            for conf_elem in conf_parent_elem.findall("configfile"):
                name = conf_elem.get("name")
                filename = conf_elem.get("filename", None)
                content = conf_elem.text
                self.config_files.append((name, filename, content))

    def __parse_trackster_conf(self, tool_source):
        self.trackster_conf = None
        if not hasattr(tool_source, "root"):
            return

        # Trackster configuration.
        if (trackster_conf := tool_source.root.find("trackster_conf")) is not None:
            self.trackster_conf = TracksterConfig.parse(trackster_conf)

    def parse_tests(self):
        if self.tool_source:
            test_descriptions = parse_tool_test_descriptions(self.tool_source, self.id)
            try:
                self.__tests = json.dumps([t.to_dict() for t in test_descriptions], indent=None)
            except Exception:
                self.__tests = None
                log.exception("Failed to parse tool tests for tool '%s'", self.id)

    @property
    def tests(self):
        if self.__tests:
            return [ToolTestDescription(d) for d in json.loads(self.__tests)]
        return None

    @property
    def _repository_dir(self):
        """If tool shed installed tool, the base directory of the repository installed."""
        if getattr(self, "tool_shed", None):
            assert self.tool_dir is not None
            tool_dir = Path(self.tool_dir)
            for repo_dir in itertools.chain([tool_dir], tool_dir.parents):
                if repo_dir.name == self.repository_name and repo_dir.parent.name == self.installed_changeset_revision:
                    return str(repo_dir)
            else:
                log.error(f"Problem finding repository dir for tool '{self.id}'")

        return None

    def test_data_path(self, filename):
        test_data = None
        if repository_dir := self._repository_dir:
            test_data = self.__walk_test_data(dir=repository_dir, filename=filename)
        else:
            if self.tool_dir:
                tool_dir = self.tool_dir
                if isinstance(self, DataManagerTool):
                    tool_dir = os.path.dirname(self.tool_dir)
                test_data = self.__walk_test_data(tool_dir, filename=filename)
        if not test_data:
            # Fallback to Galaxy test data directory for builtin tools, tools
            # under development, and some older ToolShed published tools that
            # used stock test data.
            try:
                test_data = self.app.test_data_resolver.get_filename(filename)
            except TestDataNotFoundError:
                test_data = None
        return test_data

    def __walk_test_data(self, dir, filename):
        for root, dirs, _ in os.walk(dir):
            if ".hg" in dirs:
                dirs.remove(".hg")
            if "test-data" in dirs:
                test_data_dir = os.path.join(root, "test-data")
                result = os.path.abspath(os.path.join(test_data_dir, filename))
                if not in_directory(result, test_data_dir):
                    # Don't raise an explicit exception and reveal details about what
                    # files are or are not on the path, simply return None and let the
                    # API raise a 404.
                    return None
                else:
                    if os.path.exists(result):
                        return result

    def tool_provided_metadata(self, job_wrapper):
        meta_file = os.path.join(job_wrapper.tool_working_directory, self.provided_metadata_file)
        return parse_tool_provided_metadata(
            meta_file, provided_metadata_style=self.provided_metadata_style, job_wrapper=job_wrapper
        )

    def parse_command(self, tool_source):
        """ """
        # Command line (template). Optional for tools that do not invoke a local program
        if (command := tool_source.parse_command()) is not None:
            self.command = command.lstrip()  # get rid of leading whitespace
            # Must pre-pend this AFTER processing the cheetah command template
            self.interpreter = tool_source.parse_interpreter()
        else:
            self.command = ""
            self.interpreter = None

    def parse_environment_variables(self, tool_source):
        return tool_source.parse_environment_variables()

    def parse_inputs(self, tool_source: ToolSource):
        """
        Parse the "<inputs>" element and create appropriate `ToolParameter` s.
        This implementation supports multiple pages and grouping constructs.
        """
        # Load parameters (optional)
        self.inputs: Dict[str, Union[Group, ToolParameter]] = {}
        pages = tool_source.parse_input_pages()
        enctypes: Set[str] = set()
        if pages.inputs_defined:
            if hasattr(pages, "input_elem"):
                input_elem = pages.input_elem
                # Handle properties of the input form
                self.check_values = string_as_bool(input_elem.get("check_values", self.check_values))
                self.nginx_upload = string_as_bool(input_elem.get("nginx_upload", self.nginx_upload))
                self.action = input_elem.get("action", self.action)
                # If we have an nginx upload, save the action as a tuple instead of
                # a string. The actual action needs to get url_for run to add any
                # prefixes, and we want to avoid adding the prefix to the
                # nginx_upload_path.
                if self.nginx_upload and self.app.config.nginx_upload_path and not isinstance(self.action, tuple):
                    if "?" in unquote_plus(self.action):
                        raise Exception(
                            "URL parameters in a non-default tool action can not be used "
                            "in conjunction with nginx upload.  Please convert them to "
                            "hidden POST parameters"
                        )
                    self.action = (
                        f"{self.app.config.nginx_upload_path}?nginx_redir=",
                        unquote_plus(self.action),
                    )
                self.target = input_elem.get("target", self.target)
                self.method = input_elem.get("method", self.method)
                # Parse the actual parameters
                # Handle multiple page case
            for page_source in pages.page_sources:
                inputs = self.parse_input_elem(page_source, enctypes)
                display = page_source.parse_display()
                self.inputs_by_page.append(inputs)
                self.inputs.update(inputs)
                self.display_by_page.append(display)
        else:
            self.inputs_by_page.append(self.inputs)
            self.display_by_page.append(None)
        self.display = self.display_by_page[0]
        self.npages = len(self.inputs_by_page)
        self.last_page = len(self.inputs_by_page) - 1
        self.has_multiple_pages = bool(self.last_page)
        # Determine the needed enctype for the form
        if len(enctypes) == 0:
            self.enctype = "application/x-www-form-urlencoded"
        elif len(enctypes) == 1:
            self.enctype = enctypes.pop()
        else:
            raise Exception(f"Conflicting required enctypes: {str(enctypes)}")
        # Check if the tool either has no parameters or only hidden (and
        # thus hardcoded)  FIXME: hidden parameters aren't
        # parameters at all really, and should be passed in a different
        # way, making this check easier.
        template_macros = {}
        if isinstance(tool_source, XmlToolSource):
            template_macros = template_macro_params(tool_source.root)
        self.template_macro_params = template_macros
        for param in self.inputs.values():
            if not isinstance(param, (HiddenToolParameter, BaseURLToolParameter)):
                self.input_required = True
                break

    def parse_outputs(self, tool_source):
        """
        Parse <outputs> elements and fill in self.outputs (keyed by name)
        """
        self.outputs, self.output_collections = tool_source.parse_outputs(self)

    # TODO: Include the tool's name in any parsing warnings.
    def parse_stdio(self, tool_source: ToolSource):
        """
        Parse <stdio> element(s) and fill in self.return_codes,
        self.stderr_rules, and self.stdout_rules. Return codes have a range
        and an error type (fault or warning).  Stderr and stdout rules have
        a regular expression and an error level (fault or warning).
        """
        exit_codes, regexes = tool_source.parse_stdio()
        self.stdio_exit_codes = exit_codes
        self.stdio_regexes = regexes

    def _parse_citations(self, tool_source):
        citation_models = tool_source.parse_citations()
        citations_manager = getattr(self.app, "citations_manager", None)
        citations = []
        if citations_manager is not None:
            for citation_model in citation_models:
                citation = citations_manager.parse_citation(citation_model)
                if citation:
                    citations.append(citation)
        return citations

    def parse_input_elem(
        self, page_source: PageSource, enctypes, context=None
    ) -> Dict[str, Union[Group, ToolParameter]]:
        """
        Parse a parent element whose children are inputs -- these could be
        groups (repeat, conditional) or param elements. Groups will be parsed
        recursively.
        """
        rval: Dict[str, Union[Group, ToolParameter]] = {}
        context = ExpressionContext(rval, context)
        for input_source in page_source.parse_input_sources():
            # Repeat group
            input_type = input_source.parse_input_type()
            if input_type == "repeat":
                repeat_name = input_source.get("name")
                group_r = Repeat(repeat_name)
                group_r.title = input_source.get("title")
                group_r.help = input_source.get("help", None)
                page_source = input_source.parse_nested_inputs_source()
                group_r.inputs = self.parse_input_elem(page_source, enctypes, context)
                group_r.default = int(input_source.get("default", 0))
                group_r.min = int(input_source.get("min", 0))
                # Use float instead of int so that math.inf can be used for no max
                group_r.max = float(input_source.get("max", math.inf))
                assert group_r.min <= group_r.max, ValueError(
                    f"Tool with id '{self.id}': min repeat count must be less-than-or-equal to the max."
                )
                # Force default to be within min-max range
                group_r.default = cast(int, min(max(group_r.default, group_r.min), group_r.max))
                rval[group_r.name] = group_r
            elif input_type == "conditional":
                cond_name = input_source.get("name")
                group_c = Conditional(cond_name)
                value_ref = input_source.get("value_ref", None)
                group_c.value_ref = value_ref
                group_c.value_ref_in_group = input_source.get_bool("value_ref_in_group", True)
                value_from = input_source.get("value_from", None)
                if value_from:
                    value_from = value_from.split(":")
                    temp_value_from = locals().get(value_from[0])
                    assert value_ref
                    group_c.test_param = rval[value_ref]
                    assert isinstance(group_c.test_param, ToolParameter)
                    group_c.test_param.refresh_on_change = True
                    for attr in value_from[1].split("."):
                        temp_value_from = getattr(temp_value_from, attr)
                    assert callable(temp_value_from)
                    group_c.value_from = temp_value_from
                    for case_value, case_inputs in group_c.value_from(context, group_c, self).items():
                        case = ConditionalWhen()
                        case.value = case_value
                        if case_inputs:
                            page_source = XmlPageSource(XML(f"<when>{case_inputs}</when>"))
                            case.inputs = self.parse_input_elem(page_source, enctypes, context)
                        else:
                            case.inputs = {}
                        group_c.cases.append(case)
                else:
                    # Should have one child "input" which determines the case
                    test_param_input_source = input_source.parse_test_input_source()
                    group_c.test_param = self.parse_param_elem(test_param_input_source, enctypes, context)
                    assert isinstance(group_c.test_param, (BooleanToolParameter, SelectToolParameter))
                    if group_c.test_param.optional:
                        log.debug(
                            f"Tool with id '{self.id}': declares a conditional test parameter as optional, this is invalid and will be ignored."
                        )
                        group_c.test_param.optional = False
                    possible_cases = list(
                        group_c.test_param.legal_values
                    )  # store possible cases, undefined whens will have no inputs
                    # Must refresh when test_param changes
                    group_c.test_param.refresh_on_change = True
                    # And a set of possible cases
                    for value, case_inputs_source in input_source.parse_when_input_sources():
                        case = ConditionalWhen()
                        case.value = value
                        case.inputs = self.parse_input_elem(case_inputs_source, enctypes, context)
                        group_c.cases.append(case)
                        try:
                            possible_cases.remove(case.value)
                        except Exception:
                            log.debug(
                                "Tool with id '%s': a when tag has been defined for '%s (%s) --> %s', but does not appear to be selectable.",
                                self.id,
                                group_c.name,
                                group_c.test_param.name,
                                case.value,
                            )
                    for unspecified_case in possible_cases:
                        log.warning(
                            "Tool with id '%s': a when tag has not been defined for '%s (%s) --> %s', assuming empty inputs.",
                            self.id,
                            group_c.name,
                            group_c.test_param.name,
                            unspecified_case,
                        )
                        case = ConditionalWhen()
                        case.value = unspecified_case
                        case.inputs = {}
                        group_c.cases.append(case)
                rval[group_c.name] = group_c
            elif input_type == "section":
                section_name = input_source.get("name")
                group_s = Section(section_name)
                group_s.title = input_source.get("title")
                group_s.help = input_source.get("help", None)
                group_s.expanded = input_source.get_bool("expanded", False)
                page_source = input_source.parse_nested_inputs_source()
                group_s.inputs = self.parse_input_elem(page_source, enctypes, context)
                rval[group_s.name] = group_s
            elif input_type == "upload_dataset":
                elem = input_source.elem()
                upload_name = elem.get("name")
                group_u = UploadDataset(upload_name)
                group_u.title = elem.get("title")
                group_u.file_type_name = elem.get("file_type_name", group_u.file_type_name)
                group_u.default_file_type = elem.get("default_file_type", group_u.default_file_type)
                group_u.metadata_ref = elem.get("metadata_ref", group_u.metadata_ref)
                file_type_param = rval.get(group_u.file_type_name)
                if file_type_param:
                    assert isinstance(file_type_param, ToolParameter)
                    file_type_param.refresh_on_change = True
                group_page_source = XmlPageSource(elem)
                group_u.inputs = self.parse_input_elem(group_page_source, enctypes, context)
                rval[group_u.name] = group_u
            elif input_type == "param":
                param = self.parse_param_elem(input_source, enctypes, context)
                rval[param.name] = param
                if isinstance(param, (SelectTagParameter, ColumnListParameter)):
                    param.ref_input = context[param.data_ref]
                self.input_params.append(param)
        return rval

    def parse_param_elem(self, input_source: InputSource, enctypes, context) -> ToolParameter:
        """
        Parse a single "<param>" element and return a ToolParameter instance.
        Also, if the parameter has a 'required_enctype' add it to the set
        enctypes.
        """
        param = ToolParameter.build(self, input_source)
        if param_enctype := param.get_required_enctype():
            enctypes.add(param_enctype)
        # If parameter depends on any other paramters, we must refresh the
        # form when it changes
        for name in param.get_dependencies():
            # Let it throw exception, but give some hint what the problem might be
            assert (
                name in context
            ), f"Tool with id '{self.id}': Could not find dependency '{name}' of parameter '{param.name}'"
            context[name].refresh_on_change = True
        return param

    def populate_resource_parameters(self, tool_source):
        root = getattr(tool_source, "root", None)
        if (
            root is not None
            and hasattr(self.app, "job_config")
            and hasattr(self.app.job_config, "get_tool_resource_xml")
        ):
            resource_xml = self.app.job_config.get_tool_resource_xml(root.get("id", "").lower(), self.tool_type)
            if resource_xml is not None:
                inputs = root.find("inputs")
                if inputs is None:
                    inputs = parse_xml_string("<inputs/>")
                    root.append(inputs)
                inputs.append(resource_xml)

    def populate_tool_shed_info(self, tool_shed_repository):
        if tool_shed_repository:
            self.tool_shed = tool_shed_repository.tool_shed
            assert self.tool_shed
            self.repository_name = tool_shed_repository.name
            self.repository_owner = tool_shed_repository.owner
            self.changeset_revision = tool_shed_repository.changeset_revision
            self.installed_changeset_revision = tool_shed_repository.installed_changeset_revision
            self.sharable_url = get_tool_shed_repository_url(
                self.app, self.tool_shed, self.repository_owner, self.repository_name
            )

    @property
    def help(self) -> Template:
        help_content = self.raw_help
        assert help_content
        assert help_content.format == "restructuredtext"
        try:
            return Template(
                rst_to_html(help_content.content),
                input_encoding="utf-8",
                default_filters=["decode.utf8"],
                encoding_errors="replace",
            )
        except Exception:
            log.info("Exception while parsing help for tool with id '%s'", self.id)
            return Template("", input_encoding="utf-8")

    @property
    def biotools_reference(self) -> Optional[str]:
        """Return a bio.tools ID if external reference to it is found.

        If multiple bio.tools references are found, return just the first one.
        """
        return biotools_reference(self.xrefs)

    def __get_help_with_images(self, help_content: Optional[HelpContent]) -> Optional[HelpContent]:
        if help_content and help_content.format == "restructuredtext":
            help_text = help_content.content or ""
            try:
                if help_text.find(".. image:: ") >= 0 and (self.tool_shed_repository or self.repository_id):
                    help_text = set_image_paths(
                        self.app,
                        help_text,
                        encoded_repository_id=self.repository_id,
                        tool_shed_repository=self.tool_shed_repository,
                        tool_id=self.old_id,
                        tool_version=self.version,
                    )
            except Exception:
                log.exception(
                    "Exception in parse_help, so images may not be properly displayed for tool with id '%s'", self.id
                )
            help_content = HelpContent(format="restructuredtext", content=help_text)
        return help_content

    def find_output_def(self, name):
        # name is JobToOutputDatasetAssociation name.
        # TODO: to defensive, just throw IndexError and catch somewhere
        # up that stack.
        if ToolOutputCollectionPart.is_named_collection_part_name(name):
            collection_name, part = ToolOutputCollectionPart.split_output_name(name)
            collection_def = self.output_collections.get(collection_name, None)
            if not collection_def:
                return None
            return collection_def.outputs.get(part, None)
        else:
            return self.outputs.get(name, None)

    @property
    def is_workflow_compatible(self):
        return self._is_workflow_compatible

    def check_workflow_compatible(self, tool_source):
        """
        Determine if a tool can be used in workflows. External tools and the
        upload tool are currently not supported by workflows.
        """
        # Multiple page tools are not supported -- we're eliminating most
        # of these anyway
        if self.has_multiple_pages:
            return False
        # This is probably the best bet for detecting external web tools
        # right now
        if self.tool_type.startswith("data_source"):
            return False

        if hasattr(tool_source, "root"):
            root = tool_source.root
            if not string_as_bool(root.get("workflow_compatible", "True")):
                return False

        # TODO: Anyway to capture tools that dynamically change their own
        #       outputs?
        return True

    def new_state(self, trans):
        """
        Create a new `DefaultToolState` for this tool. It will be initialized
        with default values for inputs. Grouping elements are filled in recursively.
        """
        state = DefaultToolState()
        state.initialize(trans, self)
        return state

    def get_param(self, key):
        """
        Returns the parameter named `key` or None if there is no such
        parameter.
        """
        return self.inputs.get(key, None)

    def get_hook(self, name):
        """
        Returns an object from the code file referenced by `code_namespace`
        (this will normally be a callable object)
        """
        if self.code_namespace:
            # Try to look up hook in self.hook_map, otherwise resort to default
            if name in self.hook_map and self.hook_map[name] in self.code_namespace:
                return self.code_namespace[self.hook_map[name]]
            elif name in self.code_namespace:
                return self.code_namespace[name]
        return None

    def visit_inputs(self, values, callback):
        """
        Call the function `callback` on each parameter of this tool. Visits
        grouping parameters recursively and constructs unique prefixes for
        each nested set of  The callback method is then called as:

        `callback( level_prefix, parameter, parameter_value )`
        """
        # HACK: Yet another hack around check_values -- WHY HERE?
        if self.check_values:
            visit_input_values(self.inputs, values, callback)

    def expand_incoming(
        self, request_context: WorkRequestContext, incoming: ToolRequestT, input_format: InputFormatT = "legacy"
    ) -> Tuple[
        List[ToolStateJobInstancePopulatedT],
        List[ToolStateJobInstancePopulatedT],
        Optional[int],
        Optional[MatchingCollections],
    ]:
        rerun_remap_job_id = _rerun_remap_job_id(request_context, incoming, self.id)
        set_dataset_matcher_factory(request_context, self)

        # Fixed set of input parameters may correspond to any number of jobs.
        # Expand these out to individual parameters for given jobs (tool executions).
        expanded_incomings: List[ToolStateJobInstanceT]
        collection_info: Optional[MatchingCollections]
        expanded_incomings, collection_info = expand_meta_parameters(
            request_context, self, incoming, input_format=input_format
        )

        self._ensure_expansion_is_valid(expanded_incomings, rerun_remap_job_id)

        # Process incoming data
        validation_timer = self.app.execution_timer_factory.get_timer(
            "internals.galaxy.tools.validation",
            "Validated and populated state for tool request",
        )
        all_errors: List[ParameterValidationErrorsT] = []
        all_params: List[ToolStateJobInstancePopulatedT] = []

        for expanded_incoming in expanded_incomings:
            params, errors = self._populate(request_context, expanded_incoming, input_format)
            all_errors.append(errors)
            all_params.append(params)
        unset_dataset_matcher_factory(request_context)

        log.info(validation_timer)
        return all_params, all_errors, rerun_remap_job_id, collection_info

    def _ensure_expansion_is_valid(
        self, expanded_incomings: List[ToolStateJobInstanceT], rerun_remap_job_id: Optional[int]
    ) -> None:
        """If the request corresponds to multiple jobs but this doesn't work with request configuration - raise an error.

        In particular check if this is a data source job or if we're remapping a single job - in either case we should
        not have any expansion occuring.
        """
        produces_multiple_jobs = len(expanded_incomings) > 1
        if rerun_remap_job_id and produces_multiple_jobs:
            raise exceptions.RequestParameterInvalidException(
                f"Failure executing tool with id '{self.id}' (cannot create multiple jobs when remapping existing job)."
            )

        if self.input_translator and produces_multiple_jobs:
            raise exceptions.RequestParameterInvalidException(
                f"Failure executing tool with id '{self.id}' (cannot create multiple jobs with this type of data source tool)."
            )

    def _populate(
        self, request_context, expanded_incoming: ToolStateJobInstanceT, input_format: InputFormatT
    ) -> Tuple[ToolStateJobInstancePopulatedT, ParameterValidationErrorsT]:
        """Validate expanded parameters for a job to replace references with model objects.

        So convert a ToolStateJobInstanceT to a ToolStateJobInstancePopulatedT.
        """
        params: ToolStateJobInstancePopulatedT = {}
        errors: ParameterValidationErrorsT = {}
        if self.input_translator:
            self.input_translator.translate(expanded_incoming)
        if not self.check_values:
            # If `self.check_values` is false we don't do any checking or
            # processing on input  This is used to pass raw values
            # through to/from external sites.
            params = cast(ToolStateJobInstancePopulatedT, expanded_incoming)
        else:
            # Update state for all inputs on the current page taking new
            # values from `incoming`.
            populate_state(
                request_context,
                self.inputs,
                expanded_incoming,
                params,
                errors,
                simple_errors=False,
                input_format=input_format,
            )
            self._handle_validate_input_hook(request_context, params, errors)
        return params, errors

    def _handle_validate_input_hook(
        self, request_context, params: ToolStateJobInstancePopulatedT, errors: ParameterValidationErrorsT
    ):
        # If the tool provides a `validate_input` hook, call it.
        validate_input = self.get_hook("validate_input")
        if validate_input:
            # hooks are so terrible ... this is specifically for https://github.com/galaxyproject/tools-devteam/blob/main/tool_collections/gops/basecoverage/operation_filter.py
            legacy_non_dce_params = {
                k: v.hda if isinstance(v, model.DatasetCollectionElement) and v.hda else v for k, v in params.items()
            }
            validate_input(request_context, errors, legacy_non_dce_params, self.inputs)

    def completed_jobs(
        self, trans, use_cached_job: bool, all_params: List[ToolStateJobInstancePopulatedT]
    ) -> Dict[int, Optional[model.Job]]:
        completed_jobs: Dict[int, Optional[model.Job]] = {}
        for i, param in enumerate(all_params):
            if use_cached_job:
                tool_id = self.id
                assert tool_id
                param_dump: ToolStateDumpedToJsonInternalT = params_to_json_internal(self.inputs, param, self.app)
                completed_jobs[i] = self.job_search.by_tool_input(
                    trans=trans,
                    tool_id=tool_id,
                    tool_version=self.version,
                    param=param,
                    param_dump=param_dump,
                    job_state=None,
                )
            else:
                completed_jobs[i] = None
        return completed_jobs

    def handle_input(
        self,
        trans,
        incoming: ToolRequestT,
        history: Optional[model.History] = None,
        use_cached_job: bool = DEFAULT_USE_CACHED_JOB,
        preferred_object_store_id: Optional[str] = DEFAULT_PREFERRED_OBJECT_STORE_ID,
        input_format: InputFormatT = "legacy",
    ):
        """
        Process incoming parameters for this tool from the dict `incoming`,
        update the tool state (or create if none existed), and either return
        to the form or execute the tool (only if 'execute' was clicked and
        there were no errors).
        """
        request_context = proxy_work_context_for_history(trans, history=history)
        expanded = self.expand_incoming(request_context, incoming=incoming, input_format=input_format)
        all_params: List[ToolStateJobInstancePopulatedT] = expanded[0]
        all_errors: List[ParameterValidationErrorsT] = expanded[1]
        rerun_remap_job_id: Optional[int] = expanded[2]
        collection_info: Optional[MatchingCollections] = expanded[3]

        # If there were errors, we stay on the same page and display them
        self.handle_incoming_errors(all_errors)

        mapping_params = MappingParameters(incoming, all_params)
        completed_jobs: Dict[int, Optional[model.Job]] = self.completed_jobs(trans, use_cached_job, all_params)
        execution_tracker = execute_job(
            trans,
            self,
            mapping_params,
            history=request_context.history,
            rerun_remap_job_id=rerun_remap_job_id,
            preferred_object_store_id=preferred_object_store_id,
            collection_info=collection_info,
            completed_jobs=completed_jobs,
        )
        # Raise an exception if there were jobs to execute and none of them were submitted,
        # if at least one is submitted or there are no jobs to execute - return aggregate
        # information including per-job errors. Arguably we should just always return the
        # aggregate information - we just haven't done that historically.
        raise_execution_exception = not execution_tracker.successful_jobs and len(all_params) > 0

        if raise_execution_exception:
            example_error = execution_tracker.execution_errors[0]
            assert example_error
            raise exceptions.MessageException(str(example_error))

        return dict(
            out_data=execution_tracker.output_datasets,
            num_jobs=len(execution_tracker.successful_jobs),
            job_errors=execution_tracker.execution_errors,
            jobs=execution_tracker.successful_jobs,
            output_collections=execution_tracker.output_collections,
            implicit_collections=execution_tracker.implicit_collections,
        )

    def handle_incoming_errors(self, all_errors: List[ParameterValidationErrorsT]) -> None:
        if any(all_errors):
            # simple param_key -> message string for tool form.
            err_data = {key: unicodify(value) for d in all_errors for (key, value) in d.items()}
            param_errors = {}
            for d in all_errors:
                for key, value in d.items():
                    if hasattr(value, "to_dict"):
                        value_obj = value.to_dict()
                    else:
                        value_obj = {"message": unicodify(value)}
                    param_errors[key] = value_obj
            raise exceptions.RequestParameterInvalidException(
                ", ".join(msg for msg in err_data.values()), err_data=err_data, param_errors=param_errors
            )

    def handle_single_execution(
        self,
        trans,
        rerun_remap_job_id: Optional[int],
        execution_slice: ExecutionSlice,
        history: model.History,
        execution_cache: ToolExecutionCache,
        completed_job: Optional[model.Job],
        collection_info: Optional[MatchingCollections],
        job_callback: Optional[JobCallbackT],
        preferred_object_store_id: Optional[str],
        flush_job: bool,
        skip: bool,
    ):
        """
        Return a pair with whether execution is successful as well as either
        resulting output data or an error message indicating the problem.
        """
        try:
            rval = self._execute(
                trans,
                incoming=execution_slice.param_combination,
                history=history,
                rerun_remap_job_id=rerun_remap_job_id,
                execution_cache=execution_cache,
                dataset_collection_elements=execution_slice.dataset_collection_elements,
                completed_job=completed_job,
                collection_info=collection_info,
                job_callback=job_callback,
                preferred_object_store_id=preferred_object_store_id,
                flush_job=flush_job,
                skip=skip,
            )
            job = rval[0]
            out_data = rval[1]
            if len(rval) > 2:
                execution_slice.history = rval[2]
        except (webob.exc.HTTPFound, exceptions.MessageException) as e:
            # if it's a webob redirect exception, pass it up the stack
            raise e
        except ToolInputsNotReadyException as e:
            return False, e
        except Exception as e:
            log.exception("Exception caught while attempting to execute tool with id '%s':", self.id)
            message = f"Error executing tool with id '{self.id}': {unicodify(e)}"
            return False, message
        if isinstance(out_data, dict):
            return job, list(out_data.items())
        else:
            if isinstance(out_data, str):
                message = out_data
            else:
                message = f"Failure executing tool with id '{self.id}' (invalid data returned from tool execution)"
            return False, message

    @property
    def params_with_missing_data_table_entry(self):
        """
        Return all parameters that are dynamically generated select lists whose
        options require an entry not currently in the tool_data_table_conf.xml file.
        """
        params = []
        for input_param in self.input_params:
            if isinstance(input_param, SelectToolParameter) and input_param.is_dynamic:
                options = input_param.options
                if options and options.missing_tool_data_table_name and input_param not in params:
                    params.append(input_param)
        return params

    @property
    def params_with_missing_index_file(self):
        """
        Return all parameters that are dynamically generated
        select lists whose options refer to a  missing .loc file.
        """
        params = []
        for input_param in self.input_params:
            if isinstance(input_param, SelectToolParameter) and input_param.is_dynamic:
                options = input_param.options
                if (
                    options
                    and options.tool_data_table
                    and options.tool_data_table.missing_index_file
                    and input_param not in params
                ):
                    params.append(input_param)
        return params

    def get_static_param_values(self, trans):
        """
        Returns a map of parameter names and values if the tool does not
        require any user input. Will raise an exception if any parameter
        does require input.
        """
        args = {}
        for key, param in self.inputs.items():
            # BaseURLToolParameter is now a subclass of HiddenToolParameter, so
            # we must check if param is a BaseURLToolParameter first
            if isinstance(param, BaseURLToolParameter):
                args[key] = param.get_initial_value(trans, None)
            elif isinstance(param, HiddenToolParameter):
                args[key] = model.User.expand_user_properties(trans.user, param.value)
            else:
                args[key] = param.get_initial_value(trans, None)
        return args

    def execute(
        self,
        trans,
        incoming: Optional[ToolStateJobInstancePopulatedT] = None,
        history: Optional[model.History] = None,
        set_output_hid: bool = DEFAULT_SET_OUTPUT_HID,
        flush_job: bool = True,
    ):
        """
        Execute the tool using parameter values in `incoming`. This just
        dispatches to the `ToolAction` instance specified by
        `self.tool_action`. In general this will create a `Job` that
        when run will build the tool's outputs, e.g. `DefaultToolAction`.

        _execute has many more options but should be accessed through
        handle_single_execution. The public interface to execute should be
        rarely used and in more specific ways.
        """
        return self._execute(
            trans,
            incoming=incoming,
            history=history,
            set_output_hid=set_output_hid,
            flush_job=flush_job,
        )

    def _execute(
        self,
        trans,
        incoming: Optional[ToolStateJobInstancePopulatedT] = None,
        history: Optional[model.History] = None,
        rerun_remap_job_id: Optional[int] = DEFAULT_RERUN_REMAP_JOB_ID,
        execution_cache: Optional[ToolExecutionCache] = None,
        dataset_collection_elements: Optional[DatasetCollectionElementsSliceT] = None,
        completed_job: Optional[model.Job] = None,
        collection_info: Optional[MatchingCollections] = None,
        job_callback: Optional[JobCallbackT] = DEFAULT_JOB_CALLBACK,
        preferred_object_store_id: Optional[str] = DEFAULT_PREFERRED_OBJECT_STORE_ID,
        set_output_hid: bool = DEFAULT_SET_OUTPUT_HID,
        flush_job: bool = True,
        skip: bool = False,
    ):
        if incoming is None:
            incoming = {}
        try:
            return self.tool_action.execute(
                self,
                trans,
                incoming=incoming,
                history=history,
                job_params=None,
                rerun_remap_job_id=rerun_remap_job_id,
                execution_cache=execution_cache,
                dataset_collection_elements=dataset_collection_elements,
                completed_job=completed_job,
                collection_info=collection_info,
                job_callback=job_callback,
                preferred_object_store_id=preferred_object_store_id,
                set_output_hid=set_output_hid,
                flush_job=flush_job,
                skip=skip,
            )
        except exceptions.ToolExecutionError as exc:
            job = exc.job
            job_id = UNKNOWN
            if job is not None:
                job.mark_failed(info=exc.err_msg, blurb=exc.err_code.default_error_message)
                job_id = job.id
            log.error("Tool execution failed for job: %s", job_id)
            raise

    def params_to_strings(self, params: ToolStateJobInstancePopulatedT, app, nested=False):
        return params_to_strings(self.inputs, params, app, nested)

    def params_from_strings(self, params, app, ignore_errors=False):
        return params_from_strings(self.inputs, params, app, ignore_errors)

    def check_and_update_param_values(self, values, trans, update_values=True, workflow_building_mode=False):
        """
        Check that all parameters have values, and fill in with default
        values where necessary. This could be called after loading values
        from a database in case new parameters have been added.
        """
        messages = {}
        request_context = proxy_work_context_for_history(trans, workflow_building_mode=workflow_building_mode)

        def validate_inputs(input, value, error, parent, context, prefixed_name, prefixed_label, **kwargs):
            if not error:
                value, error = check_param(request_context, input, value, context)
            if error:
                if update_values and not hasattr(input, "data_ref"):
                    try:
                        previous_value = value
                        value = input.get_initial_value(request_context, context)
                        if not prefixed_name.startswith("__"):
                            messages[prefixed_name] = (
                                error if previous_value == value else f"{error} Using default: '{value}'."
                            )
                        parent[input.name] = value
                    except Exception:
                        messages[prefixed_name] = f"Attempt to replace invalid value for '{prefixed_label}' failed."
                else:
                    messages[prefixed_name] = error

        visit_input_values(self.inputs, values, validate_inputs)
        return messages

    def build_dependency_cache(self, **kwds):
        if isinstance(self.app.toolbox.dependency_manager, CachedDependencyManager):
            self.app.toolbox.dependency_manager.build_cache(
                requirements=self.requirements,
                installed_tool_dependencies=self.installed_tool_dependencies,
                tool_dir=self.tool_dir,
                job_directory=None,
                metadata=False,
                tool_instance=self,
                **kwds,
            )

    def build_dependency_shell_commands(self, job_directory=None, metadata=False):
        """
        Return a list of commands to be run to populate the current environment to include this tools requirements.
        """
        return self.app.toolbox.dependency_manager.dependency_shell_commands(
            requirements=self.requirements,
            installed_tool_dependencies=self.installed_tool_dependencies,
            tool_dir=self.tool_dir,
            job_directory=job_directory,
            preserve_python_environment=self.requires_galaxy_python_environment,
            metadata=metadata,
            tool_instance=self,
        )

    @property
    def installed_tool_dependencies(self):
        if self.tool_shed_repository:
            installed_tool_dependencies = self.tool_shed_repository.tool_dependencies_installed_or_in_error
        else:
            installed_tool_dependencies = None
        return installed_tool_dependencies

    @property
    def tool_requirements(self):
        """
        Return all requiremens of type package
        """
        return self.requirements.packages

    @property
    def tool_requirements_status(self):
        """
        Return a list of dictionaries for all tool dependencies with their associated status
        """
        return self._view.get_requirements_status({self.id: self.tool_requirements}, self.installed_tool_dependencies)

    @property
    def output_discover_patterns(self):
        # patterns to collect for remote job execution
        patterns = []
        for output in self.outputs.values():
            patterns.extend(output.output_discover_patterns)
        return patterns

    def build_redirect_url_params(self, param_dict):
        """
        Substitute parameter values into self.redirect_url_params
        """
        if not self.redirect_url_params:
            return
        redirect_url_params = None
        # Substituting parameter values into the url params
        redirect_url_params = fill_template(self.redirect_url_params, context=param_dict)
        # Remove newlines
        redirect_url_params = redirect_url_params.replace("\n", " ").replace("\r", " ")
        return redirect_url_params

    def parse_redirect_url(self, data, param_dict):
        """
        Parse the REDIRECT_URL tool param. Tools that send data to an external
        application via a redirect must include the following 3 tool params:

        1) REDIRECT_URL - the url to which the data is being sent

        2) DATA_URL - the url to which the receiving application will send an
           http post to retrieve the Galaxy data

        3) GALAXY_URL - the url to which the external application may post
           data as a response
        """
        redirect_url = param_dict.get("REDIRECT_URL")
        redirect_url_params = self.build_redirect_url_params(param_dict)
        # Add the parameters to the redirect url.  We're splitting the param
        # string on '**^**' because the self.parse() method replaced white
        # space with that separator.
        params = redirect_url_params.split("**^**")
        rup_dict = {}
        for param in params:
            p_list = param.split("=")
            p_name = p_list[0]
            p_val = p_list[1]
            rup_dict[p_name] = p_val
        DATA_URL = param_dict.get("DATA_URL", None)
        assert DATA_URL is not None, "DATA_URL parameter missing in tool config."
        DATA_URL += f"/{str(data.id)}/display"
        redirect_url += f"?DATA_URL={DATA_URL}"
        # Add the redirect_url_params to redirect_url
        for p_name in rup_dict:
            redirect_url += f"&{p_name}={rup_dict[p_name]}"
        # Add the current user email to redirect_url
        if data.user:
            USERNAME = str(data.user.email)
        else:
            USERNAME = "Anonymous"
        redirect_url += f"&USERNAME={USERNAME}"
        return redirect_url

    def call_hook(self, hook_name, *args, **kwargs):
        """
        Call the custom code hook function identified by 'hook_name' if any,
        and return the results
        """
        try:
            code = self.get_hook(hook_name)
            if code:
                return code(*args, **kwargs)
        except Exception as e:
            original_message = ""
            if len(e.args):
                original_message = e.args[0]
            e.args = (f"Error in '{self.name}' hook '{hook_name}', original message: {original_message}",)
            raise

    def exec_before_job(self, app, inp_data, out_data, param_dict=None):
        pass

    def exec_after_process(self, app, inp_data, out_data, param_dict, job, final_job_state: Optional[str] = None):
        pass

    def job_failed(self, job_wrapper, message, exception=False):
        """
        Called when a job has failed
        """

    def discover_outputs(
        self,
        out_data,
        out_collections,
        tool_provided_metadata,
        tool_working_directory,
        job,
        input_ext,
        input_dbkey,
        inp_data=None,
        final_job_state="ok",
    ):
        """
        Find any additional datasets generated by a tool and attach (for
        cases where number of outputs is not known in advance).
        """
        # given the job_execution import is the only one, probably makes sense to refactor this out
        # into job_wrapper.
        tool = self
        permission_provider = output_collect.PermissionProvider(inp_data, tool.app.security_agent, job)
        metadata_source_provider = output_collect.MetadataSourceProvider(inp_data)
        job_context = output_collect.JobContext(
            tool,
            tool_provided_metadata,
            job,
            tool_working_directory,
            permission_provider,
            metadata_source_provider,
            input_dbkey,
            object_store=tool.app.object_store,
            final_job_state=final_job_state,
            flush_per_n_datasets=tool.app.config.flush_per_n_datasets,
            max_discovered_files=tool.app.config.max_discovered_files,
        )
        collected = output_collect.collect_primary_datasets(
            job_context,
            out_data,
            input_ext,
        )
        output_collect.collect_dynamic_outputs(
            job_context,
            out_collections,
        )
        # Return value only used in unit tests. Probably should be returning number of collected
        # bytes instead?
        return collected

    def to_archive(self):
        tarball_files = []
        temp_files = []
        assert self.config_file
        with open(os.path.abspath(self.config_file)) as fh1:
            tool_xml = fh1.read()
        # Retrieve tool help images and rewrite the tool's xml into a temporary file with the path
        # modified to be relative to the repository root.
        image_found = False
        if self.help is not None:
            tool_help = self.help._source
            # Check each line of the rendered tool help for an image tag that points to a location under static/
            for help_line in tool_help.split("\n"):
                image_regex = re.compile(r'img alt="[^"]+" src="\${static_path}/([^"]+)"')
                matches = re.search(image_regex, help_line)
                if matches is not None:
                    tool_help_image = matches.group(1)
                    tarball_path = tool_help_image
                    filesystem_path = os.path.abspath(os.path.join(self.app.config.root, "static", tool_help_image))
                    if os.path.exists(filesystem_path):
                        tarball_files.append((filesystem_path, tarball_path))
                        image_found = True
                        tool_xml = tool_xml.replace(f"${{static_path}}/{tarball_path}", tarball_path)
        # If one or more tool help images were found, add the modified tool XML to the tarball instead of the original.
        if image_found:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as fh2:
                new_tool_config = fh2.name
                fh2.write(tool_xml)
            tool_tup = (new_tool_config, os.path.split(self.config_file)[-1])
            temp_files.append(new_tool_config)
        else:
            tool_tup = (os.path.abspath(self.config_file), os.path.split(self.config_file)[-1])
        tarball_files.append(tool_tup)
        # TODO: This feels hacky.
        tool_command = self.command.strip().split()[0]
        tool_path = os.path.dirname(os.path.abspath(self.config_file))
        # Add the tool XML to the tuple that will be used to populate the tarball.
        if os.path.exists(os.path.join(tool_path, tool_command)):
            tarball_files.append((os.path.join(tool_path, tool_command), tool_command))
        # Find and add macros and code files.
        for external_file in self.get_externally_referenced_paths(os.path.abspath(self.config_file)):
            external_file_abspath = os.path.abspath(os.path.join(tool_path, external_file))
            tarball_files.append((external_file_abspath, external_file))
        if os.path.exists(os.path.join(tool_path, "Dockerfile")):
            tarball_files.append((os.path.join(tool_path, "Dockerfile"), "Dockerfile"))
        # Find tests, and check them for test data.
        if (tests := self.tests) is not None:
            for test in tests:
                # Add input file tuples to the list.
                for input in test.inputs:
                    for input_value in test.inputs[input]:
                        input_filename = str(input_value)
                        input_path = os.path.abspath(os.path.join("test-data", input_filename))
                        if os.path.exists(input_path):
                            td_tup = (input_path, os.path.join("test-data", input_filename))
                            tarball_files.append(td_tup)
                # And add output file tuples to the list.
                for _, filename, _ in test.outputs:
                    output_filepath = os.path.abspath(os.path.join("test-data", filename))
                    if os.path.exists(output_filepath):
                        td_tup = (output_filepath, os.path.join("test-data", filename))
                        tarball_files.append(td_tup)
        for param in self.input_params:
            # Check for tool data table definitions.
            param_options = getattr(param, "options", None)
            if param_options is not None:
                if hasattr(param_options, "tool_data_table"):
                    data_table = param_options.tool_data_table
                    if hasattr(data_table, "filenames"):
                        data_table_definitions = []
                        for data_table_filename in data_table.filenames:
                            # FIXME: from_shed_config seems to always be False.
                            if not data_table.filenames[data_table_filename]["from_shed_config"]:
                                tar_file = f"{data_table.filenames[data_table_filename]['filename']}.sample"
                                sample_file = os.path.join(
                                    data_table.filenames[data_table_filename]["tool_data_path"], tar_file
                                )
                                # Use the .sample file, if one exists. If not, skip this data table.
                                if os.path.exists(sample_file):
                                    tarfile_path, tarfile_name = os.path.split(tar_file)
                                    tarfile_path = os.path.join("tool-data", tarfile_name)
                                    tarball_files.append((sample_file, tarfile_path))
                                data_table_definitions.append(data_table.xml_string)
                        if len(data_table_definitions) > 0:
                            # Put the data table definition XML in a temporary file.
                            table_definition = '<?xml version="1.0" encoding="utf-8"?>\n<tables>\n    %s</tables>'
                            table_definition = table_definition % "\n".join(data_table_definitions)
                            with tempfile.NamedTemporaryFile(mode="w", delete=False) as fh3:
                                table_conf = fh3.name
                                fh3.write(table_definition)
                            tarball_files.append(
                                (table_conf, os.path.join("tool-data", "tool_data_table_conf.xml.sample"))
                            )
                            temp_files.append(table_conf)
        # Create the tarball.
        with tempfile.NamedTemporaryFile(suffix=".tgz", delete=False) as fh4:
            tarball_archive = fh4.name
        tarball = tarfile.open(name=tarball_archive, mode="w:gz")
        # Add the files from the previously generated list.
        for fspath, tarpath in tarball_files:
            tarball.add(fspath, arcname=tarpath)
        tarball.close()
        # Delete any temporary files that were generated.
        for temp_file in temp_files:
            os.remove(temp_file)
        return tarball_archive

    def to_dict(self, trans, link_details=False, io_details=False, tool_help=False):
        """Returns dict of tool."""

        # Basic information
        tool_dict = self._dictify_view_keys()

        tool_dict["edam_operations"] = self.edam_operations
        tool_dict["edam_topics"] = self.edam_topics
        tool_dict["hidden"] = self.hidden
        tool_dict["is_workflow_compatible"] = self.is_workflow_compatible
        tool_dict["xrefs"] = self.xrefs

        # Fill in ToolShedRepository info
        if hasattr(self, "tool_shed") and self.tool_shed:
            tool_dict["tool_shed_repository"] = {
                "name": self.repository_name,
                "owner": self.repository_owner,
                "changeset_revision": self.changeset_revision,
                "tool_shed": self.tool_shed,
            }

        # If an admin user, expose the path to the actual tool config XML file.
        if trans.user_is_admin:
            config_file = None if not self.config_file else os.path.abspath(self.config_file)
            tool_dict["config_file"] = config_file

        # Add link details.
        if link_details:
            # Add details for creating a hyperlink to the tool.
            if not isinstance(self, DataSourceTool):
                link = self.app.url_for(controller="tool_runner", tool_id=self.id)
            else:
                link = self.app.url_for(controller="tool_runner", action="data_source_redirect", tool_id=self.id)

            # Basic information
            tool_dict.update({"link": link, "min_width": self.uihints.get("minwidth", -1), "target": self.target})

        # Add input and output details.
        if io_details:
            tool_dict["inputs"] = [input.to_dict(trans) for input in self.inputs.values()]
            tool_dict["outputs"] = [output.to_dict(app=self.app) for output in self.outputs.values()]

        tool_dict["panel_section_id"], tool_dict["panel_section_name"] = self.get_panel_section()

        tool_class = self.__class__
        # FIXME: the Tool class should declare directly, instead of ad hoc inspection
        regular_form = tool_class == Tool or isinstance(self, (DatabaseOperationTool, InteractiveTool))
        tool_dict["form_style"] = "regular" if regular_form else "special"
        if tool_help:
            # create tool help
            help_txt = ""
            help_format = "restructuredtext"
            help_content = self.raw_help
            if help_content:
                help_format = help_content.format
                if help_format == "restructuredtext":
                    help_txt = self.help.render(
                        static_path=self.app.url_for("/static"), host_url=self.app.url_for("/", qualified=True)
                    )
                    help_txt = unicodify(help_txt)

            tool_dict["help"] = help_txt
            tool_dict["help_format"] = help_format

        return tool_dict

    def to_json(self, trans, kwd=None, job=None, workflow_building_mode=False, history=None):
        """
        Recursively creates a tool dictionary containing repeats, dynamic options and updated states.
        """
        if kwd is None:
            kwd = {}
        if (
            workflow_building_mode is workflow_building_modes.USE_HISTORY
            or workflow_building_mode is workflow_building_modes.DISABLED
        ):
            # We don't need a history when exporting a workflow for the workflow editor or when downloading a workflow
            history = history or trans.get_history()
            if history is None and job is not None:
                history = self.history_manager.get_owned(job.history.id, trans.user, current_history=trans.history)
            # We can show the tool form if the current user is anonymous and doesn't have a history
            user = trans.get_user()
            if history is None and user is not None:
                raise exceptions.MessageException("History unavailable. Please specify a valid history id")

        # build request context
        request_context = proxy_work_context_for_history(trans, history, workflow_building_mode=workflow_building_mode)

        # load job parameters into incoming
        tool_message = ""
        tool_warnings = None
        if job:
            try:
                job_params = job.get_param_values(self.app, ignore_errors=True)
                tool_warnings = self.check_and_update_param_values(job_params, request_context, update_values=True)
                self._map_source_to_history(request_context, self.inputs, job_params)
                tool_message = self._compare_tool_version(job)
                params_to_incoming(kwd, self.inputs, job_params, self.app)
            except Exception as e:
                raise exceptions.MessageException(unicodify(e))

        # create parameter object
        params = Params(kwd, sanitize=False)

        # do param translation here, used by datasource tools
        if self.input_translator:
            self.input_translator.translate(params)

        set_dataset_matcher_factory(request_context, self)
        # create tool state
        state_inputs: Dict[str, str] = {}
        state_errors: ParameterValidationErrorsT = {}
        populate_state(request_context, self.inputs, params.__dict__, state_inputs, state_errors)

        # create tool model
        tool_model = self.to_dict(request_context)
        tool_model["inputs"] = []
        self.populate_model(request_context, self.inputs, state_inputs, tool_model["inputs"])
        unset_dataset_matcher_factory(request_context)

        # create tool help
        tool_help = ""
        tool_help_format = "restructuredtext"
        if self.raw_help and self.raw_help.format == "restructuredtext":
            tool_help = self.help.render(
                static_path=self.app.url_for("/static"), host_url=self.app.url_for("/", qualified=True)
            )
            tool_help = unicodify(tool_help, "utf-8")
        elif self.raw_help:
            tool_help = self.raw_help.content
            tool_help_format = self.raw_help.format

        if isinstance(self.action, tuple):
            action = self.action[0] + self.app.url_for(self.action[1])
        else:
            action = self.app.url_for(self.action)

        state_inputs_json: ToolStateDumpedToJsonT = params_to_json(self.inputs, state_inputs, self.app)

        # update tool model
        tool_model.update(
            {
                "id": self.id,
                "help": tool_help,
                "help_format": tool_help_format,
                "citations": bool(self.citations),
                "sharable_url": self.sharable_url,
                "message": tool_message,
                "warnings": tool_warnings,
                "versions": self.tool_versions,
                "requirements": [{"name": r.name, "version": r.version} for r in self.requirements],
                "errors": state_errors,
                "tool_errors": self.tool_errors,
                "state_inputs": state_inputs_json,
                "job_id": trans.security.encode_id(job.id) if job else None,
                "job_remap": job.remappable() if job else None,
                "history_id": trans.security.encode_id(history.id) if history else None,
                "display": self.display_interface,
                "action": action,
                "license": self.license,
                "creator": self.creator,
                "method": self.method,
                "enctype": self.enctype,
            }
        )
        return swap_inf_nan(tool_model)

    def populate_model(self, request_context, inputs, state_inputs, group_inputs, other_values=None):
        """
        Populates the tool model consumed by the client form builder.
        """
        populate_model(
            request_context=request_context,
            inputs=inputs,
            state_inputs=state_inputs,
            group_inputs=group_inputs,
            other_values=other_values,
        )

    def _map_source_to_history(self, trans, tool_inputs, params):
        # Need to remap dataset parameters. Job parameters point to original
        # dataset used; parameter should be the analygous dataset in the
        # current history.
        history = trans.history

        # Create index for hdas.
        hda_source_dict = {}
        for hda in history.datasets:
            key = f"{hda.hid}_{hda.dataset.id}"
            hda_source_dict[hda.dataset.id] = hda_source_dict[key] = hda

        # Ditto for dataset collections.
        hdca_source_dict = {}
        for hdca in history.dataset_collections:
            key = f"{hdca.hid}_{hdca.collection.id}"
            hdca_source_dict[hdca.collection.id] = hdca_source_dict[key] = hdca

        # Map dataset or collection to current history
        def map_to_history(value):
            id = None
            source = None
            if isinstance(value, self.app.model.HistoryDatasetAssociation):
                id = value.dataset.id
                source = hda_source_dict
            elif isinstance(value, self.app.model.HistoryDatasetCollectionAssociation):
                id = value.collection.id
                source = hdca_source_dict
            else:
                return None
            if (key := f"{value.hid}_{id}") in source:
                return source[key]
            elif id in source:
                return source[id]
            else:
                return None

        def mapping_callback(input, value, **kwargs):
            if isinstance(input, DataToolParameter):
                if isinstance(value, list):
                    values = []
                    for val in value:
                        new_val = map_to_history(val)
                        if new_val:
                            values.append(new_val)
                        else:
                            values.append(val)
                    return values
                else:
                    return map_to_history(value)
            elif isinstance(input, DataCollectionToolParameter):
                return map_to_history(value)

        visit_input_values(tool_inputs, params, mapping_callback)

    def _compare_tool_version(self, job):
        """
        Compares a tool version with the tool version from a job (from ToolRunner).
        """
        tool_id = job.tool_id
        tool_version = job.tool_version
        message = ""
        try:
            select_field, tools, tool = self.app.toolbox.get_tool_components(
                tool_id, tool_version=tool_version, get_loaded_tools_by_lineage=False, set_selected=True
            )
            if tool is None:
                raise exceptions.MessageException(
                    f"This dataset was created by an obsolete tool ({tool_id}). Can't re-run."
                )
            if (self.id != tool_id and self.old_id != tool_id) or self.version != tool_version:
                if self.id == tool_id:
                    if tool_version:
                        message = f'This job was run with tool version "{tool_version}", which is not available. '
                        if len(tools) > 1:
                            message += (
                                "You can re-run the job with the selected tool or choose another version of the tool. "
                            )
                        else:
                            message += "You can re-run the job with this tool version, which is a different version of the original tool. "
                else:
                    new_tool_shed_url = f"{tool.sharable_url}/{tool.changeset_revision}/"
                    old_tool_shed_url = get_tool_shed_url_from_tool_shed_registry(self.app, tool_id.split("/repos/")[0])
                    old_tool_shed_url = f"{old_tool_shed_url}/view/{tool.repository_owner}/{tool.repository_name}/"
                    message = f'This job was run with <a href="{old_tool_shed_url}" target="_blank">tool id "{tool_id}"</a>, version "{tool_version}", which is not available. '
                    if len(tools) > 1:
                        message += f'You can re-run the job with the selected <a href="{new_tool_shed_url}" target="_blank">tool id "{self.id}"</a> or choose another derivation of the tool. '
                    else:
                        message += f'You can re-run the job with <a href="{new_tool_shed_url}" target="_blank">tool id "{self.id}"</a>, which is a derivation of the original tool. '
            if not self.is_latest_version:
                message += "There is a newer version of this tool available."
        except Exception as e:
            raise exceptions.MessageException(unicodify(e))
        return message

    def get_default_history_by_trans(self, trans, create=False):
        return trans.get_history(create=create)

    @classmethod
    def get_externally_referenced_paths(self, path):
        """Return relative paths to externally referenced files by the tool
        described by file at `path`. External components should not assume things
        about the structure of tool xml files (this is the tool's responsibility).
        """
        tree = raw_tool_xml_tree(path)
        root = tree.getroot()
        external_paths = []
        for code_elem in root.findall("code"):
            external_path = code_elem.get("file")
            if external_path:
                external_paths.append(external_path)
        external_paths.extend(imported_macro_paths(root))
        # May also need to load external citation files as well at some point.
        return external_paths


class OutputParameterJSONTool(Tool):
    """
    Alternate implementation of Tool that provides parameters and other values
    JSONified within the contents of an output dataset
    """

    tool_type = "output_parameter_json"

    def _prepare_json_list(self, param_list):
        rval = []
        for value in param_list:
            if isinstance(value, dict):
                rval.append(self._prepare_json_param_dict(value))
            elif isinstance(value, list):
                rval.append(self._prepare_json_list(value))
            else:
                rval.append(str(value))
        return rval

    def _prepare_json_param_dict(self, param_dict):
        rval = {}
        for key, value in param_dict.items():
            if isinstance(value, MutableMapping):
                rval[key] = self._prepare_json_param_dict(value)
            elif isinstance(value, list):
                rval[key] = self._prepare_json_list(value)
            else:
                rval[key] = str(value)
        return rval

    def exec_before_job(self, app, inp_data, out_data, param_dict=None):
        if param_dict is None:
            param_dict = {}
        json_params = {}
        json_params["param_dict"] = self._prepare_json_param_dict(
            param_dict
        )  # it would probably be better to store the original incoming parameters here, instead of the Galaxy modified ones?
        json_params["output_data"] = []
        json_params["job_config"] = dict(
            GALAXY_DATATYPES_CONF_FILE=param_dict.get("GALAXY_DATATYPES_CONF_FILE"),
            GALAXY_ROOT_DIR=param_dict.get("GALAXY_ROOT_DIR"),
            TOOL_PROVIDED_JOB_METADATA_FILE=self.provided_metadata_file,
        )
        json_filename = None
        for out_name, data in out_data.items():
            # use wrapped dataset to access certain values
            wrapped_data = param_dict.get(out_name)
            # allow multiple files to be created
            file_name = str(wrapped_data)
            extra_files_path = str(wrapped_data.files_path)
            data_dict = dict(
                out_data_name=out_name,
                ext=data.ext,
                dataset_id=data.dataset.id,
                hda_id=data.id,
                file_name=file_name,
                extra_files_path=extra_files_path,
            )
            json_params["output_data"].append(data_dict)
            if json_filename is None:
                json_filename = file_name
        if json_filename is None:
            raise Exception("Must call 'exec_before_job' with 'out_data' containing at least one entry.")
        with open(json_filename, "w") as out:
            out.write(json.dumps(json_params))


class ExpressionTool(Tool):
    requires_js_runtime = True
    tool_type = "expression"
    tool_type_local = True
    EXPRESSION_INPUTS_NAME = "_expression_inputs_.json"

    def parse_command(self, tool_source):
        self.command = f"cd ../; {expressions.EXPRESSION_SCRIPT_CALL}"
        self.interpreter = None
        self._expression = tool_source.parse_expression().strip()

    def parse_outputs(self, tool_source):
        # Setup self.outputs and self.output_collections
        super().parse_outputs(tool_source)

        # Validate these outputs for expression tools.
        if len(self.output_collections) != 0:
            message = "Expression tools may not declare output collections at this time."
            raise Exception(message)
        for output in self.outputs.values():
            if not hasattr(output, "from_expression"):
                message = "Expression tools may not declare output datasets at this time."
                raise Exception(message)

    def exec_before_job(self, app, inp_data, out_data, param_dict=None):
        super().exec_before_job(app, inp_data, out_data, param_dict=param_dict)
        local_working_directory = param_dict["__local_working_directory__"]
        expression_inputs_path = os.path.join(local_working_directory, ExpressionTool.EXPRESSION_INPUTS_NAME)

        outputs = []
        for out_name in out_data.keys():
            output_def = self.outputs[out_name]
            wrapped_data = param_dict.get(out_name)
            file_name = str(wrapped_data)

            outputs.append(
                dict(
                    name=out_name,
                    from_expression=output_def.from_expression,
                    path=file_name,
                )
            )

        if param_dict is None:
            raise Exception("Internal error - param_dict is empty.")

        job: Dict[str, str] = {}
        json_wrap(self.inputs, param_dict, self.profile, job, handle_files="OBJECT")
        expression_inputs = {
            "job": job,
            "script": self._expression,
            "outputs": outputs,
        }
        expressions.write_evalute_script(os.path.join(local_working_directory))
        with open(expression_inputs_path, "w") as f:
            json.dump(expression_inputs, f)

    def exec_after_process(self, app, inp_data, out_data, param_dict, job, final_job_state=None):
        for key, val in self.outputs.items():
            if key not in out_data:
                # Skip filtered outputs
                continue
            if val.output_type == "data":
                with open(out_data[key].get_file_name()) as f:
                    src = json.load(f)
                if src is None:
                    continue
                assert isinstance(src, dict), f"Expected dataset 'src' to be a dictionary - actual type is {type(src)}"
                dataset_id = src["id"]
                copy_object = None
                for input_dataset in inp_data.values():
                    if input_dataset and input_dataset.id == dataset_id:
                        copy_object = input_dataset
                        break
                if copy_object is None:
                    raise exceptions.MessageException("Failed to find dataset output.")
                output = out_data[key]
                # if change_datatype PJA is associated with expression tool output the new output already has
                # the desired datatype, so we use it. If the extension is "data" there's no change_dataset PJA and
                # we want to use the existing extension.
                new_ext = (
                    output.extension if output.extension not in ("data", "expression.json") else copy_object.extension
                )
                require_metadata_regeneration = copy_object.extension != new_ext
                output.copy_from(copy_object, include_metadata=not require_metadata_regeneration)
                output.extension = new_ext
                if require_metadata_regeneration:
                    if app.config.enable_celery_tasks:
                        from galaxy.celery.tasks import set_metadata

                        output._state = model.Dataset.states.SETTING_METADATA
                        return set_metadata.si(
                            dataset_id=output.id, task_user_id=output.history.user_id, ensure_can_set_metadata=False
                        )
                    else:
                        # TODO: move exec_after_process into metadata script so this doesn't run on the headnode ?
                        output.init_meta()
                        try:
                            output.set_meta()
                            output.set_metadata_success_state()
                        except Exception:
                            output.state = model.HistoryDatasetAssociation.states.FAILED_METADATA
                            log.exception("Exception occured while setting metdata")

    def parse_environment_variables(self, tool_source):
        """Setup environment variable for inputs file."""
        environmnt_variables_raw = super().parse_environment_variables(tool_source)
        expression_script_inputs = dict(
            name="GALAXY_EXPRESSION_INPUTS",
            template=ExpressionTool.EXPRESSION_INPUTS_NAME,
        )
        environmnt_variables_raw.append(expression_script_inputs)
        return environmnt_variables_raw


class DataSourceTool(OutputParameterJSONTool):
    """
    Alternate implementation of Tool for data_source tools -- those that
    allow the user to query and extract data from another web site.
    """

    tool_type = "data_source"
    default_tool_action = DataSourceToolAction

    @property
    def wants_params_cleaned(self):
        """Indicates whether received, but undeclared request params should be cleaned."""
        if self.profile < 24.0:
            return False
        return True

    def _build_GALAXY_URL_parameter(self):
        return ToolParameter.build(
            self, XML(f'<param name="GALAXY_URL" type="baseurl" value="/tool_runner?tool_id={self.id}" />')
        )

    def parse_inputs(self, tool_source):
        super().parse_inputs(tool_source)
        # Open all data_source tools in _top.
        self.target = "_top"
        # data_source tools cannot check param values
        self.check_values = False
        if "GALAXY_URL" not in self.inputs:
            self.inputs["GALAXY_URL"] = self._build_GALAXY_URL_parameter()
            self.inputs_by_page[0]["GALAXY_URL"] = self.inputs["GALAXY_URL"]

    def exec_before_job(self, app, inp_data, out_data, param_dict=None):
        if param_dict is None:
            param_dict = {}
        dbkey = param_dict.get("dbkey")
        info = param_dict.get("info")
        data_type = param_dict.get("data_type")
        name = param_dict.get("name")

        json_params = {}
        json_params["param_dict"] = self._prepare_json_param_dict(
            param_dict
        )  # it would probably be better to store the original incoming parameters here, instead of the Galaxy modified ones?
        json_params["output_data"] = []
        json_params["job_config"] = dict(
            GALAXY_DATATYPES_CONF_FILE=param_dict.get("GALAXY_DATATYPES_CONF_FILE"),
            GALAXY_ROOT_DIR=param_dict.get("GALAXY_ROOT_DIR"),
            TOOL_PROVIDED_JOB_METADATA_FILE=self.provided_metadata_file,
        )
        json_filename = None
        for out_name, data in out_data.items():
            # use wrapped dataset to access certain values
            wrapped_data = param_dict.get(out_name)
            # allow multiple files to be created
            cur_base_param_name = f"GALAXY|{out_name}|"
            cur_name = param_dict.get(f"{cur_base_param_name}name", name)
            cur_dbkey = param_dict.get(f"{cur_base_param_name}dkey", dbkey)
            cur_info = param_dict.get(f"{cur_base_param_name}info", info)
            cur_data_type = param_dict.get(f"{cur_base_param_name}data_type", data_type)
            if cur_name:
                data.name = cur_name
            if not data.info and cur_info:
                data.info = cur_info
            if cur_dbkey:
                data.dbkey = cur_dbkey
            if cur_data_type:
                data.extension = cur_data_type
            file_name = str(wrapped_data)
            extra_files_path = str(wrapped_data.files_path)
            data_dict = dict(
                out_data_name=out_name,
                ext=data.ext,
                dataset_id=data.dataset.id,
                hda_id=data.id,
                file_name=file_name,
                extra_files_path=extra_files_path,
            )
            json_params["output_data"].append(data_dict)
            if json_filename is None:
                json_filename = file_name
        if json_filename is None:
            raise Exception("Must call 'exec_before_job' with 'out_data' containing at least one entry.")
        with open(json_filename, "w") as out:
            out.write(json.dumps(json_params))


class AsyncDataSourceTool(DataSourceTool):
    tool_type = "data_source_async"

    def _build_GALAXY_URL_parameter(self):
        return ToolParameter.build(self, XML(f'<param name="GALAXY_URL" type="baseurl" value="/async/{self.id}" />'))


class DataDestinationTool(Tool):
    tool_type = "data_destination"


class SetMetadataTool(Tool):
    """
    Tool implementation for special tool that sets metadata on an existing
    dataset.
    """

    tool_type = "set_metadata"
    requires_setting_metadata = False
    tool_action: "SetMetadataToolAction"

    def regenerate_imported_metadata_if_needed(
        self, hda: model.HistoryDatasetAssociation, history: model.History, user: model.User, session_id: int
    ):
        if hda.has_metadata_files:
            job, *_ = self.tool_action.execute_via_app(
                self,
                self.app,
                session_id,
                history.id,
                user,
                incoming={"input1": hda},
                overwrite=False,
            )
            self.app.job_manager.enqueue(job=job, tool=self)

    def exec_after_process(self, app, inp_data, out_data, param_dict, job, final_job_state=None):
        working_directory = app.object_store.get_filename(job, base_dir="job_work", dir_only=True, obj_dir=True)
        for name, dataset in inp_data.items():
            external_metadata = get_metadata_compute_strategy(app.config, job.id, tool_id=self.id)
            sa_session = app.model.context
            metadata_set_successfully = external_metadata.external_metadata_set_successfully(
                dataset, name, sa_session, working_directory=working_directory
            )
            if metadata_set_successfully:
                try:
                    # external_metadata_set_successfully is only an approximation (the metadata json file exists),
                    # things can still go wrong, but we don't want to fail here since it can lead to a resubmission loop
                    external_metadata.load_metadata(dataset, name, sa_session, working_directory=working_directory)
                except Exception:
                    metadata_set_successfully = False
                    log.exception("Exception occured while loading metadata results")
            if not metadata_set_successfully:
                dataset.state = model.DatasetInstance.states.FAILED_METADATA
                self.sa_session.add(dataset)
                self.sa_session.commit()
                return
            # If setting external metadata has failed, how can we inform the
            # user? For now, we'll leave the default metadata and set the state
            # back to its original.
            dataset.datatype.after_setting_metadata(dataset)
            if job and job.tool_id == "1.0.0":
                dataset.state = param_dict.get("__ORIGINAL_DATASET_STATE__")
            else:
                # Revert dataset.state to fall back to dataset.dataset.state
                dataset.set_metadata_success_state()
            # Need to reset the peek, which may rely on metadata
            # TODO: move this into metadata setting, setting the peek requires dataset access,
            # and large chunks of the dataset may be read here.
            try:
                dataset.set_peek()
            except Exception:
                log.exception("Exception occured while setting dataset peek")
            self.sa_session.add(dataset)
            self.sa_session.commit()

    def job_failed(self, job_wrapper, message, exception=False):
        job = job_wrapper.sa_session.get(Job, job_wrapper.job_id)
        if job:
            inp_data = {}
            for dataset_assoc in job.input_datasets:
                inp_data[dataset_assoc.name] = dataset_assoc.dataset
            return self.exec_after_process(job_wrapper.app, inp_data, {}, job_wrapper.get_param_dict(), job=job)


class ExportHistoryTool(Tool):
    tool_type = "export_history"


class ImportHistoryTool(Tool):
    tool_type = "import_history"

    def exec_after_process(self, app, inp_data, out_data, param_dict, job, final_job_state=None):
        super().exec_after_process(app, inp_data, out_data, param_dict, job=job, final_job_state=final_job_state)
        if final_job_state != DETECTED_JOB_STATE.OK:
            return
        JobImportHistoryArchiveWrapper(self.app, job.id).cleanup_after_job()


class InteractiveTool(Tool):
    tool_type = "interactive"
    produces_entry_points = True

    def __init__(self, config_file, tool_source, app, **kwd):
        if not app.config.interactivetools_enable:
            raise ToolLoadError("Trying to load an InteractiveTool, but InteractiveTools are not enabled.")
        super().__init__(config_file, tool_source, app, **kwd)

    def __remove_interactivetool_by_job(self, job):
        if job:
            eps = job.interactivetool_entry_points
            log.debug("__remove_interactivetool_by_job: %s", eps)
            self.app.interactivetool_manager.remove_entry_points(eps)
        else:
            log.warning("Could not determine job to stop InteractiveTool: %s", job)

    def exec_after_process(self, app, inp_data, out_data, param_dict, job, final_job_state=None):
        super().exec_after_process(app, inp_data, out_data, param_dict, job=job, final_job_state=final_job_state)
        self.__remove_interactivetool_by_job(job)

    def job_failed(self, job_wrapper, message, exception=False):
        super().job_failed(job_wrapper, message, exception=exception)
        job = job_wrapper.sa_session.get(Job, job_wrapper.job_id)
        self.__remove_interactivetool_by_job(job)


class DataManagerTool(OutputParameterJSONTool):
    tool_type = "manage_data"
    default_tool_action = DataManagerToolAction

    def __init__(self, config_file, root, app, guid=None, data_manager_id=None, **kwds):
        self.data_manager_id = data_manager_id
        super().__init__(config_file, root, app, guid=guid, **kwds)
        if self.data_manager_id is None:
            self.data_manager_id = self.id

    def exec_after_process(self, app, inp_data, out_data, param_dict, job, final_job_state=None):
        assert self.allow_user_access(job.user), "You must be an admin to access this tool."
        if final_job_state != DETECTED_JOB_STATE.OK:
            return
        super().exec_after_process(app, inp_data, out_data, param_dict, job=job, final_job_state=final_job_state)
        # process results of tool
        data_manager_id = job.data_manager_association.data_manager_id
        data_manager = self.app.data_managers.get_manager(data_manager_id)
        assert (
            data_manager is not None
        ), f"Invalid data manager ({data_manager_id}) requested. It may have been removed before the job completed."
        data_manager_mode = param_dict.get("__data_manager_mode", "populate")
        if data_manager_mode == "populate":
            data_manager.process_result(out_data)
        elif data_manager_mode == "dry_run":
            pass
        elif data_manager_mode == "bundle":
            for bundle_path, dataset in data_manager.write_bundle(out_data).items():
                hda = cast(model.HistoryDatasetAssociation, dataset)
                hda.dataset.object_store.update_from_file(
                    hda.dataset,
                    extra_dir=hda.dataset.extra_files_path_name,
                    file_name=bundle_path,
                    alt_name=os.path.basename(bundle_path),
                    create=True,
                    preserve_symlinks=True,
                )

        else:
            raise Exception("Unknown data manager mode encountered type...")

    def get_default_history_by_trans(self, trans, create=False):
        def _create_data_manager_history(user):
            history = trans.app.model.History(name="Data Manager History (automatically created)", user=user)
            data_manager_association = trans.app.model.DataManagerHistoryAssociation(user=user, history=history)
            trans.sa_session.add_all((history, data_manager_association))
            trans.sa_session.commit()
            return history

        user = trans.user
        assert user, "You must be logged in to use this tool."
        assert self.allow_user_access(user), "You must be an admin to access this tool."
        dm_history_associations = user.data_manager_histories
        if not dm_history_associations:
            # create
            if create:
                history = _create_data_manager_history(user)
            else:
                history = None
        else:
            for dm_history_association in reversed(dm_history_associations):
                history = dm_history_association.history
                if not history.deleted:
                    break
            if history.deleted:
                if create:
                    history = _create_data_manager_history(user)
                else:
                    history = None
        return history

    def allow_user_access(self, user, attempting_access=True) -> bool:
        """Check user access to this tool.

        :param user: model object representing user.
        :type user: galaxy.model.User
        :param attempting_access: is the user attempting to do something with the
                                  the tool (set false for incidental checks like toolbox
                                  listing)
        :type attempting_access:  bool

        :returns: Whether the user is allowed to access the tool.
                  Data Manager tools are only accessible to admins.
        """
        if super().allow_user_access(user) and self.app.config.is_admin_user(user):
            return True
        # If this is just an incidental check - do not log the scary message
        # about users attempting to do something problematic.
        if attempting_access:
            if user:
                user = user.id
            log.debug("User (%s) attempted to access a data manager tool (%s), but is not an admin.", user, self.id)
        return False


class DatabaseOperationTool(Tool):
    default_tool_action = ModelOperationToolAction
    require_terminal_states = True
    require_dataset_ok = True
    tool_type_local = True
    require_terminal_or_paused_states = False

    @property
    def valid_input_states(self):
        if self.require_dataset_ok:
            return (model.Dataset.states.OK,)
        elif self.require_terminal_states:
            return model.Dataset.terminal_states
        elif self.require_terminal_or_paused_states:
            return model.Dataset.terminal_states or model.Dataset.states.PAUSED
        else:
            return model.Dataset.valid_input_states

    @property
    def allow_errored_inputs(self):
        return not self.require_dataset_ok

    def check_inputs_ready(self, input_datasets, input_dataset_collections):
        def check_dataset_state(state):
            if self.require_terminal_states and state in model.Dataset.non_ready_states:
                raise ToolInputsNotReadyException("An input dataset is pending.")

            if self.require_dataset_ok:
                if state != model.Dataset.states.OK:
                    raise ToolInputsNotOKException(
                        f"Tool requires inputs to be in valid state, but dataset {input_dataset} is in state '{input_dataset.state}'",
                        src="hda",
                        id=input_dataset.id,
                    )

        for input_dataset in input_datasets.values():
            if input_dataset:
                # None is a possible input for optional inputs
                check_dataset_state(input_dataset.state)

        for input_dataset_collection_pairs in input_dataset_collections.values():
            for input_dataset_collection, _ in input_dataset_collection_pairs:
                if not input_dataset_collection.collection.populated_optimized:
                    raise ToolInputsNotReadyException("An input collection is not populated.")

            states, _ = input_dataset_collection.collection.dataset_states_and_extensions_summary
            for state in states:
                check_dataset_state(state)

    def _add_datasets_to_history(self, history, elements, datasets_visible=False):
        for element_object in elements:
            if getattr(element_object, "history_content_type", None) == "dataset":
                element_object.visible = datasets_visible
                history.stage_addition(element_object)

    def produce_outputs(self, trans: "ProvidesUserContext", out_data, output_collections, incoming, history, **kwds):
        return self._outputs_dict()

    def _outputs_dict(self):
        return {}


class UnzipCollectionTool(DatabaseOperationTool):
    tool_type = "unzip_collection"
    require_terminal_states = False
    require_dataset_ok = False

    def produce_outputs(self, trans, out_data, output_collections, incoming, history, **kwds):
        has_collection = incoming["input"]
        if hasattr(has_collection, "element_type"):
            # It is a DCE
            collection = has_collection.element_object
        else:
            # It is an HDCA
            collection = has_collection.collection

        assert collection.collection_type == "paired"
        forward_o, reverse_o = collection.dataset_instances
        forward, reverse = forward_o.copy(copy_tags=forward_o.tags, flush=False), reverse_o.copy(
            copy_tags=reverse_o.tags, flush=False
        )
        self._add_datasets_to_history(history, [forward, reverse])

        out_data["forward"] = forward
        out_data["reverse"] = reverse


class ZipCollectionTool(DatabaseOperationTool):
    tool_type = "zip_collection"
    require_terminal_states = False
    require_dataset_ok = False

    def produce_outputs(self, trans, out_data, output_collections, incoming, history, **kwds):
        forward_o = incoming["input_forward"]
        reverse_o = incoming["input_reverse"]

        forward, reverse = forward_o.copy(copy_tags=forward_o.tags, flush=False), reverse_o.copy(
            copy_tags=reverse_o.tags, flush=False
        )
        new_elements = {}
        new_elements["forward"] = forward
        new_elements["reverse"] = reverse
        self._add_datasets_to_history(history, [forward, reverse])
        output_collections.create_collection(
            next(iter(self.outputs.values())), "output", elements=new_elements, propagate_hda_tags=False
        )


class CrossProductFlatCollectionTool(DatabaseOperationTool):
    tool_type = "cross_product_flat"
    require_terminal_states = False
    require_dataset_ok = False

    def produce_outputs(self, trans, out_data, output_collections, incoming, history, **kwds):
        input_a = incoming["input_a"]
        input_b = incoming["input_b"]
        join_identifier = incoming["join_identifier"]

        output_a = {}
        output_b = {}
        all_copied_hdas = []

        for input_a_dce in input_a.collection.elements:
            element_identifier_a = input_a_dce.element_identifier
            for input_b_dce in input_b.collection.elements:
                element_identifier_b = input_b_dce.element_identifier
                identifier = f"{element_identifier_a}{join_identifier}{element_identifier_b}"

                hda_a_copy = input_a_dce.element_object.copy(copy_tags=input_a_dce.element_object.tags, flush=False)
                hda_b_copy = input_b_dce.element_object.copy(copy_tags=input_b_dce.element_object.tags, flush=False)
                all_copied_hdas.append(hda_a_copy)
                all_copied_hdas.append(hda_b_copy)
                output_a[identifier] = hda_a_copy
                output_b[identifier] = hda_b_copy

        self._add_datasets_to_history(history, all_copied_hdas)
        output_collections.create_collection(
            self.outputs["output_a"], "output_a", elements=output_a, propagate_hda_tags=False
        )
        output_collections.create_collection(
            self.outputs["output_b"], "output_b", elements=output_b, propagate_hda_tags=False
        )


class CrossProductNestedCollectionTool(DatabaseOperationTool):
    tool_type = "cross_product_nested"
    require_terminal_states = False
    require_dataset_ok = False

    def produce_outputs(self, trans, out_data, output_collections, incoming, history, **kwds):
        input_a = incoming["input_a"]
        input_b = incoming["input_b"]

        output_a = {}
        output_b = {}
        all_copied_hdas = []

        for input_a_dce in input_a.collection.elements:
            element_identifier_a = input_a_dce.element_identifier

            iter_elements_a = {}
            iter_elements_b = {}

            for input_b_dce in input_b.collection.elements:
                element_identifier_b = input_b_dce.element_identifier

                hda_a_copy = input_a_dce.element_object.copy(copy_tags=input_a_dce.element_object.tags, flush=False)
                hda_b_copy = input_b_dce.element_object.copy(copy_tags=input_b_dce.element_object.tags, flush=False)
                all_copied_hdas.append(hda_a_copy)
                all_copied_hdas.append(hda_b_copy)
                iter_elements_a[element_identifier_b] = hda_a_copy
                iter_elements_b[element_identifier_b] = hda_b_copy

            sub_collection_a: Dict[str, Any] = {}
            sub_collection_a["src"] = "new_collection"
            sub_collection_a["collection_type"] = "list"
            sub_collection_a["elements"] = iter_elements_a

            output_a[element_identifier_a] = sub_collection_a

            sub_collection_b: Dict[str, Any] = {}
            sub_collection_b["src"] = "new_collection"
            sub_collection_b["collection_type"] = "list"
            sub_collection_b["elements"] = iter_elements_b

            output_b[element_identifier_a] = sub_collection_b

        self._add_datasets_to_history(history, all_copied_hdas)
        output_collections.create_collection(
            self.outputs["output_a"], "output_a", elements=output_a, propagate_hda_tags=False
        )
        output_collections.create_collection(
            self.outputs["output_b"], "output_b", elements=output_b, propagate_hda_tags=False
        )


class BuildListCollectionTool(DatabaseOperationTool):
    tool_type = "build_list"
    require_terminal_states = False
    require_dataset_ok = False

    def produce_outputs(self, trans, out_data, output_collections, incoming, history, **kwds):
        new_elements = {}

        for i, incoming_repeat in enumerate(incoming["datasets"]):
            if incoming_repeat["input"]:
                try:
                    id_select = incoming_repeat["id_cond"]["id_select"]
                except KeyError:
                    # Prior to tool version 1.2.0
                    id_select = "idx"
                if id_select == "idx":
                    identifier = str(i)
                elif id_select == "identifier":
                    identifier = getattr(incoming_repeat["input"], "element_identifier", incoming_repeat["input"].name)
                elif id_select == "manual":
                    identifier = incoming_repeat["id_cond"]["identifier"]
                new_elements[identifier] = incoming_repeat["input"].copy(
                    copy_tags=incoming_repeat["input"].tags, flush=False
                )

        self._add_datasets_to_history(history, new_elements.values())
        output_collections.create_collection(
            next(iter(self.outputs.values())), "output", elements=new_elements, propagate_hda_tags=False
        )


class ExtractDatasetCollectionTool(DatabaseOperationTool):
    tool_type = "extract_dataset"
    require_terminal_states = False
    require_dataset_ok = False

    def produce_outputs(self, trans, out_data, output_collections, incoming, history, **kwds):
        has_collection = incoming["input"]
        if hasattr(has_collection, "element_type"):
            # It is a DCE
            collection = has_collection.element_object
        else:
            # It is an HDCA
            collection = has_collection.collection

        collection_type = collection.collection_type
        assert collection_type in ["list", "paired"]
        how = incoming["which"]["which_dataset"]
        if how == "first":
            extracted_element = collection.first_dataset_element
            if not extracted_element:
                raise exceptions.RequestParameterInvalidException("Input collection has no dataset elements.")
        elif how == "by_identifier":
            try:
                extracted_element = collection[incoming["which"]["identifier"]]
            except KeyError as e:
                raise exceptions.RequestParameterInvalidException(e.args[0])
        elif how == "by_index":
            try:
                extracted_element = collection[int(incoming["which"]["index"])]
            except KeyError as e:
                raise exceptions.RequestParameterInvalidException(e.args[0])
        else:
            raise exceptions.RequestParameterInvalidException("Invalid tool parameters.")
        extracted = extracted_element.element_object
        extracted_o = extracted.copy(
            copy_tags=extracted.tags, new_name=extracted_element.element_identifier, flush=False
        )
        self._add_datasets_to_history(history, [extracted_o], datasets_visible=True)

        out_data["output"] = extracted_o


class MergeCollectionTool(DatabaseOperationTool):
    tool_type = "merge_collection"
    require_terminal_states = False
    require_dataset_ok = False

    def produce_outputs(self, trans, out_data, output_collections, incoming, history, **kwds):
        input_lists = []

        for incoming_repeat in incoming["inputs"]:
            input_lists.append(incoming_repeat["input"])

        dupl_actions = "keep_first"
        suffix_pattern = None
        if (advanced := incoming.get("advanced", None)) is not None:
            dupl_actions = advanced["conflict"]["duplicate_options"]

            if dupl_actions in ["suffix_conflict", "suffix_every", "suffix_conflict_rest"]:
                suffix_pattern = advanced["conflict"]["suffix_pattern"]

        new_element_structure = {}

        # Which inputs does the identifier appear in.
        identifiers_map: Dict[str, List[int]] = {}
        for input_num, input_list in enumerate(input_lists):
            for dce in input_list.collection.elements:
                element_identifier = dce.element_identifier
                if element_identifier not in identifiers_map:
                    identifiers_map[element_identifier] = []
                elif dupl_actions == "fail":
                    raise exceptions.MessageException(
                        f"Duplicate collection element identifiers found for [{element_identifier}]"
                    )
                identifiers_map[element_identifier].append(input_num)

        for copy, input_list in enumerate(input_lists):
            for dce in input_list.collection.elements:
                element = dce.element_object
                element_identifier = dce.element_identifier
                identifier_seen = element_identifier in new_element_structure
                appearances = identifiers_map[element_identifier]
                add_suffix = False
                if dupl_actions == "suffix_every":
                    add_suffix = True
                elif dupl_actions == "suffix_conflict" and len(appearances) > 1:
                    add_suffix = True
                elif dupl_actions == "suffix_conflict_rest" and len(appearances) > 1 and appearances[0] != copy:
                    add_suffix = True

                if dupl_actions == "keep_first" and identifier_seen:
                    continue

                if add_suffix and suffix_pattern:
                    suffix = suffix_pattern.replace("#", str(copy + 1))
                    effective_identifer = f"{element_identifier}{suffix}"
                else:
                    effective_identifer = element_identifier

                new_element_structure[effective_identifer] = element

        # Don't copy until we know everything is fine and we have the structure of the list ready to go.
        new_elements = {}
        for key, value in new_element_structure.items():
            if getattr(value, "history_content_type", None) == "dataset":
                copied_value = value.copy(copy_tags=value.tags, flush=False)
            else:
                copied_value = value.copy(flush=False)
            new_elements[key] = copied_value

        self._add_datasets_to_history(history, new_elements.values())
        output_collections.create_collection(
            next(iter(self.outputs.values())), "output", elements=new_elements, propagate_hda_tags=False
        )


class FilterDatasetsTool(DatabaseOperationTool):
    require_terminal_states = True
    require_dataset_ok = False

    def _get_new_elements(self, history, elements_to_copy):
        new_elements = {}
        for dce in elements_to_copy:
            element_identifier = dce.element_identifier
            if getattr(dce.element_object, "history_content_type", None) == "dataset":
                copied_value = dce.element_object.copy(copy_tags=dce.element_object.tags, flush=False)
            else:
                copied_value = dce.element_object.copy(flush=False)
            new_elements[element_identifier] = copied_value
        return new_elements

    @staticmethod
    def element_is_valid(element: model.DatasetCollectionElement):
        element_object = element.element_object
        assert isinstance(element_object, model.DatasetInstance)
        return element_object.is_ok

    def produce_outputs(self, trans, out_data, output_collections, incoming, history, **kwds):
        collection = incoming["input"]

        if hasattr(collection, "element_object"):
            # A list
            elements = collection.element_object.elements
            collection_type = collection.element_object.collection_type
        else:
            # A list of pairs
            elements = collection.collection.elements
            collection_type = collection.collection.collection_type
        # We only process list or list of pair collections. Higher order collection will be mapped over
        assert collection_type in ("list", "list:paired")

        elements_to_copy = []
        for element in elements:
            if collection_type == "list":
                if self.element_is_valid(element):
                    elements_to_copy.append(element)
            else:
                valid = True
                for child_element in element.child_collection.elements:
                    if not self.element_is_valid(child_element):
                        valid = False
                if valid:
                    elements_to_copy.append(element)

        new_elements = self._get_new_elements(history=history, elements_to_copy=elements_to_copy)
        self._add_datasets_to_history(history, new_elements.values())
        output_collections.create_collection(
            next(iter(self.outputs.values())), "output", elements=new_elements, propagate_hda_tags=False
        )


class FilterFailedDatasetsTool(FilterDatasetsTool):
    tool_type = "filter_failed_datasets_collection"
    require_dataset_ok = False

    @staticmethod
    def element_is_valid(element: model.DatasetCollectionElement):
        element_object = element.element_object
        assert isinstance(element_object, model.DatasetInstance)
        return element_object.is_ok


class KeepSuccessDatasetsTool(FilterDatasetsTool):
    tool_type = "keep_success_datasets_collection"
    require_terminal_states = False
    require_dataset_ok = False
    require_terminal_or_paused_states = True

    @staticmethod
    def element_is_valid(element: model.DatasetCollectionElement):
        element_object = element.element_object
        assert isinstance(element_object, model.DatasetInstance)
        if (
            element_object.state != model.Dataset.states.PAUSED
            and element_object.state in model.Dataset.non_ready_states
        ):
            raise ToolInputsNotReadyException("An input dataset is pending.")
        return element_object.is_ok


class FilterEmptyDatasetsTool(FilterDatasetsTool):
    tool_type = "filter_empty_datasets_collection"
    require_dataset_ok = False

    @staticmethod
    def element_is_valid(element: model.DatasetCollectionElement):
        element_object = element.element_object
        assert isinstance(element_object, model.DatasetInstance)
        if element_object.has_data():
            # We have data, but it might just be a compressed archive of nothing
            file_name = element_object.get_file_name()
            _, fh = get_fileobj_raw(file_name, mode="rb")
            if len(fh.read(1)):
                return True
        return False


class FilterNullTool(FilterDatasetsTool):
    tool_type = "filter_null"
    require_dataset_ok = True

    @staticmethod
    def element_is_valid(element: model.DatasetCollectionElement):
        element_object = element.element_object
        assert isinstance(element_object, model.DatasetInstance)
        if element_object.extension == "expression.json":
            if element_object.peek == "null":
                # shortcut
                return False
            else:
                with open(element_object.get_file_name()) as fh:
                    if fh.read(5) == "null":
                        return False
        return True


class FlattenTool(DatabaseOperationTool):
    tool_type = "flatten_collection"
    require_terminal_states = False
    require_dataset_ok = False

    def produce_outputs(self, trans, out_data, output_collections, incoming, history, **kwds):
        hdca = incoming["input"]
        join_identifier = incoming["join_identifier"]
        new_elements = {}
        copied_datasets = []

        def add_elements(collection, prefix=""):
            for dce in collection.elements:
                dce_object = dce.element_object
                dce_identifier = dce.element_identifier
                identifier = f"{prefix}{join_identifier}{dce_identifier}" if prefix else dce_identifier
                if dce.is_collection:
                    add_elements(dce_object, prefix=identifier)
                else:
                    copied_dataset = dce_object.copy(copy_tags=dce_object.tags, flush=False)
                    new_elements[identifier] = copied_dataset
                    copied_datasets.append(copied_dataset)

        add_elements(hdca.collection)
        self._add_datasets_to_history(history, copied_datasets)
        output_collections.create_collection(
            next(iter(self.outputs.values())), "output", elements=new_elements, propagate_hda_tags=False
        )


class SortTool(DatabaseOperationTool):
    tool_type = "sort_collection"
    require_terminal_states = True
    require_dataset_ok = False

    def produce_outputs(self, trans, out_data, output_collections, incoming, history, **kwds):
        hdca = incoming["input"]
        sorttype = incoming["sort_type"]["sort_type"]
        new_elements = {}
        elements = hdca.collection.elements
        presort_elements = None
        if sorttype == "alpha":
            presort_elements = [(dce.element_identifier, dce) for dce in elements]
        elif sorttype == "numeric":
            presort_elements = [(int(re.sub("[^0-9]", "", dce.element_identifier)), dce) for dce in elements]
        elif sorttype == "file":
            hda = incoming["sort_type"]["sort_file"]
            data_lines = hda.metadata.get("data_lines", 0)
            if data_lines == len(elements):
                old_elements_dict = {}
                for element in elements:
                    old_elements_dict[element.element_identifier] = element
                try:
                    with open(hda.get_file_name()) as fh:
                        sorted_elements = [old_elements_dict[line.strip()] for line in fh]
                except KeyError:
                    hdca_history_name = f"{hdca.hid}: {hdca.name}"
                    message = f"List of element identifiers does not match element identifiers in collection '{hdca_history_name}'"
                    raise exceptions.MessageException(message)
            else:
                message = f"Number of lines must match number of list elements ({len(elements)}), but file has {data_lines} lines"
                raise exceptions.MessageException(message)
        else:
            raise exceptions.MessageException(f"Unknown sort_type '{sorttype}'")

        if presort_elements is not None:
            sorted_elements = [x[1] for x in sorted(presort_elements, key=lambda x: x[0])]

        for dce in sorted_elements:
            dce_object = dce.element_object
            if getattr(dce_object, "history_content_type", None) == "dataset":
                copied_dataset = dce_object.copy(copy_tags=dce_object.tags, flush=False)
            else:
                copied_dataset = dce_object.copy(flush=False)
            new_elements[dce.element_identifier] = copied_dataset

        self._add_datasets_to_history(history, new_elements.values())
        output_collections.create_collection(
            next(iter(self.outputs.values())), "output", elements=new_elements, propagate_hda_tags=False
        )


class HarmonizeTool(DatabaseOperationTool):
    tool_type = "harmonize_list"
    require_terminal_states = False
    require_dataset_ok = False

    def produce_outputs(self, trans, out_data, output_collections, incoming, history, **kwds):
        # Get the 2 input collections
        hdca1 = incoming["input1"]
        hdca2 = incoming["input2"]
        # Get the elements of both collections
        elements1 = hdca1.collection.elements
        elements2 = hdca2.collection.elements
        # Put elements in dictionary with identifiers:
        old_elements1_dict = {}
        for element in elements1:
            old_elements1_dict[element.element_identifier] = element
        old_elements2_dict = {}
        for element in elements2:
            old_elements2_dict[element.element_identifier] = element
        # Get the list of final identifiers
        final_sorted_identifiers = [
            element.element_identifier for element in elements1 if element.element_identifier in old_elements2_dict
        ]
        if len(final_sorted_identifiers) == 0:
            # Create empty collections:
            output_collections.create_collection(
                self.outputs["output1"], "output1", elements={}, propagate_hda_tags=False
            )
            output_collections.create_collection(
                self.outputs["output2"], "output2", elements={}, propagate_hda_tags=False
            )
            return

        def output_with_selected_identifiers(old_elements_dict, output_label):
            # Create a new dictionary with the elements in the good order
            new_elements = {}
            for identifier in final_sorted_identifiers:
                dce_object = old_elements_dict[identifier].element_object
                if getattr(dce_object, "history_content_type", None) == "dataset":
                    copied_dataset = dce_object.copy(copy_tags=dce_object.tags, flush=False)
                else:
                    copied_dataset = dce_object.copy(flush=False)
                new_elements[identifier] = copied_dataset
            # Add datasets:
            self._add_datasets_to_history(history, new_elements.values())
            # Create collections:
            output_collections.create_collection(
                self.outputs[output_label], output_label, elements=new_elements, propagate_hda_tags=False
            )

        # Create outputs:
        output_with_selected_identifiers(old_elements1_dict, "output1")
        output_with_selected_identifiers(old_elements2_dict, "output2")


class RelabelFromFileTool(DatabaseOperationTool):
    tool_type = "relabel_from_file"

    def produce_outputs(self, trans, out_data, output_collections, incoming, history, **kwds):
        hdca = incoming["input"]
        how_type = incoming["how"]["how_select"]
        new_labels_dataset_assoc = incoming["how"]["labels"]
        strict = string_as_bool(incoming["how"]["strict"])
        new_elements = {}

        def add_copied_value_to_new_elements(new_label, dce_object):
            new_label = new_label.strip()
            if new_label in new_elements:
                raise exceptions.MessageException(
                    f"New identifier [{new_label}] appears twice in resulting collection, these values must be unique."
                )
            if getattr(dce_object, "history_content_type", None) == "dataset":
                copied_value = dce_object.copy(copy_tags=dce_object.tags, flush=False)
            else:
                copied_value = dce_object.copy(flush=False)
            new_elements[new_label] = copied_value

        new_labels_path = new_labels_dataset_assoc.get_file_name()
        with open(new_labels_path) as fh:
            new_labels = fh.readlines(1024 * 1000000)
        if strict and len(hdca.collection.elements) != len(new_labels):
            raise exceptions.MessageException("Relabel mapping file contains incorrect number of identifiers")
        if how_type in ["tabular", "tabular_extended"]:
            # We have a tabular file, where one column lists existing element identifiers,
            # another one the corresponding new element identifiers.
            # In tabular_extended mode the two columns ("from" and "to") are user-specified,
            # while in simple tabular mode they default to the first and second column and
            # these must be the only two columns in the input.
            from_index = int(incoming["how"].get("from", 1)) - 1
            to_index = int(incoming["how"].get("to", 2)) - 1
            if from_index < 0 or to_index < 0:
                raise exceptions.MessageException(
                    "Column < 1 specified for relabel mapping file. Column count starts at 1."
                )
            new_labels_dict = {}
            try:
                for i, line in enumerate(new_labels, 1):
                    cols = line.strip().split("\t")
                    if how_type == "tabular" and len(cols) != 2:
                        raise exceptions.MessageException(
                            f"Relabel mapping file contains {len(cols)} columns on line {i}, but 2 are required"
                        )
                    new_labels_dict[cols[from_index]] = cols[to_index]
            except IndexError:
                raise exceptions.MessageException(
                    f"Specified column number > number of columns [{len(cols)}] on line {i} of relabel mapping file."
                )
            for dce in hdca.collection.elements:
                dce_object = dce.element_object
                element_identifier = dce.element_identifier
                default = None if strict else element_identifier
                new_label = new_labels_dict.get(element_identifier, default)
                if not new_label:
                    raise exceptions.MessageException(f"Failed to find original identifier [{element_identifier}]")
                add_copied_value_to_new_elements(new_label, dce_object)
        else:
            # If new_labels_dataset_assoc is not a two-column tabular dataset we label with the current line of the dataset
            if hdca.collection.element_count > len(new_labels):
                raise exceptions.MessageException(
                    "Relabel mapping file contains less lines than there are collection elements to relabel."
                )
            for i, dce in enumerate(hdca.collection.elements):
                dce_object = dce.element_object
                add_copied_value_to_new_elements(new_labels[i], dce_object)
        for key in new_elements.keys():
            if not re.match(r"^[\w\- \.,]+$", key):
                raise exceptions.MessageException(f"Invalid new collection identifier [{key}]")
        self._add_datasets_to_history(history, new_elements.values())
        output_collections.create_collection(
            next(iter(self.outputs.values())), "output", elements=new_elements, propagate_hda_tags=False
        )


class ApplyRulesTool(DatabaseOperationTool):
    tool_type = "apply_rules"

    def produce_outputs(self, trans, out_data, output_collections, incoming, history, **kwds):
        hdca = incoming["input"]
        rule_set = RuleSet(incoming["rules"])
        copied_datasets = []

        def copy_dataset(dataset, tags):
            copied_dataset = dataset.copy(copy_tags=dataset.tags, flush=False)
            if tags is not None:
                trans.tag_handler.set_tags_from_list(
                    trans.get_user(),
                    copied_dataset,
                    tags,
                    flush=False,
                )
            copied_dataset.history_id = history.id
            copied_datasets.append(copied_dataset)
            return copied_dataset

        new_elements = self.app.dataset_collection_manager.apply_rules(hdca, rule_set, copy_dataset)
        self._add_datasets_to_history(history, copied_datasets)
        output_collections.create_collection(
            next(iter(self.outputs.values())),
            "output",
            collection_type=rule_set.collection_type,
            elements=new_elements,
            propagate_hda_tags=False,
        )


class TagFromFileTool(DatabaseOperationTool):
    tool_type = "tag_from_file"
    # We don't currently discriminate which input has to be in which state
    # so we do need all inputs to be "ok", when in fact only the file input
    # needs to be ok.
    # require_terminal_states = True
    # require_dataset_ok = False

    def produce_outputs(self, trans, out_data, output_collections, incoming, history, **kwds):
        hdca = incoming["input"]
        how = incoming["how"]
        new_tags_dataset_assoc = incoming["tags"]
        new_elements = {}
        new_datasets = []

        def add_copied_value_to_new_elements(new_tags_dict, dce):
            tag_handler = trans.tag_handler
            if getattr(dce.element_object, "history_content_type", None) == "dataset":
                copied_value = dce.element_object.copy(copy_tags=dce.element_object.tags, flush=False)
                # copy should never be visible, since part of a collection
                copied_value.visble = False
                new_datasets.append(copied_value)
                new_tags = new_tags_dict.get(dce.element_identifier)
                if new_tags:
                    if how in ("add", "remove") and dce.element_object.tags:
                        # We need get the original tags and update them with the new tags
                        old_tags = {tag for tag in tag_handler.get_tags_str(dce.element_object.tags).split(",") if tag}
                        if how == "add":
                            old_tags.update(set(new_tags))
                        elif how == "remove":
                            old_tags = old_tags - set(new_tags)
                        new_tags = old_tags
                    tag_handler.add_tags_from_list(
                        user=history.user,
                        item=copied_value,
                        new_tags_list=new_tags,
                        flush=False,
                    )
            else:
                # We have a collection, and we copy the elements so that we don't manipulate the original tags
                copied_value = dce.element_object.copy(element_destination=history, flush=False)
                for new_element, old_element in zip(copied_value.dataset_elements, dce.element_object.dataset_elements):
                    # TODO: This should be eliminated, but collections created by the collection builder
                    # don't set `visible` to `False` if you don't hide the original elements.
                    new_element.element_object.visible = False
                    new_tags = new_tags_dict.get(new_element.element_identifier)
                    if how in ("add", "remove"):
                        old_tags = {
                            tag for tag in tag_handler.get_tags_str(old_element.element_object.tags).split(",") if tag
                        }
                        if new_tags:
                            if how == "add":
                                old_tags.update(set(new_tags))
                            elif how == "remove":
                                old_tags = old_tags - set(new_tags)
                        new_tags = old_tags
                    tag_handler.add_tags_from_list(
                        user=history.user, item=new_element.element_object, new_tags_list=new_tags, flush=False
                    )
            new_elements[dce.element_identifier] = copied_value

        new_tags_path = new_tags_dataset_assoc.get_file_name()
        with open(new_tags_path) as fh:
            new_tags = fh.readlines(1024 * 1000000)
        # We have a tabular file, where the first column is an existing element identifier,
        # and the remaining columns represent new tags.
        source_new_tags = (line.strip().split("\t") for line in new_tags)
        new_tags_dict = {item[0]: item[1:] for item in source_new_tags}
        for dce in hdca.collection.elements:
            add_copied_value_to_new_elements(new_tags_dict, dce)
        self._add_datasets_to_history(history, new_datasets)
        output_collections.create_collection(
            next(iter(self.outputs.values())), "output", elements=new_elements, propagate_hda_tags=False
        )


class FilterFromFileTool(DatabaseOperationTool):
    tool_type = "filter_from_file"

    def produce_outputs(self, trans, out_data, output_collections, incoming, history, **kwds):
        hdca = incoming["input"]
        how_filter = incoming["how"]["how_filter"]
        filter_dataset_assoc = incoming["how"]["filter_source"]
        filtered_elements = {}
        discarded_elements = {}

        filtered_path = filter_dataset_assoc.get_file_name()
        with open(filtered_path) as fh:
            filtered_identifiers = [i.strip() for i in fh.readlines(1024 * 1000000)]

        # If filtered_dataset_assoc is not a two-column tabular dataset we label with the current line of the dataset
        for dce in hdca.collection.elements:
            dce_object = dce.element_object
            element_identifier = dce.element_identifier
            in_filter_file = element_identifier in filtered_identifiers
            passes_filter = in_filter_file if how_filter == "remove_if_absent" else not in_filter_file

            if getattr(dce_object, "history_content_type", None) == "dataset":
                copied_value = dce_object.copy(copy_tags=dce_object.tags, flush=False)
            else:
                copied_value = dce_object.copy(flush=False)

            if passes_filter:
                filtered_elements[element_identifier] = copied_value
            else:
                discarded_elements[element_identifier] = copied_value

        self._add_datasets_to_history(history, filtered_elements.values())
        output_collections.create_collection(
            self.outputs["output_filtered"], "output_filtered", elements=filtered_elements, propagate_hda_tags=False
        )
        self._add_datasets_to_history(history, discarded_elements.values())
        output_collections.create_collection(
            self.outputs["output_discarded"], "output_discarded", elements=discarded_elements, propagate_hda_tags=False
        )


class DuplicateFileToCollectionTool(DatabaseOperationTool):
    tool_type = "duplicate_file_to_collection"
    require_terminal_states = False
    require_dataset_ok = False

    def produce_outputs(self, trans, out_data, output_collections, incoming, history, **kwds):
        hda = incoming["input"]
        number = int(incoming["number"])
        element_identifier = incoming["element_identifier"]
        elements = {
            f"{element_identifier} {n}": hda.copy(copy_tags=hda.tags, flush=False) for n in range(1, number + 1)
        }

        self._add_datasets_to_history(history, elements.values())
        output_collections.create_collection(
            next(iter(self.outputs.values())), "output", elements=elements, propagate_hda_tags=False
        )


# Populate tool_type to ToolClass mappings
TOOL_CLASSES: List[Type[Tool]] = [
    Tool,
    SetMetadataTool,
    OutputParameterJSONTool,
    ExpressionTool,
    InteractiveTool,
    DataManagerTool,
    DataSourceTool,
    AsyncDataSourceTool,
    UnzipCollectionTool,
    ZipCollectionTool,
    MergeCollectionTool,
    RelabelFromFileTool,
    FilterFromFileTool,
    DuplicateFileToCollectionTool,
    BuildListCollectionTool,
    ExtractDatasetCollectionTool,
    DataDestinationTool,
]
tool_types = {tool_class.tool_type: tool_class for tool_class in TOOL_CLASSES}

# ---- Utility classes to be factored out -----------------------------------


def _rerun_remap_job_id(trans, incoming, tool_id: Optional[str]) -> Optional[int]:
    rerun_remap_job_id = None
    if "rerun_remap_job_id" in incoming:
        try:
            rerun_remap_job_id = trans.app.security.decode_id(incoming["rerun_remap_job_id"])
        except Exception as exception:
            log.error(str(exception))
            raise exceptions.MessageException(
                "Failure executing tool with id '%s' (attempting to rerun invalid job).", tool_id
            )
    return rerun_remap_job_id


class TracksterConfig:
    """Trackster configuration encapsulation."""

    def __init__(self, actions):
        self.actions = actions

    @staticmethod
    def parse(root):
        actions = []
        for action_elt in root.findall("action"):
            actions.append(SetParamAction.parse(action_elt))
        return TracksterConfig(actions)


class SetParamAction:
    """Set parameter action."""

    def __init__(self, name, output_name):
        self.name = name
        self.output_name = output_name

    @staticmethod
    def parse(elt):
        """Parse action from element."""
        return SetParamAction(elt.get("name"), elt.get("output_name"))


class BadValue:
    def __init__(self, value):
        self.value = value


class InterruptedUpload(Exception):
    pass
