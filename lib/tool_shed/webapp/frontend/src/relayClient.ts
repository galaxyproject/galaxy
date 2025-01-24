import { ref, type Ref } from "vue"
import type { OperationVariables } from "@apollo/client/core/index.js"
import { useLazyQuery } from "@vue/apollo-composable"
import { DocumentParameter } from "@vue/apollo-composable/dist/useQuery"
import type { Maybe, PageInfo } from "@/gql/graphql"

export interface InterfaceHasNode<NodeType> {
    node?: Maybe<NodeType>
}

export interface RelayQuery<NodeType> {
    pageInfo: PageInfo
    edges: Array<Maybe<InterfaceHasNode<NodeType>>>
}

/* eslint-disable @typescript-eslint/no-explicit-any */
export function useRelayInfiniteScrollQuery<ResultType, NodeType>(
    query: DocumentParameter<any, OperationVariables>,
    variables: OperationVariables,
    toResult: (arg: ResultType) => RelayQuery<NodeType>
) {
    const records = ref<NodeType[]>([]) as Ref<Array<NodeType>>
    const lastResult = ref<ResultType | null>(null) as Ref<ResultType | null>
    const hasNextPage = ref(true)

    const { load, error, loading, fetchMore } = useLazyQuery(query, variables, {
        fetchPolicy: "network-only",
        nextFetchPolicy: "network-only",
    })

    function handleResult(result: ResultType) {
        lastResult.value = result
        const asResult: RelayQuery<NodeType> = toResult(result)
        hasNextPage.value = asResult.pageInfo.hasNextPage
        const nodes: NodeType[] = asResult.edges.flatMap((x) => (x && x.node ? [x.node] : []))
        records.value.push(...nodes)
    }

    async function onScroll() {
        if (hasNextPage.value && lastResult.value != null && fetchMore != null) {
            const asResult: RelayQuery<NodeType> = toResult(lastResult.value)
            const endCursor = asResult.pageInfo.endCursor
            const fetchMoreVariables = { ...variables, cursor: endCursor }
            const fetchMorePromise = fetchMore({
                variables: fetchMoreVariables,
                /*
                fetchPolicy: "network-only",
                nextFetchPolicy: "network-only",
                */
            })
            if (fetchMorePromise) {
                fetchMorePromise.then((result) => handleResult(result.data as ResultType))
            }
        }
    }

    const loadPromise = load()
    if (loadPromise) {
        loadPromise.then(handleResult)
    }

    return { records, error, loading, onScroll }
}
