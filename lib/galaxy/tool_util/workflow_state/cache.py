"""Tool cache management: options models, business logic, and run_*() entry points.

Manages a local cache of ParsedTool metadata for ToolShed tools.
"""

import argparse
import json
import logging
import os
import sys
from typing import Optional

from pydantic import BaseModel

from gxformat2.normalized import ensure_native

from .toolshed_tool_info import (
    DEFAULT_TOOLSHED_URL,
    parse_toolshed_tool_id,
    ToolShedGetToolInfo,
)

log = logging.getLogger(__name__)

# TODO: move all the imports to the top of the file please.
# -- Options models --


class PopulateOptions(BaseModel):
    tool_source_cache_dir: Optional[str] = None
    verbose: bool = False
    workflow_path: str
    tool_source: str = "shed"
    galaxy_url: Optional[str] = None

    @classmethod
    def from_namespace(cls, args: argparse.Namespace) -> "PopulateOptions":
        fields = set(cls.model_fields)
        return cls(**{k: v for k, v in vars(args).items() if k in fields})


class AddOptions(BaseModel):
    tool_source_cache_dir: Optional[str] = None
    verbose: bool = False
    tool_id: str
    version: Optional[str] = None
    tool_source: str = "shed"
    galaxy_url: Optional[str] = None

    @classmethod
    def from_namespace(cls, args: argparse.Namespace) -> "AddOptions":
        fields = set(cls.model_fields)
        return cls(**{k: v for k, v in vars(args).items() if k in fields})


class AddLocalOptions(BaseModel):
    tool_source_cache_dir: Optional[str] = None
    verbose: bool = False
    xml_path: str
    tool_id: Optional[str] = None
    version: Optional[str] = None

    @classmethod
    def from_namespace(cls, args: argparse.Namespace) -> "AddLocalOptions":
        fields = set(cls.model_fields)
        return cls(**{k: v for k, v in vars(args).items() if k in fields})


class ListOptions(BaseModel):
    tool_source_cache_dir: Optional[str] = None
    verbose: bool = False
    json_output: bool = False

    @classmethod
    def from_namespace(cls, args: argparse.Namespace) -> "ListOptions":
        fields = set(cls.model_fields)
        # --json maps to args.json, but our field is json_output
        kwargs = {k: v for k, v in vars(args).items() if k in fields}
        if "json" in vars(args):
            kwargs["json_output"] = args.json
        return cls(**kwargs)


class InfoOptions(BaseModel):
    tool_source_cache_dir: Optional[str] = None
    verbose: bool = False
    trs_tool_id: str
    version: Optional[str] = None

    @classmethod
    def from_namespace(cls, args: argparse.Namespace) -> "InfoOptions":
        fields = set(cls.model_fields)
        return cls(**{k: v for k, v in vars(args).items() if k in fields})


class ClearOptions(BaseModel):
    tool_source_cache_dir: Optional[str] = None
    verbose: bool = False
    tool_id_prefix: Optional[str] = None

    @classmethod
    def from_namespace(cls, args: argparse.Namespace) -> "ClearOptions":
        fields = set(cls.model_fields)
        return cls(**{k: v for k, v in vars(args).items() if k in fields})


class SchemaOptions(BaseModel):
    tool_source_cache_dir: Optional[str] = None
    verbose: bool = False
    trs_tool_id: str
    version: Optional[str] = None
    representation: str = "workflow_step"
    output: Optional[str] = None

    @classmethod
    def from_namespace(cls, args: argparse.Namespace) -> "SchemaOptions":
        fields = set(cls.model_fields)
        return cls(**{k: v for k, v in vars(args).items() if k in fields})


class StructuralSchemaOptions(BaseModel):
    tool_source_cache_dir: Optional[str] = None
    verbose: bool = False
    strict: bool = False
    output: Optional[str] = None

    @classmethod
    def from_namespace(cls, args: argparse.Namespace) -> "StructuralSchemaOptions":
        fields = set(cls.model_fields)
        return cls(**{k: v for k, v in vars(args).items() if k in fields})


# -- Core cache operations --


def build_tool_info(cache_dir: Optional[str] = None, galaxy_url: Optional[str] = None) -> ToolShedGetToolInfo:
    """Build ToolShedGetToolInfo from a cache directory path."""
    return ToolShedGetToolInfo(cache_dir=cache_dir, galaxy_url=galaxy_url)


def add_tool(tool_info: ToolShedGetToolInfo, tool_id: str, tool_version: Optional[str], source: str = "shed") -> bool:
    """Add a single tool to the cache. Returns True on success."""
    parsed = parse_toolshed_tool_id(tool_id)
    if parsed is not None:
        toolshed_url, trs_tool_id, embedded_version = parsed
        version = tool_version or embedded_version
    else:
        toolshed_url = DEFAULT_TOOLSHED_URL
        trs_tool_id = tool_id
        version = tool_version or "_default_"

    if version is None:
        print(f"  SKIP {tool_id} (no version available)")
        return False

    if tool_info.has_cached(tool_id, version):
        print(f"  CACHED {tool_id} {version}")
        return True

    if source == "auto":
        sources_to_try = ["shed", "galaxy"]
    else:
        sources_to_try = [source]

    for src in sources_to_try:
        try:
            if src == "shed":
                parsed_tool = tool_info.fetch_from_api(toolshed_url, trs_tool_id, version)
                source_url = f"{toolshed_url}/api/tools/{trs_tool_id}/versions/{version}"
            elif src == "galaxy":
                parsed_tool = tool_info.fetch_from_galaxy(tool_info.galaxy_url, tool_id, version)
                source_url = f"{tool_info.galaxy_url}/api/tools/{tool_id}/parsed"
            else:
                continue

            tool_info.populate_from_parsed_tool(tool_id, version, parsed_tool, source=src, source_url=source_url)
            print(f"  OK {tool_id} {version} (from {src})")
            return True
        except Exception as e:
            log.debug(f"  Failed to fetch {tool_id} {version} from {src}: {e}")
            continue

    print(f"  FAIL {tool_id} {version}")
    return False


def populate_cache(tool_info: ToolShedGetToolInfo, path: str, source: str = "auto"):
    """Populate tool cache from a workflow file or directory (auto-detected).

    Returns (ok_count, fail_count).
    """
    if os.path.isdir(path):
        return _populate_cache_for_tree(tool_info, path, source=source)
    else:
        return _populate_cache_for_workflow(tool_info, path, source=source)


def _populate_cache_for_workflow(tool_info: ToolShedGetToolInfo, workflow_path: str, source: str = "auto"):
    workflow = ensure_native(workflow_path)
    tools = workflow.unique_tools

    if not tools:
        print("No tools found in workflow.")
        return 0, 0

    print(f"Found {len(tools)} tool(s) in workflow:")
    ok, fail = 0, 0
    for tool_id, tool_version in sorted(tools):
        if add_tool(tool_info, tool_id, tool_version, source=source):
            ok += 1
        else:
            fail += 1

    print(f"\nSummary: {ok} cached, {fail} failed")
    return ok, fail


def _populate_cache_for_tree(tool_info: ToolShedGetToolInfo, root: str, source: str = "auto"):
    from .workflow_tree import (
        discover_workflows,
        load_workflow_safe,
    )

    workflows = discover_workflows(root)
    all_tools = set()
    for info in workflows:
        wf_dict = load_workflow_safe(info)
        if wf_dict is not None:
            all_tools.update(ensure_native(wf_dict).unique_tools)

    if not all_tools:
        print(f"No tools found across {len(workflows)} workflow(s).")
        return 0, 0

    print(f"Found {len(all_tools)} unique tool(s) across {len(workflows)} workflow(s):")
    ok, fail = 0, 0
    for tool_id, tool_version in sorted(all_tools):
        if add_tool(tool_info, tool_id, tool_version, source=source):
            ok += 1
        else:
            fail += 1

    print(f"\nSummary: {ok} cached, {fail} failed")
    return ok, fail


# -- Subcommand entry points --


def run_populate(options: PopulateOptions):
    tool_info = build_tool_info(options.tool_source_cache_dir, galaxy_url=options.galaxy_url)
    populate_cache(tool_info, options.workflow_path, source=options.tool_source)


def run_add(options: AddOptions):
    tool_info = build_tool_info(options.tool_source_cache_dir, galaxy_url=options.galaxy_url)
    add_tool(tool_info, options.tool_id, options.version, source=options.tool_source)


def run_add_local(options: AddLocalOptions):
    from galaxy.tool_util.model_factory import parse_tool
    from galaxy.tool_util.parser.factory import get_tool_source

    tool_info = build_tool_info(options.tool_source_cache_dir)

    try:
        tool_source = get_tool_source(config_file=options.xml_path)
        parsed_tool = parse_tool(tool_source)
    except Exception as e:
        print(f"Failed to parse {options.xml_path}: {e}", file=sys.stderr)
        sys.exit(1)

    tool_id = options.tool_id
    if tool_id is None:
        parsed_id = parsed_tool.id
        parsed_version = parsed_tool.version
        if parsed_id and parsed_version:
            print(f"Parsed tool: {parsed_id} v{parsed_version}")
            print("Use --tool-id to specify the full toolshed tool_id for proper cache keying.")
            sys.exit(1)
        else:
            print("Cannot determine tool_id from XML. Use --tool-id.", file=sys.stderr)
            sys.exit(1)

    version = options.version or parsed_tool.version
    if version is None:
        print("Cannot determine version. Use --version.", file=sys.stderr)
        sys.exit(1)

    tool_info.populate_from_parsed_tool(tool_id, version, parsed_tool, source="local", source_url=str(options.xml_path))
    print(f"Cached {tool_id} {version} from {options.xml_path}")


def run_list(options: ListOptions):
    tool_info = build_tool_info(options.tool_source_cache_dir)
    entries = tool_info.list_cached()

    if not entries:
        print("Cache is empty.")
        return

    if options.json_output:
        print(json.dumps(entries, indent=2))
    else:
        print(f"{'Tool ID':<60} {'Version':<20} {'Source':<8} {'Cached At':<11}")
        print("-" * 100)
        for entry in entries:
            tool_id = entry.get("tool_id", "?")
            version = entry.get("tool_version", "?")
            source = entry.get("source", "?")
            cached_at = entry.get("cached_at", "?")[:10]
            print(f"{tool_id:<60} {version:<20} {source:<8} {cached_at:<11}")
        print(f"\n{len(entries)} tool(s) cached.")


def run_info(options: InfoOptions):
    tool_info = build_tool_info(options.tool_source_cache_dir)

    entries = tool_info.list_cached()
    matches = []
    for entry in entries:
        tid = entry.get("tool_id", "")
        tver = entry.get("tool_version", "")
        if options.trs_tool_id in tid:
            if options.version is None or tver == options.version:
                matches.append(entry)

    if not matches:
        print(f"No cached entries matching '{options.trs_tool_id}'")
        sys.exit(1)

    for entry in matches:
        print(f"Tool ID:   {entry.get('tool_id', '?')}")
        print(f"Version:   {entry.get('tool_version', '?')}")
        print(f"Source:    {entry.get('source', '?')}")
        print(f"Source URL:{entry.get('source_url', '')}")
        print(f"Cached at: {entry.get('cached_at', '?')}")
        print(f"Cache key: {entry.get('cache_key', '?')}")

        cache_key = entry.get("cache_key")
        if cache_key:
            parsed = tool_info.load_cached(cache_key)
            if parsed:
                print(f"Name:      {parsed.name}")
                print(f"Inputs:    {len(parsed.inputs)} parameter(s)")
                print(f"Outputs:   {len(parsed.outputs)} output(s)")
        print()


def run_clear(options: ClearOptions):
    tool_info = build_tool_info(options.tool_source_cache_dir)
    if options.tool_id_prefix:
        tool_info.clear_cache(options.tool_id_prefix)
        print(f"Cleared cache entries matching '{options.tool_id_prefix}'")
    else:
        tool_info.clear_cache()
        print("Cache cleared.")


def run_schema(options: SchemaOptions):
    from galaxy.tool_util.parameters.json import to_json_schema_string
    from galaxy.tool_util_models.parameters import (
        create_model_factory,
        StateRepresentationT,
        ToolParameterBundleModel,
    )

    tool_info = build_tool_info(options.tool_source_cache_dir)

    # Resolve tool from cache (same substring match as run_info)
    entries = tool_info.list_cached()
    matches = []
    for entry in entries:
        tid = entry.get("tool_id", "")
        tver = entry.get("tool_version", "")
        if options.trs_tool_id in tid:
            if options.version is None or tver == options.version:
                matches.append(entry)

    if not matches:
        print(f"No cached entries matching '{options.trs_tool_id}'", file=sys.stderr)
        sys.exit(1)

    if len(matches) > 1:
        print(f"Multiple matches for '{options.trs_tool_id}' — use --version to disambiguate:", file=sys.stderr)
        for entry in matches:
            print(f"  {entry.get('tool_id', '?')} {entry.get('tool_version', '?')}", file=sys.stderr)
        sys.exit(1)

    entry = matches[0]
    cache_key = entry.get("cache_key")
    parsed_tool = tool_info.load_cached(cache_key)
    if parsed_tool is None:
        print(f"Failed to load cached tool: {cache_key}", file=sys.stderr)
        sys.exit(1)

    representation: StateRepresentationT = options.representation  # type: ignore[assignment]
    factory = create_model_factory(representation)
    bundle = ToolParameterBundleModel(parameters=list(parsed_tool.inputs))
    model = factory(bundle)
    schema_str = to_json_schema_string(model)

    if options.output:
        with open(options.output, "w") as f:
            f.write(schema_str)
            f.write("\n")
        print(f"Schema written to {options.output}")
    else:
        print(schema_str)


def run_structural_schema(options: StructuralSchemaOptions):
    from gxformat2.schema.json_schema import workflow_json_schema_string

    schema_str = workflow_json_schema_string(strict=options.strict)

    if options.output:
        with open(options.output, "w") as f:
            f.write(schema_str)
            f.write("\n")
        print(f"Schema written to {options.output}")
    else:
        print(schema_str)
