/** Higher level wrappers around parts of API schema used. */
import { ToolShedApi, components } from "@/schema"
import type { paths as ToolShedApiPaths } from "@/schema/schema"

// TODO: deprecate loading from @/schema/types and define these types here, it was a good
// refactoring in the comparable Galaxy code.
export { type Repository } from "@/schema/types"

type IndexParameters = ToolShedApiPaths["/api/repositories"]["get"]["parameters"]["query"]

export type RepositorySearchResults = components["schemas"]["RepositorySearchResults"]
export type PaginatedRepositoryIndexResults = components["schemas"]["PaginatedRepositoryIndexResults"]

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
