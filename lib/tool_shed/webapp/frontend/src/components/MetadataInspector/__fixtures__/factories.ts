/**
 * Factory functions for creating test data.
 * These create properly-typed test objects by extending real fixture data.
 */

import type { components } from "@/schema/schema"
import { repositoryMetadataColumnMaker } from "./"

export type RepositoryRevisionMetadata = components["schemas"]["RepositoryRevisionMetadata"]
export type ChangesetMetadataStatus = components["schemas"]["ChangesetMetadataStatus"]
export type RepositoryTool = components["schemas"]["RepositoryTool"]

/**
 * Create a ChangesetMetadataStatus with sensible defaults.
 * Override any fields as needed for specific test cases.
 */
export function makeChangeset(overrides: Partial<ChangesetMetadataStatus> = {}): ChangesetMetadataStatus {
    return {
        changeset_revision: "abc123456789",
        numeric_revision: 1,
        action: "updated",
        comparison_result: null,
        has_tools: true,
        has_repository_dependencies: false,
        has_tool_dependencies: false,
        error: null,
        ...overrides,
    }
}

/**
 * Create a RepositoryRevisionMetadata based on real fixture data.
 * Override any fields as needed for specific test cases.
 */
export function makeRevision(overrides: Partial<RepositoryRevisionMetadata> = {}): RepositoryRevisionMetadata {
    const base = Object.values(repositoryMetadataColumnMaker)[0]
    return {
        ...base,
        ...overrides,
    }
}

/**
 * Create a RepositoryTool based on real fixture data.
 * Override any fields as needed for specific test cases.
 */
export function makeTool(overrides: Partial<RepositoryTool> = {}): RepositoryTool {
    const baseTool = repositoryMetadataColumnMaker[Object.keys(repositoryMetadataColumnMaker)[0]].tools?.[0]
    if (!baseTool) throw new Error("No base tool in fixture")
    return {
        ...baseTool,
        ...overrides,
    }
}
