import { type Repository, type PaginatedRepositoryIndexResults } from "@/api"

export interface RepositoryGridItem {
    id: string
    name: string
    owner: string
    index: number
    update_time: string
    description: string | null
    homepage_url: string | null | undefined
    remote_repository_url: string | null | undefined
}

export function emptyQueryResults(): QueryResults {
    return { items: [], rowsNumber: 0 }
}

export interface Query {
    page: number
    rowsPerPage: number
    filter?: string
}

export interface QueryResults {
    items: RepositoryGridItem[]
    rowsNumber: number
}

function adaptIndexItem(repository: Repository, index: number): RepositoryGridItem {
    return {
        index: index,
        id: repository.id,
        name: repository.name,
        owner: repository.owner,
        description: repository.description,
        update_time: repository.update_time,
        homepage_url: repository.homepage_url,
        remote_repository_url: repository.remote_repository_url,
    }
}

export function adaptPaginatedIndexResponse(apiResults: PaginatedRepositoryIndexResults): QueryResults {
    const items = apiResults.hits.map(adaptIndexItem)
    const rowsNumber = apiResults.total_results
    return { items, rowsNumber }
}

// simplify communication between components by setting this as only value across app
export const ROWS_PER_PAGE = 20

export type OnRequest = (query: Query) => Promise<QueryResults> // for paginating grid
