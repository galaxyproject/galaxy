import { useFragment } from "@/gql/fragment-masking"
import { RepositoryListItemFragment } from "@/gqlFragements"

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

export type OnScroll = () => Promise<void>

/* eslint-disable @typescript-eslint/no-explicit-any */
export function nodeToRow(node: any, index: number): RepositoryGridItem {
    /* Adapt CQL results to RepositoryGridItem interface consumed by the
       component. */
    if (node == null) {
        throw Error("Problem with server response")
    }

    const fragment = useFragment(RepositoryListItemFragment, node)
    return {
        id: fragment.encodedId,
        index: index,
        name: fragment.name as string, // TODO: fix schema.py so this is nonnull
        owner: fragment.user.username,
        description: fragment.description || null,
        homepage_url: fragment.homepageUrl || null,
        remote_repository_url: fragment.remoteRepositoryUrl || null,
        update_time: fragment.updateTime,
    }
}
