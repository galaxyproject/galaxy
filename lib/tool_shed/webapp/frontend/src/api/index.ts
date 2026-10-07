/** Higher level wrappers around parts of API schema used. */
import { FILE_CONTENTS_PATH, ToolShedApi, components } from "@/schema"
import type { paths as ToolShedApiPaths } from "@/schema/schema"

// TODO: deprecate loading from @/schema/types and define these types here, it was a good
// refactoring in the comparable Galaxy code.
export { type Repository } from "@/schema/types"

type IndexParameters = ToolShedApiPaths["/api/repositories"]["get"]["parameters"]["query"]

export type RepositorySearchResults = components["schemas"]["RepositorySearchResults"]
export type PaginatedRepositoryIndexResults = components["schemas"]["PaginatedRepositoryIndexResults"]
export type ParsedTool = components["schemas"]["ShedParsedTool"]
export type RepositoryFileEntry = components["schemas"]["RepositoryFileEntry"]
export type RepositoryRevisionFiles = components["schemas"]["RepositoryRevisionFiles"]
export type RepositoryFileContents = components["schemas"]["RepositoryFileContents"]
type RevisionMetadata = components["schemas"]["RepositoryRevisionMetadata"]

export async function repositorySearch(params: IndexParameters): Promise<RepositorySearchResults> {
    const { data } = await ToolShedApi().GET("/api/repositories", { params: { query: params } })
    if (data) {
        return data as RepositorySearchResults
    } else {
        throw Error("Problem searching for repositories")
    }
}

export async function paginatedIndex(params: IndexParameters): Promise<PaginatedRepositoryIndexResults> {
    const { data } = await ToolShedApi().GET("/api/repositories", { params: { query: params } })
    if (data) {
        return data as PaginatedRepositoryIndexResults
    } else {
        throw Error("Problem searching for repositories")
    }
}

export async function recentlyCreatedRepositories(): Promise<PaginatedRepositoryIndexResults> {
    const params: IndexParameters = {
        sort_by: "create_time",
        sort_desc: true,
        page_size: 10,
        page: 1,
    }
    const { data } = await ToolShedApi().GET("/api/repositories", { params: { query: params } })
    if (data) {
        return data as PaginatedRepositoryIndexResults
    } else {
        throw Error("Problem searching for repositories")
    }
}

export async function getParsedTool(trsToolId: string, version: string): Promise<ParsedTool> {
    const { data } = await ToolShedApi().GET("/api/tools/{tool_id}/versions/{tool_version}", {
        params: { path: { tool_id: trsToolId, tool_version: version } },
    })
    if (!data) {
        throw Error("Failed to fetch tool details")
    }
    return data
}

/** The files API only serves downloadable, non-malicious revisions. */
export function hasBrowsableFiles(revision: Pick<RevisionMetadata, "downloadable" | "malicious">): boolean {
    return revision.downloadable && !revision.malicious
}

/** The changeset of the newest revision in repository metadata, whose keys run oldest to newest. */
export function newestRevision(
    metadata: Record<string, Pick<RevisionMetadata, "changeset_revision">> | null | undefined,
): string | null {
    const revisions = Object.values(metadata ?? {})
    return revisions[revisions.length - 1]?.changeset_revision ?? null
}

export async function repositoryFiles(
    repositoryId: string,
    changesetRevision: string,
): Promise<RepositoryRevisionFiles> {
    const { data } = await ToolShedApi().GET(
        "/api/repositories/{encoded_repository_id}/revisions/{changeset_revision}/files",
        { params: { path: { encoded_repository_id: repositoryId, changeset_revision: changesetRevision } } },
    )
    if (!data) {
        throw Error("Failed to fetch repository files")
    }
    return data
}

export async function repositoryFileContents(
    repositoryId: string,
    changesetRevision: string,
    path: string,
): Promise<RepositoryFileContents> {
    const { data } = await ToolShedApi().GET(FILE_CONTENTS_PATH, {
        params: { path: { encoded_repository_id: repositoryId, changeset_revision: changesetRevision, path } },
    })
    if (!data) {
        throw Error("Failed to fetch file contents")
    }
    return data
}
