/**
 * Field descriptions for metadata models.
 *
 * Loads descriptions from JSON (extracted from schema.ts) and merges with
 * hardcoded fallbacks for fields that need richer explanations.
 *
 * Run `npm run extract-descriptions` to regenerate fieldDescriptions.json
 */
import schemaDescriptions from "./fieldDescriptions.json" assert { type: "json" }

type DescriptionMap = Record<string, Record<string, string>>

// Hardcoded descriptions for fields needing richer explanations than schema provides
const fallbackDescriptions: Record<string, Record<string, string>> = {
    RepositoryRevisionMetadata: {
        downloadable: "Whether this revision can be installed into Galaxy",
        malicious: "Flagged as containing malicious code by an admin",
        changeset_revision: "Mercurial changeset hash for this revision",
        numeric_revision: "Sequential revision number (0-indexed)",
        tools: "List of tools defined in this revision",
        invalid_tools: "Tool files that failed to parse",
        repository_dependencies: "Other repositories this revision depends on",
        includes_tools: "Whether this revision contains tool definitions",
        includes_datatypes: "Whether this revision defines custom datatypes",
        missing_test_components: "Whether tool tests are incomplete",
        includes_tool_dependencies: "Whether this revision defines tool dependencies",
        includes_workflows: "Whether this revision contains workflows",
        has_repository_dependencies: "Whether this revision has repository dependencies",
        has_repository_dependencies_only_if_compiling_contained_td:
            "Repository dependencies only needed when compiling tool dependencies",
    },
    RepositoryTool: {
        id: "Tool identifier (unique within repository)",
        guid: "Globally unique tool identifier",
        name: "Human-readable tool name",
        version: "Tool version string",
        description: "Short description of tool functionality",
        tool_config: "Absolute path to tool XML configuration",
        tool_type: "Type of tool (e.g., 'default', 'data_manager')",
        requirements: "Software dependencies for this tool",
        tests: "Test cases defined for this tool",
        add_to_tool_panel: "Whether tool should appear in Galaxy tool panel",
    },
    RepositoryDependency: {
        name: "Name of the required repository",
        owner: "Owner of the required repository",
        changeset_revision: "Required changeset revision",
        toolshed: "Tool Shed URL where dependency is hosted",
        prior_installation_required: "Whether dependency must be installed first",
    },
    ChangesetMetadataStatus: {
        action: "What happened to this changeset during reset",
        changeset_revision: "Mercurial changeset hash",
        numeric_revision: "Sequential revision number",
        comparison_result: "How new metadata compares to existing",
        has_tools: "Whether this changeset contains tools",
        has_repository_dependencies: "Whether this changeset has repo dependencies",
        has_tool_dependencies: "Whether this changeset has tool dependencies",
        error: "Error message if processing failed",
    },
    ResetMetadataOnRepositoryResponse: {
        status: "Overall operation status (ok, warning, error)",
        dry_run: "Whether this was a preview without changes",
        changeset_details: "Per-changeset processing details",
        repository_metadata_before: "Full metadata snapshot before reset",
        repository_metadata_after: "Full metadata snapshot after reset",
    },
    Repository: {
        deprecated: "Whether this repository is marked as deprecated",
        deleted: "Whether this repository is deleted",
        private: "Whether this repository is private",
        times_downloaded: "Number of times this repository has been installed",
    },
}

// Merge schema descriptions with fallbacks (fallbacks take priority for richer text)
const descriptions: DescriptionMap = {}

// First, add all schema descriptions
for (const [model, fields] of Object.entries(schemaDescriptions as DescriptionMap)) {
    descriptions[model] = { ...fields }
}

// Then, overlay fallback descriptions (these are more descriptive)
for (const [model, fields] of Object.entries(fallbackDescriptions)) {
    if (!descriptions[model]) {
        descriptions[model] = {}
    }
    for (const [field, desc] of Object.entries(fields)) {
        descriptions[model][field] = desc
    }
}

export function getFieldDescription(modelName: string | undefined, fieldName: string): string {
    if (!modelName) return ""
    return descriptions[modelName]?.[fieldName] ?? ""
}
