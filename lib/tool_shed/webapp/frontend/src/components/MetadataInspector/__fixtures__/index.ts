/**
 * Test fixtures generated from real API responses.
 *
 * To regenerate these fixtures, run from packages/tool_shed:
 *
 *   TOOL_SHED_FIXTURE_OUTPUT_DIR=lib/tool_shed/webapp/frontend/src/components/MetadataInspector/__fixtures__ \
 *   TOOL_SHED_API_VERSION=v2 \
 *   uv run pytest tool_shed/test/functional/test_shed_repositories.py::TestShedRepositoriesApi::test_generate_frontend_fixtures -v
 */

import type { components } from "@/schema/schema"

// Real fixtures from API
import columnMakerMetadata from "./repository_metadata_column_maker.json"
import bismarkMetadata from "./repository_metadata_bismark.json"
import resetPreview from "./reset_metadata_preview.json"
import resetApplied from "./reset_metadata_applied.json"
import resetBismark from "./reset_metadata_bismark.json"
import resetUnchanged from "./reset_metadata_unchanged.json"
import resetSubset from "./reset_metadata_subset.json"

// Simulated fixtures for edge cases
// TODO: Update test_shed_repositories.py::test_generate_frontend_fixtures to generate real API
// responses for these edge cases so this directory contains only real API responses.
// Edge cases needed:
// - Repository with no tools (empty workflow-only or datatype-only repo)
// - Repository with repository_dependencies (define one with deps in test_data)
// - Repository with multiple different tool IDs (multi-tool repo)
// - Reset response with record_operation: "created" (first-time reset on fresh repo)
// - Reset response with error (broken tool XML)
// - Reset response with status: "warning" (partial success)
import simulatedChangesetActions from "./simulated_changeset_actions.json"
import simulatedMetadataNoTools from "./simulated_metadata_no_tools.json"
import simulatedMetadataWithDeps from "./simulated_metadata_with_deps.json"
import simulatedMetadataMultiTools from "./simulated_metadata_multi_tools.json"
import simulatedResetWarning from "./simulated_reset_warning.json"

export type RepositoryMetadata = components["schemas"]["RepositoryMetadata"]
export type RepositoryRevisionMetadata = components["schemas"]["RepositoryRevisionMetadata"]
export type ResetMetadataOnRepositoryResponse = components["schemas"]["ResetMetadataOnRepositoryResponse"]
export type ChangesetMetadataStatus = components["schemas"]["ChangesetMetadataStatus"]

// ============================================================================
// Real API Fixtures
// ============================================================================

/** Multi-revision repository with tools (column_maker has 3 revisions) */
export const repositoryMetadataColumnMaker = columnMakerMetadata as RepositoryMetadata

/** Repository with invalid_tools */
export const repositoryMetadataBismark = bismarkMetadata as RepositoryMetadata

/** Reset metadata dry-run preview response */
export const resetMetadataPreview = resetPreview as ResetMetadataOnRepositoryResponse

/** Reset metadata applied (non-dry-run) response */
export const resetMetadataApplied = resetApplied as ResetMetadataOnRepositoryResponse

/** Reset metadata dry-run preview for bismark (has tool dependencies, invalid_tools) */
export const resetMetadataBismark = resetBismark as ResetMetadataOnRepositoryResponse

/** Reset metadata dry-run preview showing "equal" comparison_result (unchanged revisions) */
export const resetMetadataUnchanged = resetUnchanged as ResetMetadataOnRepositoryResponse

/** Reset metadata dry-run preview showing "subset" comparison_result (additive changes only) */
export const resetMetadataSubset = resetSubset as ResetMetadataOnRepositoryResponse

// ============================================================================
// Simulated Fixtures for Edge Case Testing
// TODO: Replace with real API responses when test data is available
// ============================================================================

/**
 * Changeset details with all comparison_result types: initial, equal, subset, not equal and not subset, error
 * TODO: Generate from real API by creating repos that produce each comparison result type
 */
export const simulatedChangesets = simulatedChangesetActions as ChangesetMetadataStatus[]

/**
 * Repository metadata with no tools (empty repo or datatype-only)
 * TODO: Generate from real API by creating a datatype-only or workflow-only repo
 */
export const simulatedMetadataEmpty = simulatedMetadataNoTools as RepositoryMetadata

/**
 * Repository metadata with repository_dependencies
 * TODO: Generate from real API by creating a repo with defined dependencies
 */
export const simulatedMetadataDeps = simulatedMetadataWithDeps as RepositoryMetadata

/**
 * Repository metadata with multiple different tool IDs across revisions
 * TODO: Generate from real API by creating a multi-tool repo with version history
 */
export const simulatedMetadataMultiTool = simulatedMetadataMultiTools as RepositoryMetadata

/**
 * Reset response with warning status and mixed action results
 * TODO: Generate from real API by resetting a repo with some broken tool XML
 */
export const simulatedResetWithWarning = simulatedResetWarning as ResetMetadataOnRepositoryResponse

// ============================================================================
// Helper Functions
// ============================================================================

/** Get changeset details from reset response */
export function getChangesetDetails(response: ResetMetadataOnRepositoryResponse): ChangesetMetadataStatus[] {
    return response.changeset_details ?? []
}

/** Get a single revision from metadata */
export function getFirstRevision(metadata: RepositoryMetadata): RepositoryRevisionMetadata | undefined {
    const keys = Object.keys(metadata)
    return keys.length > 0 ? metadata[keys[0]] : undefined
}

/** Get all tools from all revisions in metadata */
export function getAllTools(
    metadata: RepositoryMetadata
): Array<{ tool: components["schemas"]["RepositoryTool"]; revisionKey: string }> {
    const tools: Array<{ tool: components["schemas"]["RepositoryTool"]; revisionKey: string }> = []
    for (const [key, revision] of Object.entries(metadata)) {
        if (revision.tools) {
            for (const tool of revision.tools) {
                tools.push({ tool, revisionKey: key })
            }
        }
    }
    return tools
}

// Re-export test utilities
export * from "./factories"
